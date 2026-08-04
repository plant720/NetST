"""Internal, NumPy-accelerated RMST haplotype-network engine for NetST.

RMST (randomized minimum spanning tree) reconstructs the union of links that
can occur in a minimum spanning tree.  NetST provides a deterministic exact
mode and the repeated, seeded randomized mode described by Paradis (2018).

The performance-sensitive distance and graph operations use dense NumPy arrays,
while this module preserves NetST's FASTA/metadata adapter, public result types,
cancellation support, and tcsBU/JSON/TSV outputs.  Edge distances are
uncorrected mutation counts over retained aligned sites.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import json
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from service.format_conversion_service import FormatConversionError, read_fasta


CancelCallback = Optional[Callable[[], bool]]


class RMSTError(ValueError):
    """Raised when RMST inputs or options are invalid."""


class RMSTCancelled(RuntimeError):
    """Raised when the caller cancels an RMST calculation."""


@dataclass(frozen=True)
class RMSTOptions:
    method: str = "exact"
    iterations: int = 100
    seed: int = 42
    exclude_ambiguous_sites: bool = True


@dataclass(frozen=True)
class RMSTNode:
    node_id: int
    haplotypes: Tuple[str, ...]
    samples: Tuple[str, ...]
    sequence: str

    @property
    def label(self) -> str:
        return "/".join(self.haplotypes)


@dataclass(frozen=True)
class RMSTEdge:
    source: int
    target: int
    distance: int
    edge_type: str
    count: Optional[int] = None
    frequency: Optional[float] = None


@dataclass(frozen=True)
class RMSTResult:
    method: str
    alignment_length: int
    included_site_count: int
    excluded_site_count: int
    nodes: Tuple[RMSTNode, ...]
    edges: Tuple[RMSTEdge, ...]
    completed_iterations: Optional[int] = None
    seed: Optional[int] = None
    warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class _WeightedEdge:
    source: int
    target: int
    distance: int


class _NumpyDisjointSet:
    """Disjoint-set forest sharing its parent array with vectorized lookups."""

    __slots__ = ("parents", "ranks")

    def __init__(self, parents: np.ndarray) -> None:
        self.parents = parents
        self.ranks = np.zeros(len(parents), dtype=np.int64)

    def find(self, item: int) -> int:
        parents = self.parents
        while parents[item] != item:
            parents[item] = parents[parents[item]]
            item = int(parents[item])
        return item

    def union(self, left: int, right: int) -> bool:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return False
        if self.ranks[left_root] < self.ranks[right_root]:
            left_root, right_root = right_root, left_root
        self.parents[right_root] = left_root
        if self.ranks[left_root] == self.ranks[right_root]:
            self.ranks[left_root] += 1
        return True


def parse_rmst_options(args: Sequence[str]) -> RMSTOptions:
    """Parse the small allow-listed option set emitted by NetST's dialog."""
    method = "exact"
    iterations = 100
    seed = 42
    exclude_ambiguous = True
    seen = set()
    index = 0
    while index < len(args):
        option = args[index]
        if option in seen:
            raise RMSTError(f"Duplicate RMST option: {option}")
        seen.add(option)
        if option == "--netst-include-ambiguous":
            exclude_ambiguous = False
            index += 1
            continue
        if option not in {"--method", "--iterations", "--seed"}:
            raise RMSTError(f"Unsupported RMST option: {option}")
        if index + 1 >= len(args):
            raise RMSTError(f"RMST option requires a value: {option}")
        value = args[index + 1]
        if option == "--method":
            method = value.lower()
            if method not in {"exact", "randomized"}:
                raise RMSTError("RMST method must be 'exact' or 'randomized'")
        elif option == "--iterations":
            iterations = _bounded_integer(value, "iterations", 1, 1_000)
        else:
            seed = _bounded_integer(value, "seed", -2_147_483_648, 2_147_483_647)
        index += 2
    return RMSTOptions(method, iterations, seed, exclude_ambiguous)


