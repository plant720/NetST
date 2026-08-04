"""Adapter between NetST's aligned-FASTA workflow and supported McAN releases.

McAN consumes a mutation table, metadata and a site-mask file and writes a
GraphML network.  NetST consumes aligned FASTA and its bundled tcsBU viewer
expects the GML dialect emitted by fastHaN.  This module owns both conversions
so the rest of the analysis pipeline can treat McAN as another network engine.
"""

from __future__ import annotations

import csv
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from service.format_conversion_service import read_vcf, subset_metadata, subset_vcf


MAX_MCAN_SEQUENCE_LENGTH = 30000
_CANONICAL_BASES = frozenset("ACGTU-")
_GRAPHML_NAMESPACE = "http://graphml.graphdrawing.org/xmlns"


class McanAdapterError(RuntimeError):
    """Raised when McAN input or output cannot be adapted safely."""


@dataclass(frozen=True)
class McanOptions:
    """NetST and native McAN options extracted from the UI argument list."""

    threads: int = 8
    reference_name: str = ""
    exclude_ambiguous_sites: bool = False


@dataclass(frozen=True)
class McanPreparedInput:
    """Files and sample aliases required for one isolated McAN run."""

    mutation_file: str
    metadata_file: str
    site_mask_file: str
    sample_map_file: str
    output_directory: str
    alias_to_name: Dict[str, str]
    sequence_length: int
    included_site_count: int
    vcf_file: str = ""


@dataclass(frozen=True)
class McanVcfInput:
    """Original VCF and McAN six-column metadata selected in the UI."""

    vcf_file: str
    metadata_file: str


def parse_mcan_options(args: Sequence[str]) -> McanOptions:
    """Parse the small, allow-listed option set produced by NetST's dialog."""
    threads = 8
    reference_name = ""
    exclude_ambiguous_sites = False
    index = 0

    while index < len(args):
        option = args[index]
        if option in ("-t", "--nthread"):
            if index + 1 >= len(args):
                raise McanAdapterError("McAN thread option requires a value")
            try:
                threads = int(args[index + 1])
            except (TypeError, ValueError) as exc:
                raise McanAdapterError("McAN thread count must be an integer") from exc
            if not 1 <= threads <= 256:
                raise McanAdapterError("McAN thread count must be between 1 and 256")
            index += 2
        elif option == "--netst-reference":
            if index + 1 >= len(args):
                raise McanAdapterError("McAN reference option requires a sample name")
            reference_name = str(args[index + 1])
            index += 2
        elif option == "--netst-exclude-ambiguous":
            exclude_ambiguous_sites = True
            index += 1
        else:
            raise McanAdapterError(f"Unsupported McAN option: {option}")

    return McanOptions(threads, reference_name, exclude_ambiguous_sites)


def read_aligned_fasta(path: str) -> List[Tuple[str, str]]:
    """Read a simple aligned FASTA while preserving record order and names."""
    records: List[Tuple[str, str]] = []
    current_name = None
    sequence_lines: List[str] = []

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current_name is not None:
                    records.append((current_name, "".join(sequence_lines).upper()))
                current_name = line[1:]
                sequence_lines = []
            else:
                if current_name is None:
                    raise McanAdapterError("Aligned FASTA contains sequence data before a header")
                sequence_lines.append(line)

    if current_name is not None:
        records.append((current_name, "".join(sequence_lines).upper()))
    if not records:
        raise McanAdapterError("Aligned FASTA contains no sequences")
    if any(not name for name, _ in records):
        raise McanAdapterError("Aligned FASTA contains an empty sample name")
    if len({name for name, _ in records}) != len(records):
        raise McanAdapterError("Aligned FASTA contains duplicate sample names")

    sequence_length = len(records[0][1])
    if sequence_length == 0 or any(len(sequence) != sequence_length for _, sequence in records):
        raise McanAdapterError("McAN requires non-empty, equal-length aligned sequences")
    if sequence_length > MAX_MCAN_SEQUENCE_LENGTH:
        raise McanAdapterError(
            f"NetST's McAN adapter supports at most {MAX_MCAN_SEQUENCE_LENGTH} aligned sites; "
            f"the current alignment has {sequence_length}"
        )
    return records


