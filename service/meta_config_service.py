"""Build the multi-ring metadata config consumed by tcsBU's loadMetaConfig.

For each node of a tcsBU GML, this aggregates the visualized traits over the
node's samples into ready-to-draw rings: a discrete trait becomes category
segments (proportional pie) coloured from the schema; a continuous trait becomes
one solid colour from the node's mean value on a gradient. tcsBU draws these as
concentric rings (group innermost). All name matching happens here, so the
browser side never has to reconcile sample-name normalization.
"""

from __future__ import annotations

from collections import Counter
import math
import re
from typing import Dict, List, Mapping, Optional, Sequence

from model.trait_schema import CONTINUOUS, DISCRETE, UNASSIGNED_COLOR
from service.topology_analysis_service import parse_tcsbu_gml

DEFAULT_GROUP_COLOR = "#6BAB30"

def _clamp8(value: float) -> int:
    return max(0, min(255, int(round(value))))


def _parse_hex(color: str) -> Optional[tuple]:
    text = str(color or "").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        return None
    try:
        return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
    except ValueError:
        return None


def _lerp_color(low: str, high: str, fraction: float) -> str:
    lo = _parse_hex(low) or (189, 189, 189)
    hi = _parse_hex(high) or (0, 0, 0)
    fraction = 0.0 if fraction < 0 else 1.0 if fraction > 1 else fraction
    return "#{:02X}{:02X}{:02X}".format(
        _clamp8(lo[0] + (hi[0] - lo[0]) * fraction),
        _clamp8(lo[1] + (hi[1] - lo[1]) * fraction),
        _clamp8(lo[2] + (hi[2] - lo[2]) * fraction),
    )


def _numeric(value: str) -> Optional[float]:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _tcsbu_sample_id(value: str) -> str:
    """Match the browser-side sample-id normalization used by tcsBU."""
    normalized = re.sub(r"[^A-Za-z0-9_]", "_", str(value or ""))
    if normalized[:1].isdigit():
        normalized = "L" + normalized
    return normalized