def exact_rmst_edges(
    distances: Sequence[Sequence[int]],
    cancel_requested: CancelCallback = None,
) -> Tuple[Tuple[_WeightedEdge, ...], Tuple[_WeightedEdge, ...]]:
    """Return a stable MST backbone and all other MST-compatible links.

    The complete graph remains in compact NumPy arrays.  Component membership
    for an equal-distance level is evaluated in one vectorized snapshot before
    scalar union operations select the stable plotting backbone.
    """
    matrix = _validated_distance_matrix(distances)
    node_count = matrix.shape[0]
    if node_count < 2:
        return (), ()

    rows, columns = np.triu_indices(node_count, 1)
    weights = matrix[rows, columns]
    order = np.argsort(weights, kind="stable")
    rows = rows[order]
    columns = columns[order]
    weights = weights[order]

    boundaries = np.flatnonzero(np.diff(weights)) + 1
    starts = np.concatenate(([0], boundaries))
    stops = np.concatenate((boundaries, [len(weights)]))

    parents = np.arange(node_count, dtype=np.int64)
    components = _NumpyDisjointSet(parents)
    backbone: List[_WeightedEdge] = []
    alternatives: List[_WeightedEdge] = []

    for start, stop in zip(starts, stops):
        _check_cancelled(cancel_requested)
        level_rows = rows[start:stop]
        level_columns = columns[start:stop]
        compatible = (
            _find_roots(parents, level_rows)
            != _find_roots(parents, level_columns)
        )
        distance = int(weights[start])
        for source, target in zip(
            level_rows[compatible].tolist(),
            level_columns[compatible].tolist(),
        ):
            edge = _WeightedEdge(source, target, distance)
            if components.union(source, target):
                backbone.append(edge)
            else:
                alternatives.append(edge)
        if len(backbone) == node_count - 1:
            break

    if len(backbone) != node_count - 1:
        raise RMSTError("RMST distance graph is disconnected")
    return tuple(backbone), tuple(alternatives)


def randomized_rmst_edges(
    distances: Sequence[Sequence[int]],
    iterations: int,
    seed: int,
    cancel_requested: CancelCallback = None,
) -> Tuple[Tuple[_WeightedEdge, ...], Tuple[_WeightedEdge, ...], Dict[Tuple[int, int], int]]:
    """Sample stable Kruskal trees after seeded permutations of node order."""
    matrix = _validated_distance_matrix(distances)
    node_count = matrix.shape[0]
    if node_count < 2:
        return (), (), {}
    if iterations < 1 or iterations > 1_000:
        raise RMSTError("RMST iterations must be between 1 and 1000")
    edge_evaluations = node_count * (node_count - 1) // 2 * iterations
    if edge_evaluations > 50_000_000:
        raise RMSTError(
            "RMST randomized workload is too large; reduce the haplotype count "
            "or iteration count"
        )

    rows, columns = np.triu_indices(node_count, 1)
    weights = matrix[rows, columns]
    # NetST historically accepts signed 32-bit seeds, while NumPy rejects
    # negative integers.  Preserve the public range with a stable uint32 map.
    generator = np.random.default_rng(seed & 0xFFFFFFFF)
    counts: Dict[Tuple[int, int], int] = {}
    distances_by_pair: Dict[Tuple[int, int], int] = {}
    last_tree: Tuple[_WeightedEdge, ...] = ()

    for _ in range(iterations):
        _check_cancelled(cancel_requested)
        permutation = generator.permutation(node_count)
        position = np.empty(node_count, dtype=np.int64)
        position[permutation] = np.arange(node_count, dtype=np.int64)
        last_tree = _kruskal_permuted(
            node_count, rows, columns, weights, position
        )
        for edge in last_tree:
            pair = (edge.source, edge.target)
            counts[pair] = counts.get(pair, 0) + 1
            distances_by_pair[pair] = edge.distance

    backbone_pairs = {(edge.source, edge.target) for edge in last_tree}
    alternatives = tuple(
        _WeightedEdge(source, target, distances_by_pair[(source, target)])
        for source, target in sorted(counts)
        if (source, target) not in backbone_pairs
    )
    return last_tree, alternatives, counts