def prepare_mcan_input(
    aligned_fasta: str,
    output_prefix: str,
    options: McanOptions,
    check_cancelled: Optional[Callable[[], None]] = None,
) -> McanPreparedInput:
    """Convert aligned sequences to mutation, metadata and site-mask files."""
    records = read_aligned_fasta(aligned_fasta)
    names = [name for name, _ in records]
    reference_name = options.reference_name or names[0]
    if reference_name not in names:
        raise McanAdapterError(f"McAN reference sample was not found: {reference_name}")

    reference_sequence = dict(records)[reference_name]
    sequence_length = len(reference_sequence)
    included_positions = _included_positions(records, options.exclude_ambiguous_sites)
    if not included_positions:
        raise McanAdapterError(
            "No sites remain for McAN after excluding ambiguous or missing bases"
        )

    run_directory = output_prefix + "_mcan"
    os.makedirs(run_directory, exist_ok=True)
    mutation_file = os.path.join(run_directory, "input.mutations.tsv")
    metadata_file = os.path.join(run_directory, "input.metadata.tsv")
    site_mask_file = os.path.join(run_directory, "site_mask.txt")
    sample_map_file = os.path.join(run_directory, "sample_map.csv")

    alias_to_name: Dict[str, str] = {}
    name_to_alias: Dict[str, str] = {}
    for record_index, (name, _) in enumerate(records, start=1):
        if check_cancelled is not None:
            check_cancelled()
        alias = f"S{record_index:07d}"
        alias_to_name[alias] = name
        name_to_alias[name] = alias

    with open(sample_map_file, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["mcan_alias", "sequence_name", "is_reference"])
        for name, _ in records:
            writer.writerow([name_to_alias[name], name, int(name == reference_name)])

    included_set = set(included_positions)
    with open(mutation_file, "w", encoding="utf-8", newline="") as handle:
        for name, sequence in records:
            if check_cancelled is not None:
                check_cancelled()
            mutations = []
            for position, (reference_base, sample_base) in enumerate(
                zip(reference_sequence, sequence), start=1
            ):
                if check_cancelled is not None and position % 1000 == 0:
                    check_cancelled()
                if position not in included_set:
                    continue
                ref = _mcan_base_token(reference_base)
                alt = _mcan_base_token(sample_base)
                if ref != alt:
                    # McAN's mutation reader allocates by counting SNP tokens.
                    # Encoding each aligned-column difference as SNP is both
                    # lossless for its distance calculation and avoids its
                    # mixed-indel allocation bug.
                    mutations.append(f"{position}(SNP:{ref}->{alt})")
            alias = name_to_alias[name]
            row = f"{alias}\t{alias}"
            if mutations:
                row += "\t" + ";".join(mutations)
            handle.write(row + "\n")

    with open(metadata_file, "w", encoding="utf-8", newline="") as handle:
        for name, _ in records:
            alias = name_to_alias[name]
            # McAN uses dates to orient equally plausible edges.  NetST FASTA
            # has no sampling-date field, so a shared neutral date avoids
            # inventing chronological information.
            handle.write(f"{alias}\t{alias}\t2000-01-01\t*\t*\t*\n")

    with open(site_mask_file, "w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(str(position) for position in included_positions) + "\n")

    return McanPreparedInput(
        mutation_file,
        metadata_file,
        site_mask_file,
        sample_map_file,
        run_directory,
        alias_to_name,
        sequence_length,
        len(included_positions),
    )


def prepare_mcan_vcf_input(
    source: McanVcfInput,
    output_prefix: str,
    selected_names: Sequence[str],
    check_cancelled: Optional[Callable[[], None]] = None,
) -> McanPreparedInput:
    """Subset a VCF/metadata pair and replace sample names with XML-safe aliases."""
    if not source.vcf_file or not os.path.isfile(source.vcf_file):
        raise McanAdapterError("The original VCF source file is unavailable")
    if not source.metadata_file or not os.path.isfile(source.metadata_file):
        raise McanAdapterError("McAN direct VCF analysis requires a metadata file")
    if not selected_names:
        raise McanAdapterError("No VCF samples were selected for McAN")
    if check_cancelled is not None:
        check_cancelled()

    vcf = read_vcf(source.vcf_file)
    positions = sorted({record.position for record in vcf.records})
    if positions[-1] > MAX_MCAN_SEQUENCE_LENGTH:
        raise McanAdapterError(
            f"NetST's McAN adapter supports VCF positions up to {MAX_MCAN_SEQUENCE_LENGTH}; "
            f"the input contains position {positions[-1]}"
        )

    run_directory = output_prefix + "_mcan"
    os.makedirs(run_directory, exist_ok=True)
    vcf_file = os.path.join(run_directory, "input.subset.vcf")
    metadata_file = os.path.join(run_directory, "input.metadata.tsv")
    site_mask_file = os.path.join(run_directory, "site_mask.txt")
    sample_map_file = os.path.join(run_directory, "sample_map.csv")

    name_to_alias = {
        name: f"S{index:07d}" for index, name in enumerate(selected_names, start=1)
    }
    alias_to_name = {alias: name for name, alias in name_to_alias.items()}
    subset_vcf(source.vcf_file, vcf_file, selected_names, name_to_alias)
    subset_metadata(source.metadata_file, metadata_file, selected_names, name_to_alias)

    with open(site_mask_file, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(str(position) for position in positions) + "\n")
    with open(sample_map_file, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["mcan_alias", "sequence_name", "is_reference"])
        for name in selected_names:
            writer.writerow([name_to_alias[name], name, 0])

    return McanPreparedInput(
        "",
        metadata_file,
        site_mask_file,
        sample_map_file,
        run_directory,
        alias_to_name,
        positions[-1],
        len(positions),
        vcf_file,
    )


def _included_positions(
    records: Iterable[Tuple[str, str]], exclude_ambiguous_sites: bool
) -> List[int]:
    sequences = [sequence for _, sequence in records]
    if not exclude_ambiguous_sites:
        return list(range(1, len(sequences[0]) + 1))
    return [
        position
        for position, column in enumerate(zip(*sequences), start=1)
        if all(base in _CANONICAL_BASES for base in column)
    ]


def convert_graphml_to_tcsbu_gml(
    graphml_file: str,
    gml_file: str,
    alias_to_name: Dict[str, str],
) -> None:
    """Convert McAN GraphML to the fastHaN-flavoured GML parsed by tcsBU."""
    if not os.path.isfile(graphml_file) or os.path.getsize(graphml_file) == 0:
        raise McanAdapterError("McAN GraphML output is missing or empty")

    try:
        root = ET.parse(graphml_file).getroot()
    except (ET.ParseError, OSError) as exc:
        raise McanAdapterError(f"Cannot read McAN GraphML output: {exc}") from exc

    namespace = {"g": _GRAPHML_NAMESPACE}
    key_names = {
        element.attrib.get("id", ""): element.attrib.get("attr.name", "")
        for element in root.findall("g:key", namespace)
    }
    graph = root.find("g:graph", namespace)
    if graph is None:
        raise McanAdapterError("McAN GraphML output does not contain a graph")

    node_ids: Dict[str, int] = {}
    node_rows = []
    for index, node in enumerate(graph.findall("g:node", namespace)):
        node_id = node.attrib.get("id", "")
        if not node_id or node_id in node_ids:
            raise McanAdapterError("McAN GraphML contains a missing or duplicate node ID")
        node_ids[node_id] = index
        data = _graphml_data(node, key_names, namespace)
        aliases = _graphml_sample_aliases(data)
        unknown_aliases = [alias for alias in aliases if alias not in alias_to_name]
        if unknown_aliases:
            raise McanAdapterError(
                "McAN GraphML contains unknown sample aliases: "
                + ", ".join(unknown_aliases[:5])
            )
        names = [alias_to_name[alias] for alias in aliases]
        if not names:
            raise McanAdapterError(f"McAN node {node_id or index} contains no samples")
        frequency = _positive_int(data.get("numOfVirus"), len(names))
        node_rows.append((index, frequency, names))

    if not node_rows:
        raise McanAdapterError("McAN GraphML output contains no nodes")

    edge_rows = []
    for edge in graph.findall("g:edge", namespace):
        source_id = edge.attrib.get("source", "")
        target_id = edge.attrib.get("target", "")
        if source_id not in node_ids or target_id not in node_ids:
            raise McanAdapterError("McAN GraphML edge refers to an unknown node")
        data = _graphml_data(edge, key_names, namespace)
        distance = _positive_int(data.get("distance"), 1)
        edge_rows.append((node_ids[source_id], node_ids[target_id], distance))

    with open(gml_file, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("graph [\n")
        handle.write("   directed 1\n")
        for node_id, frequency, names in node_rows:
            handle.write("   node [\n")
            handle.write("      data [\n")
            handle.write(f'         Frequency "frequency={float(frequency):.1f}\n')
            for name in names:
                handle.write(_single_line(name) + "\n")
            handle.write('"\n')
            handle.write("      ]\n")
            handle.write(f"      id {node_id}\n")
            handle.write("   ]\n")
        for source, target, distance in edge_rows:
            handle.write("   edge [\n")
            handle.write("      data [\n")
            handle.write(f'         Changes "{distance}"\n')
            handle.write("      ]\n")
            handle.write(f"      source {source}\n")
            handle.write(f"      target {target}\n")
            handle.write("   ]\n")
        handle.write("]\n")


def _graphml_data(element, key_names, namespace) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for data in element.findall("g:data", namespace):
        name = key_names.get(data.attrib.get("key", ""), data.attrib.get("key", ""))
        values[name] = data.text or ""
    return values


def _graphml_sample_aliases(data: Dict[str, str]) -> List[str]:
    """Read sample aliases emitted by supported McAN GraphML versions.

    McAN 1.2 used ``virus_name`` while 1.4.x uses
    ``virus$name@string``.  Accessions are an equivalent fallback because
    NetST deliberately writes the same private alias into both metadata
    columns before invoking McAN.
    """
    preferred_keys = (
        "virus_name",
        "virus$name@string",
        "virus_name@string",
        "virus$name",
        "virus$accession@string",
        "virus_accession",
    )
    raw_value = next((data[key] for key in preferred_keys if data.get(key)), "")
    if not raw_value:
        normalized = {
            re.sub(r"[^a-z0-9]", "", key.lower()): value
            for key, value in data.items()
            if value
        }
        for key in ("virusnamestring", "virusname", "virusaccessionstring",
                    "virusaccession"):
            if normalized.get(key):
                raw_value = normalized[key]
                break
    return [value.strip() for value in raw_value.split(";") if value.strip()]


def _positive_int(value: str, fallback: int) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = fallback
    return max(1, number)


def _single_line(value: str) -> str:
    return str(value).replace("\r", "_").replace("\n", "_")


def _mcan_base_token(base: str) -> str:
    """Return a token safe for McAN's ``REF->ALT`` sscanf parser.

    A reference gap cannot be written literally because McAN treats the first
    hyphen as the arrow delimiter.  Alphanumeric tokens preserve equality and
    distance semantics without relying on its fragile delimiter parsing.
    """
    if base == "-":
        return "GAP"
    if len(base) == 1 and base.isascii() and base.isalnum():
        return base.upper()
    return "HEX" + "_".join(f"{ord(character):X}" for character in base)