def build_meta_config(
    gml_file: str,
    traits_spec: Sequence[Mapping],
    sample_values: Mapping[str, Mapping[str, str]],
    ring_ratio: float = 0.5,
) -> Dict:
    """Return the tcsBU metadata config for a GML network.

    Args:
        gml_file: Path to a tcsBU-dialect GML.
        traits_spec: Visualized traits, group first. Each item has ``name``,
            ``kind``; discrete items carry ``colors`` ({category: hex}, in
            global order); continuous items carry ``gradient`` ([low, high]) and
            optionally ``vmin``/``vmax``.
        sample_values: ``{sample_name: {trait_name: value}}``.
        ring_ratio: Ring width as a fraction of node radius.
    """
    graph = parse_tcsbu_gml(gml_file)
    network_samples = {
        sample
        for node in graph.nodes
        for sample in node.samples
    }

    # Fill missing continuous ranges from the data so gradients span the values.
    specs = [dict(spec) for spec in traits_spec]
    for spec in specs:
        if spec.get("kind") != CONTINUOUS:
            continue
        if spec.get("vmin") is None or spec.get("vmax") is None:
            numbers = [
                _numeric(sample_values.get(sample, {}).get(spec["name"], ""))
                for sample in network_samples
            ]
            numbers = [n for n in numbers if n is not None]
            if numbers:
                spec.setdefault("vmin", min(numbers))
                spec.setdefault("vmax", max(numbers))
            else:
                spec.setdefault("vmin", 0.0)
                spec.setdefault("vmax", 1.0)

    nodes: Dict[str, Dict] = {}
    for node in graph.nodes:
        # Median vectors / transition nodes have no samples and are not
        # haplotypes.  Keep their classic small marker instead of surrounding
        # them with a stack of "missing" metadata rings.
        if node.is_intermediate:
            nodes[str(node.id)] = {"rings": []}
            continue
        rings: List[Dict] = []
        samples = node.samples
        for spec in specs:
            name = spec["name"]
            if spec.get("kind") == CONTINUOUS:
                parsed_values = [
                    _numeric(sample_values.get(s, {}).get(name, ""))
                    for s in samples
                ]
                values = [v for v in parsed_values if v is not None]
                gradient = spec.get("gradient") or ["#BDBDBD", "#000000"]
                vmin = float(spec.get("vmin", 0.0))
                vmax = float(spec.get("vmax", 1.0))
                span = vmax - vmin
                value_counts = Counter(values)
                segments = []
                # Draw continuous sectors monotonically around the ring. The
                # sample order in the GML must not make light/dark colours
                # alternate when values are otherwise ordered numerically.
                for value in sorted(value_counts):
                    count = value_counts[value]
                    fraction = 0.5 if span == 0 else (value - vmin) / span
                    segments.append({
                        "label": value,
                        "value": count,
                        "color": _lerp_color(
                            gradient[0], gradient[1], fraction),
                    })
                missing_count = len(parsed_values) - len(values)
                if missing_count:
                    segments.append({
                        "label": "",
                        "value": missing_count,
                        "color": "#FFFFFF",
                    })
                if values:
                    mean = sum(values) / len(values)
                    fraction = 0.5 if span == 0 else (mean - vmin) / span
                    color = _lerp_color(gradient[0], gradient[1], fraction)
                else:
                    mean = None
                    color = "#FFFFFF"
                if not segments:
                    segments = [{
                        "label": "",
                        "value": 1,
                        "color": "#FFFFFF",
                    }]
                rings.append({
                    "kind": "continuous",
                    "trait": name,
                    "color": color,
                    "value": mean,
                    "segments": segments,
                })
            else:
                colors = spec.get("colors") or {}
                fallback = DEFAULT_GROUP_COLOR if spec.get("group") else UNASSIGNED_COLOR
                counts = Counter(
                    (sample_values.get(s, {}).get(name, "") or "").strip()
                    for s in samples
                )
                # Order segments by the trait's global colour order, then any
                # categories the schema did not colour (blank included).
                ordered = [c for c in colors if counts.get(c)]
                ordered += [c for c in counts if c and c not in colors]
                segments = [
                    {
                        "label": c,
                        "value": counts[c],
                        "color": colors.get(c, fallback),
                    }
                    for c in ordered
                ]
                blank = counts.get("", 0)
                if blank:
                    segments.append({
                        "label": "",
                        "value": blank,
                        "color": fallback,
                    })
                if not segments:
                    segments = [{
                        "label": "",
                        "value": 1,
                        "color": fallback,
                    }]
                rings.append({"kind": "discrete", "trait": name, "segments": segments})
        nodes[str(node.id)] = {"rings": rings}

    legend_traits: List[Dict] = []
    for spec in specs:
        name = spec["name"]
        entry = {
            "name": name,
            "kind": spec.get("kind", DISCRETE),
            "group": bool(spec.get("group")),
        }
        if entry["kind"] == CONTINUOUS:
            entry.update({
                "gradient": list(
                    spec.get("gradient") or ["#BDBDBD", "#000000"]),
                "vmin": spec.get("vmin", 0.0),
                "vmax": spec.get("vmax", 1.0),
            })
        else:
            colors = spec.get("colors") or {}
            observed = {
                str(sample_values.get(sample, {}).get(name, "") or "").strip()
                for sample in network_samples
            }
            entry["categories"] = [
                {"label": category, "color": color}
                for category, color in colors.items()
                if category in observed
            ]
            entry["has_missing"] = any(
                not str(sample_values.get(sample, {}).get(name, "") or "").strip()
                for sample in network_samples
            )
        legend_traits.append(entry)

    return {
        "ring_ratio": ring_ratio,
        "traits": legend_traits,
        "nodes": nodes,
        # tcsBU normalizes GML labels before putting them in its grids.  Export
        # the values under those same ids so edits in the standalone sidebar
        # can immediately rebuild the corresponding metadata rings.
        "sample_values": {
            _tcsbu_sample_id(sample): {
                spec["name"]: str(
                    sample_values.get(sample, {}).get(spec["name"], "") or ""
                )
                for spec in specs
            }
            for sample in network_samples
        },
    }