def build_rmst_network(
    haplotype_fasta: str,
    metadata_csv: str,
    output_prefix: str,
    options: RMSTOptions = RMSTOptions(),
    cancel_requested: CancelCallback = None,
) -> RMSTResult:
    """Build RMST outputs from NetST haplotypes and sample assignments."""
    _check_cancelled(cancel_requested)
    records = _read_haplotypes(haplotype_fasta)
    samples_by_haplotype = _read_sample_assignments(metadata_csv)
    unknown = sorted(set(samples_by_haplotype) - {name for name, _ in records})
    if unknown:
        raise RMSTError(
            "Metadata refers to unknown haplotypes: " + ", ".join(unknown[:5])
        )
    missing = [name for name, _ in records if not samples_by_haplotype.get(name)]
    if missing:
        raise RMSTError(
            "No sample assignment found for haplotypes: " + ", ".join(missing[:5])
        )

    alignment_length = len(records[0][1])
    included_sites = _included_sites(records, options.exclude_ambiguous_sites)
    if not included_sites:
        raise RMSTError(
            "No aligned sites remain for RMST after ambiguous-site filtering"
        )
    nodes = _collapse_haplotypes(records, samples_by_haplotype, included_sites)
    warnings: List[str] = []
    if len(nodes) < len(records):
        warnings.append(
            f"{len(records) - len(nodes)} haplotype(s) became identical after site filtering "
            "and were merged for RMST"
        )
    limit = 500 if options.method == "randomized" else 1_000
    if len(nodes) > limit:
        raise RMSTError(
            f"RMST {options.method} mode supports at most {limit} retained haplotypes; "
            f"received {len(nodes)}"
        )

    matrix = _mutation_distance_matrix(nodes, cancel_requested)
    completed_iterations: Optional[int] = None
    seed: Optional[int] = None
    if options.method == "exact":
        backbone, alternatives = exact_rmst_edges(matrix, cancel_requested)
        counts: Dict[Tuple[int, int], int] = {}
    elif options.method == "randomized":
        backbone, alternatives, counts = randomized_rmst_edges(
            matrix, options.iterations, options.seed, cancel_requested
        )
        completed_iterations = options.iterations
        seed = options.seed
    else:
        raise RMSTError("RMST method must be 'exact' or 'randomized'")

    edges: List[RMSTEdge] = []
    for edge_type, weighted_edges in (
        ("backbone", backbone), ("alternative", alternatives)
    ):
        for edge in weighted_edges:
            count = counts.get((edge.source, edge.target)) if counts else None
            edges.append(RMSTEdge(
                source=edge.source,
                target=edge.target,
                distance=edge.distance,
                edge_type=edge_type,
                count=count,
                frequency=(count / options.iterations) if count is not None else None,
            ))

    result = RMSTResult(
        method=options.method,
        alignment_length=alignment_length,
        included_site_count=len(included_sites),
        excluded_site_count=alignment_length - len(included_sites),
        nodes=nodes,
        edges=tuple(edges),
        completed_iterations=completed_iterations,
        seed=seed,
        warnings=tuple(warnings),
    )
    _write_tcsbu_gml(output_prefix + ".gml", result)
    _write_json(output_prefix + "_rmst.json", result, options)
    _write_tsv(output_prefix + "_rmst.tsv", result)
    return result


def _read_haplotypes(path: str) -> List[Tuple[str, str]]:
    try:
        fasta_records = read_fasta(path)
    except (OSError, FormatConversionError) as exc:
        raise RMSTError(f"Cannot read RMST haplotype FASTA: {exc}") from exc
    records = [(record.name, record.sequence.upper().replace("U", "T"))
               for record in fasta_records]
    if not records:
        raise RMSTError("RMST haplotype FASTA is empty")
    length = len(records[0][1])
    if length == 0 or any(len(sequence) != length for _, sequence in records):
        raise RMSTError("RMST requires non-empty, equal-length aligned haplotypes")
    if len({name for name, _ in records}) != len(records):
        raise RMSTError("RMST haplotype names must be unique")
    return records


def _read_sample_assignments(path: str) -> Dict[str, List[str]]:
    assignments: Dict[str, List[str]] = {}
    seen_samples = set()
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or not {
                "sequence_name", "haplotype"
            }.issubset(reader.fieldnames):
                raise RMSTError(
                    "RMST metadata requires sequence_name and haplotype columns"
                )
            for row_number, row in enumerate(reader, start=2):
                sample = (row.get("sequence_name") or "").strip()
                haplotype = (row.get("haplotype") or "").strip()
                if not sample or not haplotype:
                    raise RMSTError(
                        f"RMST metadata has an empty sample or haplotype at row {row_number}"
                    )
                if sample in seen_samples:
                    raise RMSTError(f"Duplicate sample in RMST metadata: {sample}")
                seen_samples.add(sample)
                assignments.setdefault(haplotype, []).append(sample)
    except OSError as exc:
        raise RMSTError(f"Cannot read RMST metadata: {exc}") from exc
    if not seen_samples:
        raise RMSTError("RMST metadata contains no samples")
    return assignments


