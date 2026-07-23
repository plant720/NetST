"""Sequence-file conversion for FASTA, NEXUS, PHYLIP and sample VCF.

VCF contains variants rather than complete sequences.  Consequently VCF to
FASTA/PHYLIP produces a variable-site alignment unless a reference FASTA is
provided.  With a reference, non-overlapping VCF records are applied to build
a full-length alignment while preserving indels as gap-padded blocks.
"""

from __future__ import annotations

import csv
import gzip
import math
import os
import re
import shlex
import tempfile
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from model.taxon_data import TaxonData


class FormatConversionError(ValueError):
    """Raised for malformed input or a conversion that would lose structure."""


@dataclass(frozen=True)
class SequenceRecord:
    name: str
    sequence: str


@dataclass(frozen=True)
class VcfRecord:
    chrom: str
    position: int
    identifier: str
    reference: str
    alternates: Tuple[str, ...]
    quality: str
    filter_value: str
    info: str
    format_keys: Tuple[str, ...]
    sample_fields: Tuple[str, ...]


@dataclass(frozen=True)
class VcfData:
    samples: Tuple[str, ...]
    records: Tuple[VcfRecord, ...]
    headers: Tuple[str, ...]


@dataclass(frozen=True)
class MetadataEntry:
    sample_name: str
    discrete_trait: str = ""
    continuous_trait: str = "0"


@dataclass(frozen=True)
class VcfImportResult:
    taxons: Tuple[TaxonData, ...]
    samples: Tuple[str, ...]
    variant_records: int
    alignment_length: int
    full_length: bool
    warnings: Tuple[str, ...] = ()


_IUPAC = {
    frozenset(("A", "G")): "R",
    frozenset(("C", "T")): "Y",
    frozenset(("G", "C")): "S",
    frozenset(("A", "T")): "W",
    frozenset(("G", "T")): "K",
    frozenset(("A", "C")): "M",
}

_NAME_HEADERS = {
    "sample", "sampleid", "sample_id", "name", "sequence", "sequence_name",
    "samplename", "sample_name", "accession", "accessionid", "accession_id",
    "strain", "strainname", "strain_name",
}
_DISCRETE_HEADERS = {
    "group", "population", "country", "location", "region", "discrete",
    "discrete_trait", "trait", "state", "province", "city", "locality",
}
_CONTINUOUS_HEADERS = {
    "value", "continuous", "continuous_trait", "time", "numeric_trait",
}


def detect_format(path: str) -> str:
    lower = path.lower()
    if lower.endswith((".vcf", ".vcf.gz")):
        return "vcf"
    if lower.endswith((".phy", ".phylip")):
        return "phylip"
    if lower.endswith((".nex", ".nexus", ".nxs")):
        return "nexus"
    if lower.endswith((".fa", ".fas", ".fasta", ".fna", ".ffn")):
        return "fasta"
    raise FormatConversionError(f"Cannot infer the file format from: {path}")


def read_fasta(path: str) -> List[SequenceRecord]:
    records: List[SequenceRecord] = []
    name: Optional[str] = None
    sequence_lines: List[str] = []
    with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    records.append(SequenceRecord(name, "".join(sequence_lines).upper()))
                name = line[1:].strip()
                if not name:
                    raise FormatConversionError(f"Empty FASTA header at line {line_number}")
                sequence_lines = []
            else:
                if name is None:
                    raise FormatConversionError(
                        f"FASTA sequence appears before the first header at line {line_number}"
                    )
                sequence_lines.append(re.sub(r"\s+", "", line))
    if name is not None:
        records.append(SequenceRecord(name, "".join(sequence_lines).upper()))
    _validate_sequence_records(records)
    return records


def write_fasta(path: str, records: Sequence[SequenceRecord], line_width: int = 80) -> None:
    _validate_sequence_records(records)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(f">{_single_line(record.name)}\n")
            sequence = record.sequence.upper()
            for offset in range(0, len(sequence), max(1, line_width)):
                handle.write(sequence[offset:offset + max(1, line_width)] + "\n")


def _strip_nexus_comments(content: str) -> str:
    """Remove nested ``[comments]`` while preserving quoted taxon labels."""
    result: List[str] = []
    depth = 0
    quote: Optional[str] = None
    index = 0
    while index < len(content):
        char = content[index]
        if depth:
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
            elif char == "\n":
                result.append("\n")
            index += 1
            continue
        if quote:
            result.append(char)
            if char == quote:
                # NEXUS escapes a quote inside a quoted label by doubling it.
                if index + 1 < len(content) and content[index + 1] == quote:
                    result.append(content[index + 1])
                    index += 1
                else:
                    quote = None
            index += 1
            continue
        if char in ("'", '"'):
            quote = char
            result.append(char)
        elif char == "[":
            depth = 1
        else:
            result.append(char)
        index += 1
    if depth:
        raise FormatConversionError("NEXUS contains an unterminated comment")
    if quote:
        raise FormatConversionError("NEXUS contains an unterminated quoted label")
    return "".join(result)


