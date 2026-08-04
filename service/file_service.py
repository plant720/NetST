"""
Service for handling file operations (FASTA, CSV, etc.)
"""
import csv
import json
import re
import shutil
from pathlib import Path
from typing import List

import chardet

from model.taxon_data import TaxonData
from service.format_conversion_service import (
    SequenceRecord,
    read_nexus,
    read_phylip,
    records_to_vcf,
    write_nexus,
    write_phylip,
)


class FileService:
    """Service for handling file I/O operations."""

    @staticmethod
    def clean_fasta_header(header: str) -> str:
        """Normalize a FASTA title into a safe single-token sample name."""
        cleaned = header.replace(',', '_').replace('"', '').replace("'", '').replace('=', '_')
        return re.sub(r'\s+', '_', cleaned.strip())

    @staticmethod
    def detect_encoding(file_path: str) -> str:
        """Detect file encoding. Always returns a valid codec name."""
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Read first 10KB
        if not raw_data:
            return 'utf-8'
        result = chardet.detect(raw_data) or {}
        encoding = result.get('encoding')
        if not encoding:
            return 'utf-8'
        # Validate codec; fall back to utf-8 on unknown encoding names.
        try:
            import codecs
            codecs.lookup(encoding)
        except LookupError:
            return 'utf-8'
        return encoding

    @staticmethod
    def ensure_utf8(file_path: str) -> None:
        """Convert file to UTF-8 if needed."""
        encoding = FileService.detect_encoding(file_path)
        if encoding.lower() not in ('utf-8', 'ascii'):
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

    def load_fasta_file(self, file_path: str) -> List[TaxonData]:
        """
        Load sequences from a FASTA file.
        
        Args:
            file_path: Path to FASTA file
        Returns:
            List of TaxonData objects
        """
        taxons = []
        encoding = self.detect_encoding(file_path)

        with open(file_path, 'r', encoding=encoding) as f:
            current_header = None
            sequence_lines = []
            taxon_id = 0

            for line in f:
                line = line.strip()
                if line.startswith('>'):
                    if current_header is not None:
                        if not sequence_lines:
                            raise ValueError(
                                f"FASTA record '{current_header}' has no sequence")
                        taxon_id += 1
                        sequence = ''.join(sequence_lines)
                        taxon = self._parse_fasta_header(taxon_id, current_header, sequence)
                        taxons.append(taxon)
                    current_header = line[1:]  # Remove '>'
                    if not current_header.strip():
                        raise ValueError("FASTA contains an empty header")
                    sequence_lines = []
                elif line:
                    if current_header is None:
                        raise ValueError("FASTA sequence data appears before the first header")
                    sequence_lines.append(line)

            if current_header is not None:
                if not sequence_lines:
                    raise ValueError(f"FASTA record '{current_header}' has no sequence")
                taxon_id += 1
                sequence = ''.join(sequence_lines)
                taxon = self._parse_fasta_header(taxon_id, current_header, sequence)
                taxons.append(taxon)

        return taxons

    def load_nexus_file(self, file_path: str) -> List[TaxonData]:
        """Load a NEXUS sequence matrix as editable NetST records."""
        return self._sequence_records_to_taxons(read_nexus(file_path))

    def load_phylip_file(self, file_path: str) -> List[TaxonData]:
        """Load a sequential PHYLIP alignment as editable NetST records."""
        return self._sequence_records_to_taxons(read_phylip(file_path))

    def get_sequence_headers(self, file_path: str, file_format: str,
                             limit: int = 100) -> List[str]:
        """Return normalized labels for a supported structured sequence file."""
        loaders = {
            "nexus": read_nexus,
            "phylip": read_phylip,
        }
        try:
            loader = loaders[file_format.lower()]
        except KeyError as exc:
            raise ValueError(f"Unsupported sequence format: {file_format}") from exc
        return [
            self.clean_fasta_header(record.name)
            for record in loader(file_path)[:max(0, limit)]
        ]

    def _sequence_records_to_taxons(self, records) -> List[TaxonData]:
        return [
            TaxonData(
                id=index,
                name=self.clean_fasta_header(record.name),
                sequence=record.sequence,
            )
            for index, record in enumerate(records, start=1)
        ]

    def _parse_fasta_header(self, taxon_id: int, header: str,
                            sequence: str) -> TaxonData:
        """Parse FASTA header and create TaxonData."""
        # Clean header: replace problematic characters
        clean_header = self.clean_fasta_header(header)

        taxon = TaxonData(id=taxon_id, name=clean_header, sequence=sequence)
        return taxon

    def export_to_fasta(self, file_path: str, taxons: List[TaxonData], delimiter: str = "|") -> None:
        """
        Export sequences to FASTA file.
        
        Args:
            file_path: Output file path
            taxons: List of TaxonData to export
            delimiter: Delimiter for header fields
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            for taxon in taxons:
                f.write(taxon.to_fasta_header(delimiter) + '\n')
                f.write(taxon.sequence + '\n')

    def export_sequences(self, file_path: str, taxons: List[TaxonData],
                         file_format: str) -> List[str]:
        """Export sequence data and return every generated output path.

        FASTA headers intentionally contain the editable traits. NEXUS,
        PHYLIP, and VCF contain sample names plus sequences only. A VCF export
        additionally embeds NetST metadata headers and writes a paired CSV so
        the traits can be imported again without parsing custom VCF headers.
        """
        if not taxons:
            raise ValueError("No sequence data to export")
        file_format = file_format.lower()
        if file_format == "fasta":
            self.export_to_fasta(file_path, taxons, "|")
            return [file_path]

        records = [
            SequenceRecord(taxon.name, taxon.sequence)
            for taxon in taxons
        ]
        if file_format == "nexus":
            write_nexus(file_path, records)
            return [file_path]
        if file_format == "phylip":
            write_phylip(file_path, records)
            return [file_path]
        if file_format != "vcf":
            raise ValueError(f"Unsupported export format: {file_format}")

        content = records_to_vcf(records)
        lines = content.rstrip("\n").split("\n")
        header_index = next(
            index for index, line in enumerate(lines)
            if line.startswith("#CHROM")
        )
        vcf_sample_names = lines[header_index].split("\t")[9:]
        trait_rows = []
        for taxon, sample_name in zip(taxons, vcf_sample_names):
            row = self._trait_row(taxon)
            row["sample"] = sample_name
            trait_rows.append(row)
        metadata_lines = [
            "##NetSTSampleMetadata=" + json.dumps(
                row, ensure_ascii=False, separators=(",", ":"),
            )
            for row in trait_rows
        ]
        lines[header_index:header_index] = metadata_lines
        with open(file_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")

        stem = file_path[:-4] if file_path.lower().endswith(".vcf") else file_path
        metadata_path = stem + "_metadata.csv"
        self._write_trait_rows(metadata_path, trait_rows)
        return [file_path, metadata_path]

    def export_traits(self, file_path: str, taxons: List[TaxonData],
                      delimiter: str = ",", trait_names=None) -> None:
        """Export sample metadata as a UTF-8 CSV or TSV table.

        With ``trait_names`` the table has one column per named trait
        (``sample, <trait...>``); otherwise it falls back to the classic
        ``sample, discrete_trait, continuous_trait`` layout.
        """
        if not taxons:
            raise ValueError("No metadata to export")
        if trait_names:
            fieldnames = ["sample"] + list(trait_names)
            rows = []
            for taxon in taxons:
                row = {"sample": taxon.name}
                for name in trait_names:
                    row[name] = taxon.trait_value(name)
                rows.append(row)
            with open(file_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter)
                writer.writeheader()
                writer.writerows(rows)
            return
        self._write_trait_rows(
            file_path, [self._trait_row(taxon) for taxon in taxons],
            delimiter=delimiter)

    @staticmethod
    def _write_trait_rows(file_path: str, rows: List[dict],
                          delimiter: str = ",") -> None:
        with open(file_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "sample", "discrete_trait", "continuous_trait",
            ], delimiter=delimiter)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _trait_row(taxon: TaxonData) -> dict:
        return {
            "sample": taxon.name,
            "discrete_trait": taxon.discrete_traits,
            "continuous_trait": taxon.continuous_traits,
        }

    def write_analysis_fasta(self, file_path: str, taxons: List[TaxonData]) -> None:
        """
        Write selected sequences to FASTA for analysis.
        
        Args:
            file_path: Output file path
            taxons: List of selected TaxonData
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            for taxon in taxons:
                f.write(taxon.to_analysis_header() + '\n')
                f.write(taxon.sequence + '\n')

    @staticmethod
    def safe_copy(source: str, destination: str) -> None:
        """Safely copy a file."""
        shutil.copy2(source, destination)

    @staticmethod
    def ensure_directory(dir_path: str) -> None:
        """Ensure directory exists, create if not."""
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    def apply_standardization(self, taxons: List[TaxonData], config, start_id: int = 1) -> List[TaxonData]:
        """
        Apply standardization configuration to taxons.
        
        Args:
            taxons: List of TaxonData objects
            config: StandardizationConfig object
            start_id: Starting ID for taxons (default 1)
            
        Returns:
            List of processed TaxonData objects
        """
        result = []
        current_id = start_id

        ambiguous = frozenset('RYSWKMBDHVN')
        replace_enabled = config.replace_enabled and bool(config.replace_from)
        replace_from = config.replace_from
        replace_to = config.replace_to or ""

        split_name = (config.split_name_enabled and bool(config.split_name_delimiter),
                      config.split_name_delimiter, config.split_name_index)
        split_disc = (config.split_discrete_enabled and bool(config.split_discrete_delimiter),
                      config.split_discrete_delimiter, config.split_discrete_index)
        split_cont = (config.split_continuous_enabled and bool(config.split_continuous_delimiter),
                      config.split_continuous_delimiter, config.split_continuous_index)

        # When several splits share the same delimiter (common case) we can
        # split once and reuse the parts list instead of re-splitting.
        same_delim = (
            split_name[0] and split_disc[0] and split_cont[0]
            and split_name[1] == split_disc[1] == split_cont[1]
        )

        for taxon in taxons:
            if config.remove_ambiguous and any(b in ambiguous for b in taxon.sequence.upper()):
                continue

            taxon.id = current_id
            current_id += 1

            if replace_enabled:
                taxon.name = taxon.name.replace(replace_from, replace_to)

            original_name = taxon.name

            if same_delim:
                parts = original_name.split(split_name[1])
                if split_name[2] < len(parts):
                    taxon.name = parts[split_name[2]].strip()
                if split_disc[2] < len(parts):
                    taxon.discrete_traits = parts[split_disc[2]].strip()
                if split_cont[2] < len(parts):
                    taxon.continuous_traits = parts[split_cont[2]].strip()
            else:
                if split_name[0]:
                    parts = original_name.split(split_name[1])
                    if split_name[2] < len(parts):
                        taxon.name = parts[split_name[2]].strip()
                if split_disc[0]:
                    parts = original_name.split(split_disc[1])
                    if split_disc[2] < len(parts):
                        taxon.discrete_traits = parts[split_disc[2]].strip()
                if split_cont[0]:
                    parts = original_name.split(split_cont[1])
                    if split_cont[2] < len(parts):
                        taxon.continuous_traits = parts[split_cont[2]].strip()

            if config.use_numbering:
                taxon.name = str(taxon.id)

            result.append(taxon)

        return result