def _included_sites(
    records: Sequence[Tuple[str, str]], exclude_ambiguous: bool
) -> Tuple[int, ...]:
    if not exclude_ambiguous:
        return tuple(range(len(records[0][1])))
    canonical = frozenset("ACGT-")
    return tuple(
        index for index, column in enumerate(zip(*(sequence for _, sequence in records)))
        if all(base in canonical for base in column)
    )


def _collapse_haplotypes(
    records: Sequence[Tuple[str, str]],
    samples_by_haplotype: Dict[str, List[str]],
    sites: Sequence[int],
) -> Tuple[RMSTNode, ...]:
    groups: Dict[str, Dict[str, List[str]]] = {}
    for haplotype, sequence in records:
        retained = "".join(sequence[index] for index in sites)
        group = groups.setdefault(retained, {"haplotypes": [], "samples": []})
        group["haplotypes"].append(haplotype)
        group["samples"].extend(samples_by_haplotype[haplotype])
    return tuple(
        RMSTNode(
            node_id=index,
            haplotypes=tuple(group["haplotypes"]),
            samples=tuple(group["samples"]),
            sequence=sequence,
        )
        for index, (sequence, group) in enumerate(groups.items())
    )


def _mutation_distance_matrix(
    nodes: Sequence[RMSTNode], cancel_requested: CancelCallback
) -> np.ndarray:
    """Compute all Hamming distances with bounded-memory matrix products."""
    size = len(nodes)
    if size == 0:
        return np.zeros((0, 0), dtype=np.int64)

    sequence_length = len(nodes[0].sequence)
    if sequence_length == 0:
        return np.zeros((size, size), dtype=np.int64)
    joined = "".join(node.sequence for node in nodes)
    try:
        raw = np.frombuffer(
            joined.encode("ascii"),
            dtype=np.uint8,
        ).reshape(size, sequence_length)
        symbols = np.flatnonzero(np.bincount(raw.ravel(), minlength=256))
    except UnicodeEncodeError:
        raw = np.frombuffer(
            joined.encode("utf-32le"),
            dtype="<u4",
        ).reshape(size, sequence_length)
        symbols = np.unique(raw)
    agreements = np.zeros((size, size), dtype=np.float64)

    # Keep temporary one-hot arrays bounded even for long alignments.
    for start in range(0, sequence_length, 8192):
        _check_cancelled(cancel_requested)
        block = raw[:, start:start + 8192]
        for symbol in symbols:
            _check_cancelled(cancel_requested)
            one_hot = (block == symbol).astype(np.float64)
            agreements += one_hot @ one_hot.T

    distances = sequence_length - agreements
    distances = np.rint((distances + distances.T) / 2.0).astype(np.int64)
    np.fill_diagonal(distances, 0)
    return distances