def _nexus_tokens(line: str, line_number: int) -> List[str]:
    # shlex treats two adjacent single-quoted strings as concatenation, while
    # NEXUS uses doubled single quotes to represent one literal quote inside a
    # taxon label. Protect that escape during tokenization for lossless
    # read/write round trips.
    quote_sentinel = "\ue000"
    lexer = shlex.shlex(line.replace("''", quote_sentinel), posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return [token.replace(quote_sentinel, "'") for token in lexer]
    except ValueError as exc:
        raise FormatConversionError(
            f"Invalid NEXUS matrix row at line {line_number}: {exc}"
        ) from exc


def read_nexus(path: str) -> List[SequenceRecord]:
    """Read a DNA/RNA NEXUS DATA or CHARACTERS matrix.

    Sequential matrices, named interleaved blocks, and unnamed continuation
    blocks are supported. Tree-only NEXUS files are rejected explicitly.
    """
    with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
        content = _strip_nexus_comments(handle.read())
    if not re.search(r"(?im)^\s*#nexus\b", content):
        raise FormatConversionError("File does not start with a #NEXUS declaration")
    block_match = re.search(
        r"(?is)\bbegin\s+(?:data|characters)\s*;(.*?)\b(?:end|endblock)\s*;",
        content,
    )
    if block_match is None:
        raise FormatConversionError("NEXUS has no DATA or CHARACTERS block")
    block = block_match.group(1)
    matrix_match = re.search(r"(?is)\bmatrix\b(.*?);", block)
    if matrix_match is None:
        raise FormatConversionError("NEXUS DATA block has no MATRIX")

    ntax_match = re.search(r"(?i)\bntax\s*=\s*(\d+)", block)
    nchar_match = re.search(r"(?i)\bnchar\s*=\s*(\d+)", block)
    expected_count = int(ntax_match.group(1)) if ntax_match else None
    expected_length = int(nchar_match.group(1)) if nchar_match else None
    matchchar_match = re.search(r"(?i)\bmatchchar\s*=\s*([^\s;]+)", block)
    matchchar = (
        matchchar_match.group(1).strip("'\"").upper()
        if matchchar_match else "."
    )

    order: List[str] = []
    fragments: Dict[str, List[str]] = {}
    continuation_index = 0
    matrix_start_line = content[:block_match.start(1) + matrix_match.start(1)].count("\n") + 1
    for offset, raw_line in enumerate(matrix_match.group(1).splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continuation_index = 0
            continue
        tokens = _nexus_tokens(line, matrix_start_line + offset)
        if not tokens:
            continue
        is_named_row = (
            len(tokens) >= 2
            and (
                tokens[0] in fragments
                or expected_count is None
                or len(order) < expected_count
            )
        )
        if is_named_row:
            name = tokens[0]
            fragment = "".join(tokens[1:])
            if name not in fragments:
                order.append(name)
                fragments[name] = []
            fragments[name].append(fragment)
        else:
            if not order:
                raise FormatConversionError(
                    "NEXUS MATRIX continuation appears before any taxon label"
                )
            name = order[continuation_index % len(order)]
            fragments[name].append("".join(tokens))
            continuation_index += 1

    records = [
        SequenceRecord(name, re.sub(r"\s+", "", "".join(fragments[name])).upper())
        for name in order
    ]
    if expected_count is not None and len(records) != expected_count:
        raise FormatConversionError(
            f"NEXUS declares {expected_count} taxa but contains {len(records)}"
        )
    if expected_length is not None and any(
        len(record.sequence) != expected_length for record in records
    ):
        raise FormatConversionError(
            f"One or more NEXUS sequences do not match declared length {expected_length}"
        )
    if records and any(
        len(record.sequence) != len(records[0].sequence) for record in records
    ):
        raise FormatConversionError("NEXUS MATRIX sequences have unequal lengths")
    if matchchar:
        reference = records[0].sequence if records else ""
        if matchchar in reference:
            raise FormatConversionError("The first NEXUS sequence cannot contain MATCHCHAR")
        records = [records[0]] + [
            SequenceRecord(
                record.name,
                "".join(
                    reference[index] if base == matchchar else base
                    for index, base in enumerate(record.sequence)
                ),
            )
            for record in records[1:]
        ] if records else []
    _validate_sequence_records(records)
    return records


def read_phylip(path: str) -> List[SequenceRecord]:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
        lines = [line.rstrip("\r\n") for line in handle]
    nonempty = [line for line in lines if line.strip()]
    if not nonempty:
        raise FormatConversionError("PHYLIP file is empty")
    header = nonempty[0].split()
    if len(header) < 2:
        raise FormatConversionError("PHYLIP header must contain sequence count and length")
    try:
        expected_count, expected_length = int(header[0]), int(header[1])
    except ValueError as exc:
        raise FormatConversionError("Invalid PHYLIP sequence count or length") from exc

    if expected_count < 1 or expected_length < 1:
        raise FormatConversionError("PHYLIP sequence count and length must be positive")

    header_index = next(index for index, line in enumerate(lines) if line.strip())
    body = lines[header_index + 1:]

    def named_row(line: str, line_number: int) -> Tuple[str, str]:
        fields = line.split()
        if len(fields) >= 2:
            return fields[0], "".join(fields[1:]).upper()
        # Strict PHYLIP reserves the first ten columns for the taxon label and
        # does not require whitespace before the sequence.
        if len(line) > 10 and line[:10].strip() and line[10:].strip():
            return line[:10].strip(), re.sub(r"\s+", "", line[10:]).upper()
        raise FormatConversionError(
            f"PHYLIP record is incomplete at line {line_number}"
        )

    indexed_body = [
        (header_index + offset + 2, line)
        for offset, line in enumerate(body) if line.strip()
    ]

    def parse_interleaved() -> List[SequenceRecord]:
        if len(indexed_body) < expected_count:
            raise FormatConversionError("PHYLIP contains fewer records than declared")
        order: List[str] = []
        fragments: Dict[str, List[str]] = {}
        for line_number, line in indexed_body[:expected_count]:
            name, fragment = named_row(line, line_number)
            if name in fragments:
                raise FormatConversionError(f"Duplicate PHYLIP taxon name: {name}")
            order.append(name)
            fragments[name] = [fragment]
        continuation_index = 0
        for line_number, line in indexed_body[expected_count:]:
            fields = line.split()
            if len(fields) >= 2 and fields[0] in fragments:
                fragments[fields[0]].append("".join(fields[1:]).upper())
            else:
                if not fields:
                    continue
                name = order[continuation_index % expected_count]
                fragments[name].append("".join(fields).upper())
                continuation_index += 1
        return [SequenceRecord(name, "".join(fragments[name])) for name in order]

    def parse_wrapped_sequential() -> List[SequenceRecord]:
        records: List[SequenceRecord] = []
        cursor = 0
        for _ in range(expected_count):
            if cursor >= len(indexed_body):
                raise FormatConversionError("PHYLIP contains fewer records than declared")
            line_number, line = indexed_body[cursor]
            cursor += 1
            name, sequence = named_row(line, line_number)
            while len(sequence) < expected_length and cursor < len(indexed_body):
                _, continuation = indexed_body[cursor]
                cursor += 1
                sequence += "".join(continuation.split()).upper()
            records.append(SequenceRecord(name, sequence))
        if cursor != len(indexed_body):
            raise FormatConversionError("PHYLIP contains extra sequence rows")
        return records

    try:
        records = parse_interleaved()
        if any(len(record.sequence) != expected_length for record in records):
            raise FormatConversionError("Interleaved PHYLIP lengths do not match")
    except FormatConversionError:
        records = parse_wrapped_sequential()

    if len({record.name for record in records}) != len(records):
        raise FormatConversionError("PHYLIP contains duplicate taxon names")
    if any(len(record.sequence) != expected_length for record in records):
        raise FormatConversionError(
            f"One or more PHYLIP sequences do not match declared length {expected_length}"
        )
    _validate_sequence_records(records)
    return records


def write_nexus(path: str, records: Sequence[SequenceRecord]) -> None:
    """Write an aligned DNA/RNA matrix as standards-compatible NEXUS."""
    _validate_aligned_records(records, "NEXUS")
    symbols = {
        base
        for record in records
        for base in record.sequence.upper()
    }
    supported = set("ACGTURYSWKMBDHVN?-")
    unsupported = sorted(symbols - supported)
    if unsupported:
        raise FormatConversionError(
            "NEXUS DNA/RNA output contains unsupported symbols: "
            + ", ".join(unsupported[:10])
        )
    if "T" in symbols and "U" in symbols:
        raise FormatConversionError(
            "NEXUS output cannot infer DNA or RNA from sequences containing both T and U"
        )
    datatype = "RNA" if "U" in symbols else "DNA"
    length = len(records[0].sequence)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("#NEXUS\n\n")
        handle.write("BEGIN DATA;\n")
        handle.write(f"    DIMENSIONS NTAX={len(records)} NCHAR={length};\n")
        handle.write(
            f"    FORMAT DATATYPE={datatype} MISSING=? GAP=-;\n"
        )
        handle.write("    MATRIX\n")
        for record in records:
            label = _single_line(record.name).replace("\t", " ").strip()
            escaped_label = label.replace("'", "''")
            handle.write(f"        '{escaped_label}' {record.sequence.upper()}\n")
        handle.write("    ;\n")
        handle.write("END;\n")


def write_phylip(path: str, records: Sequence[SequenceRecord]) -> None:
    _validate_aligned_records(records, "PHYLIP")
    length = len(records[0].sequence)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(f" {len(records)} {length}\n")
        for record in records:
            name = re.sub(r"\s+", "_", _single_line(record.name))
            handle.write(f"{name} {record.sequence.upper()}\n")


def read_vcf(path: str) -> VcfData:
    opener = gzip.open if path.lower().endswith(".gz") else open
    headers: List[str] = []
    samples: Tuple[str, ...] = ()
    records: List[VcfRecord] = []
    with opener(path, "rt", encoding="utf-8-sig", errors="replace") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\r\n")
            if not line:
                continue
            if line.startswith("##"):
                headers.append(line)
                continue
            if line.startswith("#CHROM"):
                columns = line.split("\t")
                if len(columns) < 9:
                    raise FormatConversionError("VCF #CHROM header has fewer than 9 columns")
                samples = tuple(columns[9:])
                if len(set(samples)) != len(samples):
                    raise FormatConversionError("VCF contains duplicate sample names")
                continue
            if line.startswith("#"):
                headers.append(line)
                continue
            if not samples:
                raise FormatConversionError(
                    f"VCF data appears before a sample #CHROM header at line {line_number}"
                )
            columns = line.split("\t")
            if len(columns) < 9 + len(samples):
                raise FormatConversionError(f"Incomplete VCF record at line {line_number}")
            try:
                position = int(columns[1])
            except ValueError as exc:
                raise FormatConversionError(f"Invalid VCF position at line {line_number}") from exc
            if position < 1:
                raise FormatConversionError(
                    f"VCF position must be positive at line {line_number}"
                )
            reference = columns[3].upper()
            alternates = tuple(value.upper() for value in columns[4].split(","))
            if not reference or reference == "." or any(not alt or alt == "." for alt in alternates):
                raise FormatConversionError(
                    f"VCF record at line {line_number} has an empty REF/ALT allele"
                )
            if any(alt == "*" or alt.startswith("<") or "[" in alt or "]" in alt
                   for alt in alternates):
                raise FormatConversionError(
                    f"Symbolic or breakend ALT alleles are not supported (line {line_number})"
                )
            records.append(VcfRecord(
                columns[0], position, columns[2], reference, alternates,
                columns[5], columns[6], columns[7], tuple(columns[8].split(":")),
                tuple(columns[9:9 + len(samples)]),
            ))
    if not samples:
        raise FormatConversionError("VCF has no sample columns")
    if not records:
        raise FormatConversionError("VCF has no variant records")
    contigs = {record.chrom for record in records}
    if len(contigs) != 1:
        raise FormatConversionError(
            "NetST sequence conversion currently requires a single-contig VCF"
        )
    ordered = sorted(records, key=lambda record: record.position)
    return VcfData(samples, tuple(ordered), tuple(headers))


def vcf_to_sequences(vcf: VcfData, reference_fasta: str = "") -> Tuple[List[SequenceRecord], bool]:
    reference_sequence = ""
    if reference_fasta:
        references = read_fasta(reference_fasta)
        chrom = vcf.records[0].chrom
        matches = [record for record in references if record.name.split()[0] == chrom]
        if len(references) == 1:
            reference_sequence = references[0].sequence.replace("-", "")
        elif len(matches) == 1:
            reference_sequence = matches[0].sequence.replace("-", "")
        else:
            raise FormatConversionError(
                f"Reference FASTA must contain exactly one record matching VCF contig {chrom}"
            )

    previous_end = 0
    for record in vcf.records:
        zero_based = record.position - 1
        if zero_based < previous_end:
            raise FormatConversionError(
                f"Overlapping VCF records near position {record.position} are not supported"
            )
        previous_end = zero_based + len(record.reference)

    parts: Dict[str, List[str]] = {sample: [] for sample in vcf.samples}
    cursor = 0
    for record in vcf.records:
        zero_based = record.position - 1
        if reference_sequence:
            if zero_based < cursor:
                raise FormatConversionError(
                    f"Overlapping VCF records near position {record.position} are not supported"
                )
            end = zero_based + len(record.reference)
            if end > len(reference_sequence):
                raise FormatConversionError(
                    f"VCF record at {record.position} extends beyond the reference FASTA"
                )
            observed = reference_sequence[zero_based:end].upper()
            if observed != record.reference:
                raise FormatConversionError(
                    f"VCF REF mismatch at {record.chrom}:{record.position}: "
                    f"VCF={record.reference}, FASTA={observed}"
                )
            invariant = reference_sequence[cursor:zero_based]
            for sample in vcf.samples:
                parts[sample].append(invariant)

        alleles = (record.reference,) + record.alternates
        width = max(len(allele) for allele in alleles)
        for sample, field in zip(vcf.samples, record.sample_fields):
            allele = _sample_allele(record, field)
            parts[sample].append(allele.ljust(width, "-"))
        if reference_sequence:
            cursor = zero_based + len(record.reference)

    if reference_sequence:
        suffix = reference_sequence[cursor:]
        for sample in vcf.samples:
            parts[sample].append(suffix)

    records = [
        SequenceRecord(sample, "".join(parts[sample]))
        for sample in vcf.samples
    ]
    _validate_aligned_records(records, "VCF-derived alignment")
    return records, bool(reference_sequence)


def import_vcf(
    vcf_path: str,
    metadata_path: str = "",
    reference_fasta: str = "",
) -> VcfImportResult:
    vcf = read_vcf(vcf_path)
    records, full_length = vcf_to_sequences(vcf, reference_fasta)
    metadata = read_metadata(metadata_path) if metadata_path else {}
    warnings: List[str] = []
    if metadata:
        missing = [sample for sample in vcf.samples if sample not in metadata]
        if missing:
            warnings.append(
                f"Metadata did not match {len(missing)} VCF sample(s): "
                + ", ".join(missing[:5])
            )

    taxons: List[TaxonData] = []
    for index, record in enumerate(records, start=1):
        entry = metadata.get(record.name, MetadataEntry(record.name))
        taxons.append(TaxonData(
            id=index,
            name=record.name,
            sequence=record.sequence,
            discrete_traits=entry.discrete_trait,
            continuous_traits=entry.continuous_trait,
        ))
    return VcfImportResult(
        tuple(taxons), vcf.samples, len(vcf.records), len(records[0].sequence),
        full_length, tuple(warnings),
    )


def read_metadata(path: str) -> Dict[str, MetadataEntry]:
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        raw_lines = [line for line in handle if line.strip() and not line.startswith("#")]
    if not raw_lines:
        raise FormatConversionError("Metadata file is empty")
    delimiter = "\t" if raw_lines[0].count("\t") >= raw_lines[0].count(",") else ","
    rows = list(csv.reader(raw_lines, delimiter=delimiter))
    first = [_normal_header(value) for value in rows[0]]
    name_header_count = sum(value in _NAME_HEADERS for value in first)
    trait_header_count = sum(
        value in (_DISCRETE_HEADERS | _CONTINUOUS_HEADERS) for value in first
    )
    # One value such as "sample" or "name" is not enough to prove that the
    # first row is a header: those are also valid sample names in headerless
    # McAN metadata.  A supported header has either two identifier columns
    # (SampleName + AccessionID) or an identifier plus a recognised trait.
    has_header = (
        name_header_count >= 2
        or (name_header_count >= 1 and trait_header_count >= 1)
    )

    result: Dict[str, MetadataEntry] = {}
    if has_header:
        name_indexes = [
            index for index, value in enumerate(first) if value in _NAME_HEADERS
        ]
        if not name_indexes:
            raise FormatConversionError("Metadata header has no sample/accession column")
        discrete_indexes = [
            index for index, value in enumerate(first) if value in _DISCRETE_HEADERS
        ]
        continuous_index = _first_header_index(first, _CONTINUOUS_HEADERS)
        data_rows = rows[1:]
        for row in data_rows:
            names = [row[index].strip() for index in name_indexes
                     if index < len(row) and row[index].strip() and row[index].strip() != "*"]
            if not names:
                continue
            discrete_values = [_cell(row, index, "") for index in discrete_indexes]
            discrete = " / ".join(value for value in discrete_values if value)
            continuous = _finite_number_or_default(_cell(row, continuous_index, "0"))
            entry = MetadataEntry(names[0], discrete, continuous)
            for name in names:
                if name in result:
                    raise FormatConversionError(f"Duplicate metadata sample/accession: {name}")
                result[name] = entry
    else:
        # McAN metadata: SampleName, AccessionID, Date, Country, State, City.
        for row in rows:
            if len(row) < 2:
                raise FormatConversionError(
                    "Headerless metadata must contain at least sample name and accession"
                )
            sample_name = row[0].strip()
            accession = row[1].strip()
            country = _cell(row, 3, "")
            state = _cell(row, 4, "")
            city = _cell(row, 5, "")
            discrete = " / ".join(value for value in (country, state, city)
                                  if value and value != "*")
            keys = [value for value in (accession, sample_name) if value and value != "*"]
            if not keys:
                continue
            entry = MetadataEntry(keys[0], discrete, "0")
            for key in keys:
                if key in result:
                    raise FormatConversionError(f"Duplicate metadata sample/accession: {key}")
                result[key] = entry
    return result


def records_to_vcf(
    records: Sequence[SequenceRecord],
    reference_name: str = "",
    chrom: str = "alignment",
) -> str:
    _validate_aligned_records(records, "VCF export")
    names = [record.name for record in records]
    vcf_names = [_vcf_sample_name(name) for name in names]
    if len(set(vcf_names)) != len(vcf_names):
        raise FormatConversionError(
            "Sequence names become duplicated after VCF sample-name normalization"
        )
    reference_name = reference_name or names[0]
    if reference_name not in names:
        raise FormatConversionError(f"Reference sequence not found: {reference_name}")
    reference = next(record.sequence.upper() for record in records
                     if record.name == reference_name)
    sequences = [record.sequence.upper() for record in records]
    variable = [len({sequence[index] for sequence in sequences}) > 1
                for index in range(len(reference))]

    blocks: List[Tuple[int, int]] = []
    index = 0
    while index < len(variable):
        if not variable[index]:
            index += 1
            continue
        end = index + 1
        while end < len(variable) and variable[end]:
            end += 1
        blocks.append((index, end))
        index = end

    # VCF alleles may not be empty, so an insertion/deletion-only alignment
    # block needs a neighbouring reference base as an anchor.  Expanding a
    # block can make it overlap a later SNP block (notably for leading
    # insertions).  Normalize and merge the intervals before emitting records;
    # otherwise NetST could create an invalid VCF containing overlapping rows.
    anchored_blocks: List[Tuple[int, int]] = []
    for start, end in blocks:
        raw_alleles = [sequence[start:end].replace("-", "")
                       for sequence in sequences]
        if any(not allele for allele in raw_alleles):
            anchor = _previous_reference_anchor(reference, start)
            if anchor is not None:
                start = anchor
            else:
                anchor = _next_reference_anchor(reference, end)
                if anchor is None:
                    raise FormatConversionError(
                        "Cannot anchor an all-gap terminal variant block in VCF"
                    )
                end = anchor + 1
        if anchored_blocks and start < anchored_blocks[-1][1]:
            previous_start, previous_end = anchored_blocks[-1]
            anchored_blocks[-1] = (previous_start, max(previous_end, end))
        else:
            anchored_blocks.append((start, end))

    lines = [
        "##fileformat=VCFv4.2",
        "##source=NetST",
        f"##contig=<ID={chrom},length={len(reference.replace('-', ''))}>",
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Haploid genotype">',
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t"
        + "\t".join(vcf_names),
    ]

    for start, end in anchored_blocks:
        raw_alleles = [sequence[start:end].replace("-", "").replace("U", "T")
                       for sequence in sequences]
        ref_allele = raw_alleles[names.index(reference_name)]
        if not ref_allele or any(not allele for allele in raw_alleles):
            raise FormatConversionError("Unable to construct non-empty VCF alleles")
        alternates: List[str] = []
        for allele in raw_alleles:
            if allele != ref_allele and allele not in alternates:
                alternates.append(allele)
        if not alternates:
            continue
        allele_indexes = {ref_allele: 0, **{
            allele: alt_index for alt_index, allele in enumerate(alternates, start=1)
        }}
        position = sum(base != "-" for base in reference[:start]) + 1
        genotype_fields = [str(allele_indexes[allele]) for allele in raw_alleles]
        info = f"NS={len(records)};TYPE={'SNP' if len(ref_allele) == 1 and all(len(a) == 1 for a in alternates) else 'COMPLEX'}"
        lines.append(
            f"{chrom}\t{position}\t.\t{ref_allele}\t{','.join(alternates)}"
            f"\t.\tPASS\t{info}\tGT\t" + "\t".join(genotype_fields)
        )
    if len(lines) == 5:
        raise FormatConversionError("The alignment contains no variable sites to export")
    return "\n".join(lines) + "\n"


def write_vcf(
    path: str,
    records: Sequence[SequenceRecord],
    reference_name: str = "",
    chrom: str = "alignment",
) -> None:
    content = records_to_vcf(records, reference_name, chrom)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def convert_file(
    input_path: str,
    output_path: str,
    input_format: str = "auto",
    output_format: str = "fasta",
    reference_fasta: str = "",
    reference_name: str = "",
) -> None:
    if os.path.normcase(os.path.abspath(input_path)) == os.path.normcase(
        os.path.abspath(output_path)
    ):
        raise FormatConversionError("Input and output paths must be different")
    source_format = detect_format(input_path) if input_format == "auto" else input_format.lower()
    target_format = output_format.lower()
    if source_format == target_format:
        raise FormatConversionError("Input and output formats must be different")

    if source_format == "fasta":
        records = read_fasta(input_path)
    elif source_format == "nexus":
        records = read_nexus(input_path)
    elif source_format == "phylip":
        records = read_phylip(input_path)
    elif source_format == "vcf":
        records, _ = vcf_to_sequences(read_vcf(input_path), reference_fasta)
    else:
        raise FormatConversionError(f"Unsupported input format: {source_format}")

    if target_format == "fasta":
        write_fasta(output_path, records)
    elif target_format == "nexus":
        write_nexus(output_path, records)
    elif target_format == "phylip":
        write_phylip(output_path, records)
    elif target_format == "vcf":
        write_vcf(output_path, records, reference_name=reference_name)
    else:
        raise FormatConversionError(f"Unsupported output format: {target_format}")


def subset_vcf(
    vcf_path: str,
    output_path: str,
    sample_names: Sequence[str],
    sample_aliases: Optional[Dict[str, str]] = None,
) -> None:
    """Write a VCF containing only selected sample columns, preserving records."""
    selected = set(sample_names)
    if not selected:
        raise FormatConversionError("At least one VCF sample must be selected")
    if len(selected) != len(sample_names):
        raise FormatConversionError("Selected VCF sample names contain duplicates")
    opener = gzip.open if vcf_path.lower().endswith(".gz") else open
    found: List[str] = []
    indexes: Optional[List[int]] = None
    source_column_count: Optional[int] = None

    # Validate the complete source before creating/replacing the destination.
    # This prevents a missing sample or malformed late row from leaving a
    # plausible-looking partial VCF behind.
    with opener(vcf_path, "rt", encoding="utf-8-sig", errors="replace") as source:
        for raw_line in source:
            line = raw_line.rstrip("\r\n")
            if line.startswith("#CHROM"):
                columns = line.split("\t")
                if len(columns) < 10:
                    raise FormatConversionError("VCF has no sample columns")
                source_samples = columns[9:]
                indexes = [index for index, name in enumerate(source_samples) if name in selected]
                found = [source_samples[index] for index in indexes]
                source_column_count = len(columns)
            elif line and not line.startswith("#"):
                if indexes is None:
                    raise FormatConversionError("VCF is missing its #CHROM header")
                columns = line.split("\t")
                if len(columns) != source_column_count:
                    raise FormatConversionError(
                        "VCF data row does not match the #CHROM column count"
                    )
    missing = selected - set(found)
    if missing:
        raise FormatConversionError(
            "Selected samples were not found in VCF: " + ", ".join(sorted(missing)[:10])
        )
    output_names = [(sample_aliases or {}).get(name, name) for name in found]
    if len(set(output_names)) != len(output_names):
        raise FormatConversionError("VCF sample aliases contain duplicates")

    output_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(output_dir, exist_ok=True)
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=output_dir,
            prefix=".netst-vcf-", suffix=".tmp", delete=False,
        ) as destination:
            temp_path = destination.name
            with opener(vcf_path, "rt", encoding="utf-8-sig", errors="replace") as source:
                for raw_line in source:
                    line = raw_line.rstrip("\r\n")
                    if line.startswith("#CHROM"):
                        columns = line.split("\t")
                        destination.write("\t".join(columns[:9] + output_names) + "\n")
                    elif line.startswith("#"):
                        destination.write(line + "\n")
                    elif line:
                        columns = line.split("\t")
                        destination.write("\t".join(
                            columns[:9] + [columns[9 + index] for index in indexes]
                        ) + "\n")
        os.replace(temp_path, output_path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def subset_metadata(
    metadata_path: str,
    output_path: str,
    sample_names: Sequence[str],
    sample_aliases: Optional[Dict[str, str]] = None,
) -> None:
    """Write McAN-compatible six-column metadata ordered like selected samples."""
    entries = read_metadata_rows(metadata_path)
    lookup: Dict[str, Tuple[str, ...]] = {}
    for row in entries:
        for key in (row[0], row[1]):
            if key and key != "*":
                if key in lookup:
                    raise FormatConversionError(
                        f"Duplicate metadata sample/accession: {key}"
                    )
                lookup[key] = row
    missing = [name for name in sample_names if name not in lookup]
    if missing:
        raise FormatConversionError(
            "Metadata is missing selected VCF samples: " + ", ".join(missing[:10])
        )
    aliases = [(sample_aliases or {}).get(name, name) for name in sample_names]
    if len(set(aliases)) != len(aliases):
        raise FormatConversionError("Metadata sample aliases contain duplicates")
    with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
        for name in sample_names:
            row = list(lookup[name])
            alias = (sample_aliases or {}).get(name, name)
            row[0] = alias
            row[1] = alias
            handle.write("\t".join(row) + "\n")


def read_metadata_rows(path: str) -> List[Tuple[str, ...]]:
    """Read McAN six-column metadata, accepting an optional standard header."""
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        rows = [line.rstrip("\r\n").split("\t") for line in handle
                if line.strip() and not line.startswith("#")]
    if not rows:
        raise FormatConversionError("Metadata file is empty")
    first = [_normal_header(value) for value in rows[0]]
    if first and first[0] in _NAME_HEADERS and len(first) > 1 and first[1] in _NAME_HEADERS:
        rows = rows[1:]
    if not rows:
        raise FormatConversionError("Metadata file contains a header but no data rows")
    normalized = []
    for index, row in enumerate(rows, start=1):
        if len(row) < 6:
            raise FormatConversionError(
                f"McAN metadata row {index} has fewer than six tab-delimited columns"
            )
        values = [(value.strip() or "*") for value in row[:6]]
        normalized.append(tuple(values))
    return normalized


def _sample_allele(record: VcfRecord, sample_field: str) -> str:
    values = sample_field.split(":")
    try:
        gt_index = record.format_keys.index("GT")
    except ValueError as exc:
        raise FormatConversionError(
            f"VCF record {record.chrom}:{record.position} has no GT field"
        ) from exc
    genotype = values[gt_index] if gt_index < len(values) else "."
    indexes = re.split(r"[/|]", genotype)
    if not indexes or any(value in ("", ".") for value in indexes):
        width = max(len(record.reference), *(len(alt) for alt in record.alternates))
        return "N" * width
    alleles = (record.reference,) + record.alternates
    try:
        selected = [alleles[int(value)] for value in indexes]
    except (ValueError, IndexError) as exc:
        raise FormatConversionError(
            f"Invalid genotype {genotype} at {record.chrom}:{record.position}"
        ) from exc
    if len(set(selected)) == 1:
        return selected[0]
    if all(len(allele) == 1 and allele in "ACGT" for allele in selected):
        return _IUPAC.get(frozenset(selected), "N")
    return "N" * max(len(allele) for allele in selected)


def _validate_sequence_records(records: Sequence[SequenceRecord]) -> None:
    if not records:
        raise FormatConversionError("No sequences were found")
    if any(not record.name.strip() for record in records):
        raise FormatConversionError("A sequence has an empty name")
    if len({record.name for record in records}) != len(records):
        raise FormatConversionError("Sequence names must be unique")
    if any(not record.sequence for record in records):
        raise FormatConversionError("A sequence is empty")


def _validate_aligned_records(records: Sequence[SequenceRecord], target: str) -> None:
    _validate_sequence_records(records)
    lengths = {len(record.sequence) for record in records}
    if len(lengths) != 1:
        raise FormatConversionError(f"{target} requires equal-length aligned sequences")


def _previous_reference_anchor(reference: str, start: int) -> Optional[int]:
    for index in range(start - 1, -1, -1):
        if reference[index] != "-":
            return index
    return None


def _next_reference_anchor(reference: str, end: int) -> Optional[int]:
    for index in range(end, len(reference)):
        if reference[index] != "-":
            return index
    return None


def _single_line(value: str) -> str:
    return str(value).replace("\r", "_").replace("\n", "_")


def _vcf_sample_name(value: str) -> str:
    name = re.sub(r"\s+", "_", _single_line(value).strip())
    if not name or "\t" in name:
        raise FormatConversionError("VCF sample names cannot be empty or contain tabs")
    return name


def _normal_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _first_header_index(headers: Sequence[str], candidates: Iterable[str]) -> Optional[int]:
    candidate_set = set(candidates)
    return next((index for index, value in enumerate(headers) if value in candidate_set), None)


def _cell(row: Sequence[str], index: Optional[int], default: str) -> str:
    if index is None or index >= len(row):
        return default
    value = row[index].strip()
    return value if value and value != "*" else default


def _finite_number_or_default(value: str) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0"
    return value if math.isfinite(number) else "0"
