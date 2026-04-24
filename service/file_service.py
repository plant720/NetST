"""
Service for handling file operations (FASTA, CSV, etc.)
"""
import csv
import os
import shutil
from pathlib import Path
from typing import List

import chardet

from model.taxon_data import TaxonData


class FileService:
    """Service for handling file I/O operations."""

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

    def load_fasta_file(self, file_path: str, delimiter: str = "|") -> List[TaxonData]:
        """
        Load sequences from a FASTA file.
        
        Args:
            file_path: Path to FASTA file
            delimiter: Delimiter used in headers
            
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
                    # Save previous sequence if exists
                    if current_header is not None and sequence_lines:
                        taxon_id += 1
                        sequence = ''.join(sequence_lines)
                        taxon = self._parse_fasta_header(taxon_id, current_header, sequence, delimiter)
                        taxons.append(taxon)
                        sequence_lines = []

                    current_header = line[1:]  # Remove '>'
                elif line:
                    sequence_lines.append(line)

            # Don't forget the last sequence
            if current_header is not None and sequence_lines:
                taxon_id += 1
                sequence = ''.join(sequence_lines)
                taxon = self._parse_fasta_header(taxon_id, current_header, sequence, delimiter)
                taxons.append(taxon)

        return taxons

    def _parse_fasta_header(self, taxon_id: int, header: str, sequence: str, delimiter: str) -> TaxonData:
        """Parse FASTA header and create TaxonData."""
        # Clean header: replace problematic characters
        clean_header = header.replace(',', '_').replace('"', '').replace("'", "").replace('=', '_')

        taxon = TaxonData(id=taxon_id, name=clean_header, sequence=sequence)
        return taxon

    def load_csv_file(self, file_path: str) -> List[TaxonData]:
        """
        Load data from CSV file.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of TaxonData objects
        """
        taxons = []
        encoding = self.detect_encoding(file_path)

        with open(file_path, 'r', encoding=encoding, newline='') as f:
            reader = csv.reader(f)

            # Skip header
            try:
                next(reader)
            except StopIteration:
                return taxons

            taxon_id = 0
            for row in reader:
                if not row or not any(row):  # Skip empty rows
                    continue

                taxon_id += 1
                taxon = TaxonData(id=taxon_id)

                if len(row) > 0:
                    taxon.name = row[0].strip()
                if len(row) > 1:
                    taxon.sequence = row[1].strip()
                if len(row) > 2:
                    taxon.discrete_traits = row[2].strip()
                if len(row) > 3:
                    taxon.continuous_traits = row[3].strip()

                taxons.append(taxon)

        return taxons

    def save_to_csv(self, file_path: str, taxons: List[TaxonData]) -> None:
        """
        Save data to CSV file.
        
        Args:
            file_path: Output file path
            taxons: List of TaxonData to save
        """
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(['ID', 'Name', 'Sequence', 'Discrete Traits', 'Continuous Traits'])

            # Write data
            for taxon in taxons:
                writer.writerow([
                    taxon.id,
                    taxon.name,
                    taxon.sequence,
                    taxon.discrete_traits,
                    taxon.continuous_traits,
                ])

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
    def file_exists(file_path: str) -> bool:
        """Check if file exists."""
        return os.path.isfile(file_path)

    @staticmethod
    def ensure_directory(dir_path: str) -> None:
        """Ensure directory exists, create if not."""
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    def get_fasta_headers(self, file_path: str, limit: int = 100) -> List[str]:
        """
        Extract sequence headers from FASTA file for preview.
        
        Args:
            file_path: Path to FASTA file
            limit: Maximum number of headers to extract
            
        Returns:
            List of header strings (without '>')
        """
        headers = []
        encoding = self.detect_encoding(file_path)

        with open(file_path, 'r', encoding=encoding) as f:
            count = 0
            for line in f:
                line = line.strip()
                if line.startswith('>'):
                    # Clean header like VB.NET does
                    header = line[1:].replace(',', '_').replace('"', '').replace("'", "").replace('=', '_')
                    headers.append(header)
                    count += 1
                    if count >= limit:
                        break

        return headers

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