def _validated_distance_matrix(
    distances: Sequence[Sequence[int]],
) -> np.ndarray:
    if len(distances) == 0:
        return np.zeros((0, 0), dtype=np.int64)
    try:
        raw = np.asarray(distances)
        matrix = np.asarray(distances, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise RMSTError(
            "RMST distances must be non-negative integers"
        ) from exc
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise RMSTError("RMST distance matrix must be square")
    if raw.dtype == np.bool_ or (
        raw.dtype == object
        and any(isinstance(value, (bool, np.bool_)) for value in raw.flat)
    ):
        raise RMSTError("RMST distances must be non-negative integers")
    if not np.all(np.isfinite(matrix)):
        raise RMSTError("RMST distances must be finite")
    if np.any(np.diag(matrix) != 0.0):
        raise RMSTError("RMST distance matrix diagonal must be zero")
    if not np.array_equal(matrix, matrix.T):
        raise RMSTError("RMST distance matrix must be symmetric")
    if np.any(matrix < 0.0) or np.any(matrix != np.floor(matrix)):
        raise RMSTError("RMST distances must be non-negative integers")
    if np.any(matrix > np.iinfo(np.int64).max):
        raise RMSTError("RMST distances are too large")
    return matrix.astype(np.int64, copy=False)


def _find_roots(parents: np.ndarray, nodes: np.ndarray) -> np.ndarray:
    """Return union-find roots for many nodes without mutating the snapshot."""
    roots = nodes
    ancestors = parents[roots]
    while np.any(ancestors != roots):
        roots = ancestors
        ancestors = parents[roots]
    return roots


def _kruskal_permuted(
    node_count: int,
    rows: np.ndarray,
    columns: np.ndarray,
    weights: np.ndarray,
    position: np.ndarray,
) -> Tuple[_WeightedEdge, ...]:
    """Build one MST with equal weights ordered by a node permutation."""
    row_positions = position[rows]
    column_positions = position[columns]
    low = np.minimum(row_positions, column_positions)
    high = np.maximum(row_positions, column_positions)
    tie_order = (
        low * (2 * node_count - low - 1) // 2
        + (high - low - 1)
    )
    order = np.lexsort((tie_order, weights))

    parents = list(range(node_count))

    def find(item: int) -> int:
        while parents[item] != item:
            parents[item] = parents[parents[item]]
            item = parents[item]
        return item

    tree: List[_WeightedEdge] = []
    for source, target, distance in zip(
        rows[order].tolist(),
        columns[order].tolist(),
        weights[order].tolist(),
    ):
        source_root = find(source)
        target_root = find(target)
        if source_root == target_root:
            continue
        parents[target_root] = source_root
        tree.append(_WeightedEdge(source, target, int(distance)))
        if len(tree) == node_count - 1:
            return tuple(tree)
    raise RMSTError("RMST distance graph is disconnected")


def _write_tcsbu_gml(path: str, result: RMSTResult) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("graph [\n")
        handle.write("   directed 0\n")
        for node in result.nodes:
            handle.write("   node [\n")
            handle.write("      data [\n")
            handle.write(f'         Frequency "frequency={float(len(node.samples)):.1f}\n')
            for sample in node.samples:
                handle.write(_safe_gml_text(sample) + "\n")
            handle.write('"\n')
            handle.write("      ]\n")
            handle.write(f"      id {node.node_id}\n")
            handle.write(f'      label "{_safe_gml_text(node.label)}"\n')
            handle.write("   ]\n")
        for edge in result.edges:
            handle.write("   edge [\n")
            handle.write("      data [\n")
            handle.write(f'         Changes "{edge.distance}"\n')
            handle.write("      ]\n")
            handle.write(f"      source {edge.source}\n")
            handle.write(f"      target {edge.target}\n")
            handle.write("   ]\n")
        handle.write("]\n")


def _write_json(path: str, result: RMSTResult, options: RMSTOptions) -> None:
    payload = {
        "schema": "netst.rmst.v1",
        "algorithm": "RMST",
        "distance": "uncorrected_mutation_count",
        "options": asdict(options),
        "alignment_length": result.alignment_length,
        "included_site_count": result.included_site_count,
        "excluded_site_count": result.excluded_site_count,
        "completed_iterations": result.completed_iterations,
        "seed": result.seed,
        "warnings": list(result.warnings),
        "nodes": [asdict(node) | {"label": node.label} for node in result.nodes],
        "edges": [asdict(edge) for edge in result.edges],
    }
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_tsv(path: str, result: RMSTResult) -> None:
    node_by_id = {node.node_id: node for node in result.nodes}
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow([
            "source", "target", "distance", "edge_type", "count", "frequency",
            "source_haplotypes", "target_haplotypes",
        ])
        for edge in result.edges:
            writer.writerow([
                edge.source, edge.target, edge.distance, edge.edge_type,
                "" if edge.count is None else edge.count,
                "" if edge.frequency is None else f"{edge.frequency:.6f}",
                ";".join(node_by_id[edge.source].haplotypes),
                ";".join(node_by_id[edge.target].haplotypes),
            ])


def _safe_gml_text(value: str) -> str:
    return value.replace("\\", "_").replace('"', "_").replace("\r", "_").replace("\n", "_")


def _bounded_integer(value: str, name: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RMSTError(f"RMST {name} must be an integer") from exc
    if parsed < minimum or parsed > maximum:
        raise RMSTError(f"RMST {name} must be between {minimum} and {maximum}")
    return parsed


def _check_cancelled(cancel_requested: CancelCallback) -> None:
    if cancel_requested is not None and cancel_requested():
        raise RMSTCancelled("RMST analysis cancelled")
