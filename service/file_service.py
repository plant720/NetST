"""
Service for handling file operations (FASTA, CSV, etc.)
"""
import csv
import shutil
from pathlib import Path
from typing import List

import chardet

from model.taxon_data import TaxonData


class FileService:
    """Service for handling file I/O operations."""

    @staticmethod
    def detect_encoding(file_path: str) -> str:
        """Detect file encoding."""
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Read first 10KB
            result = chardet.detect(raw_data)
            return result['encoding'] or 'utf-8'

    @staticmethod
    def ensure_utf8(file_path: str) -> None:
        """Convert file to UTF-8 if needed."""
        encoding = FileService.detect_encoding(file_path)
        if encoding.lower() not in ('utf-8', 'ascii'):
            with open(file_path, 'r', encoding=encoding) as f:
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
                    if current_header is not None and sequence_lines:
                        taxon_id += 1
                        sequence = ''.join(sequence_lines)
                        taxon = self._parse_fasta_header(taxon_id, current_header, sequence, delimiter)
                        taxons.append(taxon)
                        sequence_lines = []
                    current_header = line[1:]
                elif line:
                    sequence_lines.append(line)
            if current_header is not None and sequence_lines:
                taxon_id += 1
                sequence = ''.join(sequence_lines)
                taxon = self._parse_fasta_header(taxon_id, current_header, sequence, delimiter)
                taxons.append(taxon)

        return taxons

    @staticmethod
    def _clean_fasta_header(header: str) -> str:
        """Sanitize a raw FASTA header (strip characters that break downstream parsers)."""
        return header.replace(',', '_').replace('"', '').replace("'", "").replace('=', '_')

    def _parse_fasta_header(self, taxon_id: int, header: str, sequence: str, delimiter: str) -> TaxonData:
        """Parse FASTA header and create TaxonData."""
        return TaxonData(id=taxon_id, name=self._clean_fasta_header(header), sequence=sequence)

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
            try:
                next(reader)
            except StopIteration:
                return taxons
            taxon_id = 0
            for row in reader:
                if not row or not any(row):
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
            writer.writerow(['ID', 'Name', 'Sequence', 'Discrete Traits', 'Continuous Traits'])
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
                    header = self._clean_fasta_header(line[1:])
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

        for i, taxon in enumerate(taxons):
            # Skip sequences with ambiguous bases if requested
            if config.remove_ambiguous:
                ambiguous = set('RYSWKMBDHVN')
                if any(base.upper() in ambiguous for base in taxon.sequence):
                    continue

            # Update taxon ID
            taxon.id = current_id
            current_id += 1

            # Apply replace if enabled
            if config.replace_enabled and config.replace_from:
                taxon.name = taxon.name.replace(config.replace_from, config.replace_to)

            # Get original header for splitting
            original_name = taxon.name

            # Split and extract new name
            if config.split_name_enabled and config.split_name_delimiter:
                parts = original_name.split(config.split_name_delimiter)
                if config.split_name_index < len(parts):
                    taxon.name = parts[config.split_name_index].strip()

            # Split and extract discrete trait
            if config.split_discrete_enabled and config.split_discrete_delimiter:
                parts = original_name.split(config.split_discrete_delimiter)
                if config.split_discrete_index < len(parts):
                    taxon.discrete_traits = parts[config.split_discrete_index].strip()

            # Split and extract continuous trait
            if config.split_continuous_enabled and config.split_continuous_delimiter:
                parts = original_name.split(config.split_continuous_delimiter)
                if config.split_continuous_index < len(parts):
                    taxon.continuous_traits = parts[config.split_continuous_index].strip()

            # Use numbering as name if requested
            if config.use_numbering:
                taxon.name = str(taxon.id)

            result.append(taxon)

        return result
