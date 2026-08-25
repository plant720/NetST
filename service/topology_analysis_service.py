"""Pure-Python topology analysis for NetST haplotype-network GML files.

The fastHaN output, McAN adapter, and native RMST engine use the tcsBU dialect of GML:
sample names and frequency are embedded in ``data/Frequency`` and mutation
distance is stored in ``data/Changes``.  This module deliberately analyses the
undirected topology of those networks, while retaining the source GML's
``directed`` flag as provenance.  Mutation distance is a *distance* throughout;
it is never converted into an edge strength.

No biological direction, ancestry, origin, or transmission interpretation is
inferred from any centrality value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import math
import re
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple


CancelCallback = Optional[Callable[[], bool]]
NodeId = Any


class TopologyAnalysisError(ValueError):
    """Raised when a graph cannot be parsed or has invalid topology data."""


class TopologyAnalysisCancelled(RuntimeError):
    """Raised when a caller-requested cancellation interrupts analysis."""


@dataclass(frozen=True)
class TopologyNode:
    id: NodeId
    label: str = ""
    frequency: float = 0.0
    samples: Tuple[str, ...] = ()
    is_intermediate: bool = False
    attributes: Mapping[str, Any] = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class TopologyEdge:
    index: int
    source: NodeId
    target: NodeId
    mutation_distance: float = 1.0
    label: str = ""
    attributes: Mapping[str, Any] = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class TopologyGraph:
    nodes: Tuple[TopologyNode, ...]
    edges: Tuple[TopologyEdge, ...]
    directed: bool = False
    attributes: Mapping[str, Any] = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class GraphMetrics:
    node_count: int
    edge_count: int
    component_count: int
    density: float
    cycle_rank: int
    observed_node_count: int
    intermediate_node_count: int
    source_directed: bool
    analysis_projection: str = "undirected"


@dataclass(frozen=True)
class NodeMetrics:
    node_id: NodeId
    degree: int
    mutation_distance_sum: float
    closeness: float
    betweenness: float
    component: int
    articulation_point: bool
    is_intermediate: bool
    haplotype: str = ""
    frequency: float = 0.0
    samples: Tuple[str, ...] = ()
    traits: Mapping[str, Tuple[str, ...]] = field(
        default_factory=dict, compare=False)


@dataclass(frozen=True)
class EdgeMetrics:
    edge_index: int
    source: NodeId
    target: NodeId
    mutation_distance: float
    bridge: bool
    betweenness: float
    source_haplotype: str = ""
    target_haplotype: str = ""


@dataclass(frozen=True)
class TopologyAnalysisResult:
    graph: GraphMetrics
    nodes: Tuple[NodeMetrics, ...]
    edges: Tuple[EdgeMetrics, ...]
    interpretation_note: str = (
        "Centrality and articulation metrics describe graph topology only; "
        "they do not identify ancestors, origins, or transmission sources."
    )
    trait_types: Mapping[str, str] = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class _GmlBlock:
    entries: Tuple[Tuple[str, Any], ...]

    def all(self, key: str) -> List[Any]:
        return [value for name, value in self.entries if name == key]

    def first(self, key: str, default: Any = None) -> Any:
        for name, value in self.entries:
            if name == key:
                return value
        return default

    def contains(self, key: str) -> bool:
        return any(name == key for name, _ in self.entries)


@dataclass(frozen=True)
class _Token:
    value: str
    kind: str
    offset: int


def parse_tcsbu_gml(path: str) -> TopologyGraph:
    """Read a fastHaN/McAN/RMST tcsBU-compatible GML file."""
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return parse_tcsbu_gml_text(handle.read())
    except OSError as exc:
        raise TopologyAnalysisError(f"Cannot read GML file: {exc}") from exc


def parse_tcsbu_gml_text(text: str) -> TopologyGraph:
    """Parse the NetST tcsBU GML dialect without requiring NetworkX."""
    tokens = _tokenize_gml(text)
    root = _parse_document(tokens)
    graph_values = root.all("graph")
    if len(graph_values) != 1 or not isinstance(graph_values[0], _GmlBlock):
        raise TopologyAnalysisError("GML must contain exactly one graph block")
    block = graph_values[0]

    directed_value = block.first("directed", 0)
    if directed_value not in (0, 1, False, True):
        raise TopologyAnalysisError("GML directed must be 0 or 1")
    directed = bool(directed_value)

    nodes: List[TopologyNode] = []
    seen_ids = set()
    for raw_node in block.all("node"):
        if not isinstance(raw_node, _GmlBlock):
            raise TopologyAnalysisError("GML node must be a block")
        node_id = raw_node.first("id")
        if node_id is None:
            raise TopologyAnalysisError("GML node is missing id")
        try:
            duplicate = node_id in seen_ids
        except TypeError as exc:
            raise TopologyAnalysisError("GML node id must be a scalar value") from exc
        if duplicate:
            raise TopologyAnalysisError(f"Duplicate GML node id: {node_id!r}")
        seen_ids.add(node_id)

        data = raw_node.first("data", _GmlBlock(()))
        if not isinstance(data, _GmlBlock):
            raise TopologyAnalysisError(f"GML node {node_id!r} data must be a block")
        frequency_declared = data.contains("Frequency")
        frequency_text = data.first("Frequency", "")
        frequency, samples = _parse_frequency(
            frequency_text, required=frequency_declared
        )
        label_present = raw_node.contains("label")
        label = str(raw_node.first("label", "")).strip()
        # fastHaN explicitly uses an empty label for inferred transition nodes.
        # McAN-adapted GML omits label entirely, so absence alone is not enough.
        is_intermediate = (
            (frequency_declared and frequency <= 0)
            or (label_present and not label)
        )
        nodes.append(TopologyNode(
            id=node_id,
            label=label,
            frequency=frequency,
            samples=samples,
            is_intermediate=is_intermediate,
            attributes=_block_to_plain(raw_node),
        ))

    edges: List[TopologyEdge] = []
    seen_pairs = set()
    for index, raw_edge in enumerate(block.all("edge")):
        if not isinstance(raw_edge, _GmlBlock):
            raise TopologyAnalysisError("GML edge must be a block")
        source = raw_edge.first("source")
        target = raw_edge.first("target")
        if source not in seen_ids or target not in seen_ids:
            raise TopologyAnalysisError(
                f"GML edge {index} refers to an unknown node: {source!r}, {target!r}"
            )
        if source == target:
            raise TopologyAnalysisError(f"Self-loop at node {source!r} is not supported")
        pair = frozenset((source, target))
        if pair in seen_pairs:
            raise TopologyAnalysisError(
                f"Parallel edge between {source!r} and {target!r} is not supported"
            )
        seen_pairs.add(pair)

        data = raw_edge.first("data", _GmlBlock(()))
        if not isinstance(data, _GmlBlock):
            raise TopologyAnalysisError(f"GML edge {index} data must be a block")
        distance = _parse_mutation_distance(data.first("Changes", None), index)
        edges.append(TopologyEdge(
            index=index,
            source=source,
            target=target,
            mutation_distance=distance,
            label=str(raw_edge.first("label", "")).strip(),
            attributes=_block_to_plain(raw_edge),
        ))

    graph_attributes = {
        key: _plain_value(value)
        for key, value in block.entries
        if key not in {"node", "edge"}
    }
    return TopologyGraph(tuple(nodes), tuple(edges), directed, graph_attributes)


def analyze_gml(
    path: str,
    cancel_requested: CancelCallback = None,
    *,
    sample_haplotypes: Optional[Mapping[str, str]] = None,
    sample_traits: Optional[Mapping[str, Mapping[str, Any]]] = None,
    trait_types: Optional[Mapping[str, str]] = None,
) -> TopologyAnalysisResult:
    """Parse and analyse a NetST GML file."""
    _check_cancelled(cancel_requested)
    return analyze_topology(
        parse_tcsbu_gml(path), cancel_requested,
        sample_haplotypes=sample_haplotypes,
        sample_traits=sample_traits,
        trait_types=trait_types,
    )


def analyze_topology(
    graph: TopologyGraph,
    cancel_requested: CancelCallback = None,
    *,
    sample_haplotypes: Optional[Mapping[str, str]] = None,
    sample_traits: Optional[Mapping[str, Mapping[str, Any]]] = None,
    trait_types: Optional[Mapping[str, str]] = None,
) -> TopologyAnalysisResult:
    """Calculate mutation-distance-aware metrics on an undirected projection.

    Closeness uses mutation distance and the disconnected-graph correction
    ``reachable/(N-1)``. Betweenness also uses mutation distance and is
    normalized to the conventional [0, 1] range for simple undirected graphs.
    """
    _check_cancelled(cancel_requested)
    node_order = [node.id for node in graph.nodes]
    if len(set(node_order)) != len(node_order):
        raise TopologyAnalysisError("Graph contains duplicate node IDs")
    node_set = set(node_order)
    adjacency: Dict[NodeId, List[Tuple[NodeId, float, int]]] = {
        node_id: [] for node_id in node_order
    }
    seen_pairs = set()
    edge_by_index: Dict[int, TopologyEdge] = {}
    for edge in graph.edges:
        _check_cancelled(cancel_requested)
        if edge.index in edge_by_index:
            raise TopologyAnalysisError(f"Duplicate edge index: {edge.index}")
        if edge.source not in node_set or edge.target not in node_set:
            raise TopologyAnalysisError("Edge refers to an unknown node")
        if edge.source == edge.target:
            raise TopologyAnalysisError("Self-loops are not supported")
        if not math.isfinite(edge.mutation_distance) or edge.mutation_distance <= 0:
            raise TopologyAnalysisError("Mutation distance must be finite and positive")
        pair = frozenset((edge.source, edge.target))
        if pair in seen_pairs:
            raise TopologyAnalysisError("Parallel edges are not supported")
        seen_pairs.add(pair)
        edge_by_index[edge.index] = edge
        adjacency[edge.source].append((edge.target, edge.mutation_distance, edge.index))
        adjacency[edge.target].append((edge.source, edge.mutation_distance, edge.index))

    component_by_node, component_count = _components(
        node_order, adjacency, cancel_requested
    )
    articulation, bridges = _cut_vertices_and_bridges(
        node_order, adjacency, cancel_requested
    )
    closeness = _closeness(node_order, adjacency, cancel_requested)
    node_between, edge_between = _brandes_betweenness(
        node_order, adjacency, cancel_requested
    )

    n = len(node_order)
    m = len(graph.edges)
    density = 0.0 if n < 2 else (2.0 * m) / (n * (n - 1))
    cycle_rank = m - n + component_count if n else 0
    observed = sum(not node.is_intermediate for node in graph.nodes)
    summary = GraphMetrics(
        node_count=n,
        edge_count=m,
        component_count=component_count,
        density=density,
        cycle_rank=cycle_rank,
        observed_node_count=observed,
        intermediate_node_count=n - observed,
        source_directed=graph.directed,
    )

    node_lookup = {node.id: node for node in graph.nodes}
    annotations = _node_annotations(
        graph.nodes, sample_haplotypes or {}, sample_traits or {})
    node_metrics = tuple(NodeMetrics(
        node_id=node_id,
        degree=len(adjacency[node_id]),
        mutation_distance_sum=sum(distance for _, distance, _ in adjacency[node_id]),
        closeness=closeness[node_id],
        betweenness=node_between[node_id],
        component=component_by_node[node_id],
        articulation_point=node_id in articulation,
        is_intermediate=node_lookup[node_id].is_intermediate,
        haplotype=annotations[node_id][0],
        frequency=node_lookup[node_id].frequency,
        samples=node_lookup[node_id].samples,
        traits=annotations[node_id][1],
    ) for node_id in node_order)
    edge_metrics = tuple(EdgeMetrics(
        edge_index=edge.index,
        source=edge.source,
        target=edge.target,
        mutation_distance=edge.mutation_distance,
        bridge=edge.index in bridges,
        betweenness=edge_between[edge.index],
        source_haplotype=annotations[edge.source][0],
        target_haplotype=annotations[edge.target][0],
    ) for edge in graph.edges)
    return TopologyAnalysisResult(
        summary, node_metrics, edge_metrics,
        trait_types=dict(trait_types or {}))


def _node_annotations(
    nodes: Sequence[TopologyNode],
    sample_haplotypes: Mapping[str, str],
    sample_traits: Mapping[str, Mapping[str, Any]],
) -> Dict[NodeId, Tuple[str, Mapping[str, Tuple[str, ...]]]]:
    """Resolve observed GML nodes to haplotypes and aggregate sample traits.

    The sample-to-haplotype file is authoritative.  A label is only used as a
    fallback when it exactly matches a haplotype present in that mapping; this
    avoids accidentally presenting internal GML labels as biological names.
    """
    normalized_haplotypes = {
        str(sample).strip(): str(haplotype).strip()
        for sample, haplotype in sample_haplotypes.items()
        if str(sample).strip() and str(haplotype).strip()
    }
    known_haplotypes = set(normalized_haplotypes.values())
    normalized_traits = {
        str(sample).strip(): values
        for sample, values in sample_traits.items()
        if str(sample).strip()
    }
    result: Dict[NodeId, Tuple[str, Mapping[str, Tuple[str, ...]]]] = {}
    for node in nodes:
        haplotypes = list(dict.fromkeys(
            normalized_haplotypes[sample]
            for sample in node.samples
            if sample in normalized_haplotypes
        ))
        haplotype = haplotypes[0] if len(haplotypes) == 1 else ""
        if not haplotype and node.label in known_haplotypes:
            haplotype = node.label

        aggregated: Dict[str, List[str]] = {}
        for sample in node.samples:
            for name, raw_value in normalized_traits.get(sample, {}).items():
                value = str(raw_value).strip()
                if not value:
                    continue
                key = str(name).strip()
                if key and value not in aggregated.setdefault(key, []):
                    aggregated[key].append(value)
        result[node.id] = (
            haplotype,
            {name: tuple(values) for name, values in aggregated.items()},
        )
    return result


def _components(
    node_order: Sequence[NodeId],
    adjacency: Mapping[NodeId, Sequence[Tuple[NodeId, float, int]]],
    cancel_requested: CancelCallback,
) -> Tuple[Dict[NodeId, int], int]:
    assigned: Dict[NodeId, int] = {}
    component = 0
    for start in node_order:
        if start in assigned:
            continue
        component += 1
        assigned[start] = component
        stack = [start]
        while stack:
            _check_cancelled(cancel_requested)
            current = stack.pop()
            for neighbour, _, _ in adjacency[current]:
                if neighbour not in assigned:
                    assigned[neighbour] = component
                    stack.append(neighbour)
    return assigned, component


def _cut_vertices_and_bridges(
    node_order: Sequence[NodeId],
    adjacency: Mapping[NodeId, Sequence[Tuple[NodeId, float, int]]],
    cancel_requested: CancelCallback,
) -> Tuple[set, set]:
    """Iterative Tarjan traversal, avoiding recursion limits on large graphs."""
    discovery: Dict[NodeId, int] = {}
    low: Dict[NodeId, int] = {}
    parent: Dict[NodeId, NodeId] = {}
    parent_edge: Dict[NodeId, int] = {}
    child_count: Dict[NodeId, int] = {}
    articulation = set()
    bridges = set()
    clock = 0

    for start in node_order:
        if start in discovery:
            continue
        clock += 1
        discovery[start] = low[start] = clock
        child_count[start] = 0
        stack: List[Tuple[NodeId, Any]] = [(start, iter(adjacency[start]))]
        while stack:
            _check_cancelled(cancel_requested)
            node, neighbours = stack[-1]
            try:
                neighbour, _, edge_index = next(neighbours)
            except StopIteration:
                stack.pop()
                if node not in parent:
                    if child_count[node] > 1:
                        articulation.add(node)
                    continue
                predecessor = parent[node]
                low[predecessor] = min(low[predecessor], low[node])
                if predecessor in parent and low[node] >= discovery[predecessor]:
                    articulation.add(predecessor)
                if low[node] > discovery[predecessor]:
                    bridges.add(parent_edge[node])
                continue

            if neighbour not in discovery:
                parent[neighbour] = node
                parent_edge[neighbour] = edge_index
                child_count[node] += 1
                child_count[neighbour] = 0
                clock += 1
                discovery[neighbour] = low[neighbour] = clock
                stack.append((neighbour, iter(adjacency[neighbour])))
            elif edge_index != parent_edge.get(node):
                low[node] = min(low[node], discovery[neighbour])
    return articulation, bridges


def _closeness(
    node_order: Sequence[NodeId],
    adjacency: Mapping[NodeId, Sequence[Tuple[NodeId, float, int]]],
    cancel_requested: CancelCallback,
) -> Dict[NodeId, float]:
    result: Dict[NodeId, float] = {}
    total_nodes = len(node_order)
    for source in node_order:
        distances = _dijkstra(source, adjacency, cancel_requested)
        reachable = len(distances) - 1
        total_distance = sum(distances.values())
        if total_nodes <= 1 or reachable == 0 or total_distance <= 0:
            result[source] = 0.0
        else:
            result[source] = (
                reachable / total_distance * reachable / (total_nodes - 1)
            )
    return result


def _dijkstra(
    source: NodeId,
    adjacency: Mapping[NodeId, Sequence[Tuple[NodeId, float, int]]],
    cancel_requested: CancelCallback,
) -> Dict[NodeId, float]:
    distances = {source: 0.0}
    counter = 0
    queue: List[Tuple[float, int, NodeId]] = [(0.0, counter, source)]
    while queue:
        _check_cancelled(cancel_requested)
        distance, _, node = heapq.heappop(queue)
        if distance > distances[node]:
            continue
        for neighbour, weight, _ in adjacency[node]:
            candidate = distance + weight
            if candidate < distances.get(neighbour, math.inf):
                distances[neighbour] = candidate
                counter += 1
                heapq.heappush(queue, (candidate, counter, neighbour))
    return distances


def _brandes_betweenness(
    node_order: Sequence[NodeId],
    adjacency: Mapping[NodeId, Sequence[Tuple[NodeId, float, int]]],
    cancel_requested: CancelCallback,
) -> Tuple[Dict[NodeId, float], Dict[int, float]]:
    node_score = {node: 0.0 for node in node_order}
    edge_score = {
        edge_index: 0.0
        for values in adjacency.values()
        for _, _, edge_index in values
    }
    for source in node_order:
        _check_cancelled(cancel_requested)
        predecessors: Dict[NodeId, List[Tuple[NodeId, int]]] = {
            node: [] for node in node_order
        }
        sigma = {node: 0.0 for node in node_order}
        sigma[source] = 1.0
        distances = {source: 0.0}
        stack: List[NodeId] = []
        queue: List[Tuple[float, int, NodeId]] = [(0.0, 0, source)]
        counter = 0
        settled = set()
        while queue:
            distance, _, node = heapq.heappop(queue)
            if node in settled:
                continue
            settled.add(node)
            stack.append(node)
            for neighbour, weight, edge_index in adjacency[node]:
                candidate = distance + weight
                previous = distances.get(neighbour, math.inf)
                if candidate < previous and not math.isclose(candidate, previous):
                    distances[neighbour] = candidate
                    counter += 1
                    heapq.heappush(queue, (candidate, counter, neighbour))
                    sigma[neighbour] = sigma[node]
                    predecessors[neighbour] = [(node, edge_index)]
                elif math.isclose(candidate, previous):
                    sigma[neighbour] += sigma[node]
                    predecessors[neighbour].append((node, edge_index))

        dependency = {node: 0.0 for node in node_order}
        while stack:
            node = stack.pop()
            if sigma[node] == 0:
                continue
            coefficient = (1.0 + dependency[node]) / sigma[node]
            for predecessor, edge_index in predecessors[node]:
                contribution = sigma[predecessor] * coefficient
                dependency[predecessor] += contribution
                edge_score[edge_index] += contribution
            if node != source:
                node_score[node] += dependency[node]

    n = len(node_order)
    if n > 2:
        node_scale = 1.0 / ((n - 1) * (n - 2))
        node_score = {node: value * node_scale for node, value in node_score.items()}
    else:
        node_score = {node: 0.0 for node in node_order}
    if n > 1:
        edge_scale = 1.0 / (n * (n - 1))
        edge_score = {edge: value * edge_scale for edge, value in edge_score.items()}
    else:
        edge_score = {edge: 0.0 for edge in edge_score}
    return node_score, edge_score


def _parse_frequency(
    value: Any, required: bool = False
) -> Tuple[float, Tuple[str, ...]]:
    text = "" if value is None else str(value).replace("\r\n", "\n")
    match = re.search(
        r"(?:^|\b)frequency\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        if required:
            raise TopologyAnalysisError(
                f"Node Frequency does not contain a numeric frequency=: {text!r}"
            )
        return 0.0, ()
    frequency = float(match.group(1))
    if not math.isfinite(frequency) or frequency < 0:
        raise TopologyAnalysisError("Node frequency must be finite and non-negative")
    sample_text = text[match.end():]
    samples = tuple(line.strip() for line in sample_text.splitlines() if line.strip())
    return frequency, samples


def _parse_mutation_distance(value: Any, edge_index: int) -> float:
    if value is None or str(value).strip() == "":
        return 1.0
    text = str(value).strip()
    match = re.fullmatch(
        r"(?:changes\s*=\s*)?([+]?(?:\d+(?:\.\d*)?|\.\d+))",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        raise TopologyAnalysisError(
            f"GML edge {edge_index} has a non-numeric Changes value: {text!r}"
        )
    distance = float(match.group(1))
    if not math.isfinite(distance) or distance <= 0:
        raise TopologyAnalysisError(
            f"GML edge {edge_index} mutation distance must be positive"
        )
    return distance


def _tokenize_gml(text: str) -> List[_Token]:
    tokens: List[_Token] = []
    index = 0
    length = len(text)
    while index < length:
        character = text[index]
        if character.isspace():
            index += 1
            continue
        if character == "#":
            newline = text.find("\n", index)
            index = length if newline < 0 else newline + 1
            continue
        if character in "[]":
            tokens.append(_Token(character, "bracket", index))
            index += 1
            continue
        if character == '"':
            start = index
            index += 1
            value: List[str] = []
            while index < length:
                character = text[index]
                if character == '"':
                    index += 1
                    break
                if character == "\\":
                    index += 1
                    if index >= length:
                        raise TopologyAnalysisError("Unterminated GML escape sequence")
                    escaped = text[index]
                    value.append({"n": "\n", "r": "\r", "t": "\t"}.get(escaped, escaped))
                    index += 1
                    continue
                value.append(character)
                index += 1
            else:
                raise TopologyAnalysisError(f"Unterminated GML string at offset {start}")
            tokens.append(_Token("".join(value), "string", start))
            continue
        start = index
        while index < length and not text[index].isspace() and text[index] not in "[]#":
            index += 1
        tokens.append(_Token(text[start:index], "atom", start))
    return tokens


def _parse_document(tokens: Sequence[_Token]) -> _GmlBlock:
    entries, position = _parse_entries(tokens, 0, expect_close=False)
    if position != len(tokens):
        raise TopologyAnalysisError("Unexpected trailing GML tokens")
    return _GmlBlock(tuple(entries))


def _parse_entries(
    tokens: Sequence[_Token], position: int, expect_close: bool
) -> Tuple[List[Tuple[str, Any]], int]:
    entries: List[Tuple[str, Any]] = []
    while position < len(tokens):
        token = tokens[position]
        if token.value == "]":
            if not expect_close:
                raise TopologyAnalysisError(f"Unexpected ] at offset {token.offset}")
            return entries, position + 1
        if token.kind != "atom" or token.value == "[":
            raise TopologyAnalysisError(f"Expected GML key at offset {token.offset}")
        key = token.value
        position += 1
        if position >= len(tokens):
            raise TopologyAnalysisError(f"Missing value for GML key {key!r}")
        value_token = tokens[position]
        if value_token.value == "[":
            nested, position = _parse_entries(tokens, position + 1, expect_close=True)
            value: Any = _GmlBlock(tuple(nested))
        elif value_token.value == "]":
            raise TopologyAnalysisError(f"Missing value for GML key {key!r}")
        else:
            value = (
                value_token.value
                if value_token.kind == "string"
                else _parse_atom(value_token.value)
            )
            position += 1
        entries.append((key, value))
    if expect_close:
        raise TopologyAnalysisError("Unclosed GML block")
    return entries, position


def _parse_atom(value: str) -> Any:
    if re.fullmatch(r"[+-]?\d+", value):
        try:
            return int(value)
        except ValueError:
            pass
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value):
        try:
            return float(value)
        except ValueError:
            pass
    return value


def _block_to_plain(block: _GmlBlock) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in block.entries:
        plain = _plain_value(value)
        if key not in result:
            result[key] = plain
        elif isinstance(result[key], list):
            result[key].append(plain)
        else:
            result[key] = [result[key], plain]
    return result


def _plain_value(value: Any) -> Any:
    return _block_to_plain(value) if isinstance(value, _GmlBlock) else value


def _check_cancelled(cancel_requested: CancelCallback) -> None:
    if cancel_requested is not None and cancel_requested():
        raise TopologyAnalysisCancelled("Topology analysis cancelled")


__all__ = [
    "EdgeMetrics",
    "GraphMetrics",
    "NodeMetrics",
    "TopologyAnalysisCancelled",
    "TopologyAnalysisError",
    "TopologyAnalysisResult",
    "TopologyEdge",
    "TopologyGraph",
    "TopologyNode",
    "analyze_gml",
    "analyze_topology",
    "parse_tcsbu_gml",
    "parse_tcsbu_gml_text",
]
