"""
Service for running haplotype network analyses and external programs.
Corresponds to the analysis_network and related methods in VB.NET.
"""
import csv
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Callable, Tuple

from model.taxon_data import TaxonData
from service.file_service import FileService


@dataclass
class AnalysisResult:
    """Result of an analysis operation."""
    timestamp: int
    success: bool
    output_path: str = ""
    error_message: Optional[str] = None

    def get_html_report_path(self) -> str:
        return os.path.join(self.output_path, f"{self.timestamp}_report.html")

    def get_visualization_path(self) -> str:
        return os.path.join(self.output_path, f"{self.timestamp}.html")


class AnalysisService:
    """Service for running haplotype network analyses."""

    def __init__(self, application_path: str):
        """
        Initialize analysis service.

        Args:
            application_path: Root application directory
        """
        self.root_path = application_path
        self.lib_path = os.path.join(application_path, "lib")
        self.file_service = FileService()

        # Callbacks for progress and logging
        self._progress_callback: Optional[Callable[[int], None]] = None
        self._log_callback: Optional[Callable[[str], None]] = None

    def set_progress_callback(self, callback: Callable[[int], None]) -> None:
        """Set callback for progress updates."""
        self._progress_callback = callback

    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for log messages."""
        self._log_callback = callback

    def _update_progress(self, value: int) -> None:
        """Update progress."""
        if self._progress_callback:
            self._progress_callback(value)

    def _log(self, message: str) -> None:
        """Log a message."""
        if self._log_callback:
            self._log_callback(message)

    def run_network_analysis(self, network_type: str, taxons: List[TaxonData],
                             output_path: str) -> AnalysisResult:
        """
        Run haplotype network analysis.

        Workflow:
          1. Write input FASTA
          2. Align with MAFFT (or MUSCLE fallback) if sequences have different lengths
          3. Process haplotypes: identify unique sequences, write PHYLIP and supporting files
          4. Call fastHaN to build the network (MSN / MJN / modified_tcs)
          5. Generate visualization via GenNetworkConfig2
          6. Write HTML report and history

        Args:
            network_type: One of "modified_tcs", "mjn", "msn"
            taxons: List of selected taxons
            output_path: Directory for output files

        Returns:
            AnalysisResult with timestamp and success status
        """
        timestamp = int(time.time())
        formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        success = True

        FileService.ensure_directory(output_path)

        result_file_path = os.path.join(output_path, f"{timestamp}_rst.csv")

        try:
            with open(result_file_path, 'w', encoding='utf-8', newline='') as result_file:
                result_writer = csv.writer(result_file)

                # Write CSV header
                result_writer.writerow(['FileType', 'FilePath', 'Status', 'Description'])

                # Write metadata as comments
                result_file.write(f"# Network Type: {network_type}\n")
                result_file.write(f"# Analysis Time: {formatted_time}\n")
                result_file.write(f"# Timestamp: {timestamp}\n")

                # ── Step 1: Write input FASTA ──────────────────────────────────
                input_fasta = os.path.join(output_path, f"{timestamp}.fasta")
                self.file_service.write_analysis_fasta(input_fasta, taxons)
                result_writer.writerow(['Ori_seqs', input_fasta, 'Success', 'Original sequences'])
                self._update_progress(10)

                # ── Step 2: Alignment ──────────────────────────────────────────
                aligned_fasta = os.path.join(output_path, f"{timestamp}_aln.fasta")
                needs_alignment = not self._are_sequences_aligned(taxons)

                if needs_alignment:
                    self._log("Sequences are not aligned. Running MAFFT...")
                    aligned = self._run_mafft_alignment(input_fasta, aligned_fasta)
                    if not aligned:
                        self._log("MAFFT not available or failed. Trying MUSCLE...")
                        aligned = self._run_muscle_alignment(input_fasta, aligned_fasta)

                    if aligned:
                        result_writer.writerow(
                            ['Aligned_seqs', aligned_fasta, 'Success', 'Sequences aligned'])
                    else:
                        result_writer.writerow(
                            ['Aligned_seqs', aligned_fasta, 'Failed', 'Alignment failed'])
                        return AnalysisResult(timestamp, False, output_path,
                                              "Sequence alignment failed")
                else:
                    FileService.safe_copy(input_fasta, aligned_fasta)
                    result_writer.writerow(
                        ['Aligned_seqs', aligned_fasta, 'Success', 'Sequences already aligned'])

                self._update_progress(30)

                # ── Step 3: Ensure UTF-8 encoding ─────────────────────────────
                FileService.ensure_utf8(aligned_fasta)

                # ── Step 4: Process haplotypes → PHYLIP + supporting files ────
                file_suffix = os.path.join(output_path, str(timestamp))
                self._log("Processing haplotypes...")
                if not self._process_haplotypes(aligned_fasta, file_suffix, result_writer):
                    return AnalysisResult(timestamp, False, output_path,
                                          "Haplotype processing failed")
                self._update_progress(50)

                # ── Step 5: Run fastHaN ────────────────────────────────────────
                self._log(f"Building {network_type} haplotype network with fastHaN...")
                network_executable = self._get_network_executable()
                exe_path = os.path.join(self.lib_path, network_executable)
                seq_phy_file = f"{file_suffix}_seq.phy"

                if not os.path.isfile(exe_path):
                    self._log(f"Network executable not found: {exe_path}")
                    return AnalysisResult(timestamp, False, output_path,
                                          f"Executable not found: {network_executable}")

                try:
                    self._log(
                        f"Running: {exe_path} {network_type} -i {seq_phy_file} -o {file_suffix}")
                    process = subprocess.run(
                        [exe_path, network_type, "-i", seq_phy_file, "-o", file_suffix],
                        cwd=output_path,
                        capture_output=True,
                        text=True
                    )
                    if process.stdout:
                        self._log(f"fastHaN stdout: {process.stdout.strip()}")
                    if process.stderr:
                        self._log(f"fastHaN stderr: {process.stderr.strip()}")
                    if process.returncode != 0:
                        self._log(f"fastHaN exited with code {process.returncode}")
                        success = False
                except Exception as e:
                    self._log(f"Network construction error: {e}")
                    self._log(traceback.format_exc())
                    success = False

                self._update_progress(70)

                # ── Step 6: Check GML/JSON output ──────────────────────────────
                gml_file = f"{file_suffix}.gml"
                json_file = f"{file_suffix}.json"

                if os.path.isfile(gml_file):
                    result_writer.writerow(
                        ['HapNet_gml', gml_file, 'Success', 'Haplotype network in GML format'])
                    if os.path.isfile(json_file):
                        result_writer.writerow(
                            ['HapNet_json', json_file, 'Success', 'Haplotype network in JSON format'])

                    # ── Step 7: Generate visualization ─────────────────────────
                    self._log("Generating visualization...")
                    success = self._generate_visualization(timestamp, output_path, result_writer)
                else:
                    result_writer.writerow(
                        ['HapNet_gml', gml_file, 'Failed', 'GML network file not created'])
                    success = False

                self._update_progress(90)

                # ── Step 8: HTML report + history ─────────────────────────────
                report_html = os.path.join(output_path, f"{timestamp}_report.html")
                self.generate_html_report(result_file_path, report_html, str(timestamp),
                                          formatted_time, success)
                result_writer.writerow(['Report_html', report_html, 'Success', 'Analysis report'])

                self._append_to_history(output_path, formatted_time, timestamp, network_type)
                self._update_progress(100)

        except Exception as e:
            self._log(f"Analysis error: {str(e)}")
            self._log(traceback.format_exc())
            return AnalysisResult(timestamp, False, output_path, str(e))

        return AnalysisResult(timestamp, success, output_path)

    # ── Alignment helpers ───────────────────────────────────────────────────────

    def _are_sequences_aligned(self, taxons: List[TaxonData]) -> bool:
        """Check if all sequences have the same length (already aligned)."""
        if not taxons:
            return True
        first_length = len(taxons[0].sequence)
        return all(len(t.sequence) == first_length for t in taxons)

    def _run_mafft_alignment(self, input_file: str, output_file: str,
                              method_args: List[str] = None) -> bool:
        """
        Run MAFFT multiple sequence alignment.

        Tries platform-specific lib binary first, then falls back to system mafft.

        Args:
            input_file: Input FASTA file path
            output_file: Output aligned FASTA file path
            method_args: MAFFT algorithm arguments (default: ['--retree', '2'])

        Returns:
            True if alignment succeeded
        """
        if method_args is None:
            method_args = ["--retree", "2"]

        # Build candidate list: (mafft_command, working_directory)
        candidates: List[Tuple[str, Optional[str]]] = []

        if self._is_windows():
            mafft_dir = os.path.join(self.lib_path, "mafft-win")
            candidates.append((os.path.join(mafft_dir, "mafft.bat"), mafft_dir))
        elif self._is_mac():
            mafft_dir = os.path.join(self.lib_path, "mafft-mac", "mafftdir", "bin")
            candidates.append((os.path.join(mafft_dir, "mafft"), mafft_dir))
        else:
            # Linux: check lib for a bundled mafft
            linux_lib_mafft = os.path.join(self.lib_path, "mafft")
            if os.path.isfile(linux_lib_mafft):
                candidates.append((linux_lib_mafft, None))

        # Always try system mafft as final fallback
        candidates.append(("mafft", None))

        for mafft_cmd, work_dir in candidates:
            try:
                with open(output_file, 'w') as out_f:
                    process = subprocess.run(
                        [mafft_cmd, "--inputorder"] + method_args + [input_file],
                        cwd=work_dir,
                        stdout=out_f,
                        stderr=subprocess.PIPE,
                        timeout=600
                    )

                if (process.returncode == 0
                        and os.path.isfile(output_file)
                        and os.path.getsize(output_file) > 0):
                    self._log(f"MAFFT alignment succeeded using: {mafft_cmd}")
                    return True

                # Clean up empty/failed output
                if os.path.isfile(output_file):
                    os.remove(output_file)

            except (FileNotFoundError, PermissionError):
                if os.path.isfile(output_file):
                    try:
                        os.remove(output_file)
                    except OSError:
                        pass
            except subprocess.TimeoutExpired:
                self._log("MAFFT timed out")
                if os.path.isfile(output_file):
                    try:
                        os.remove(output_file)
                    except OSError:
                        pass

        return False

    def _run_muscle_alignment(self, input_file: str, output_file: str) -> bool:
        """
        Run MUSCLE alignment as fallback when MAFFT is unavailable.

        Args:
            input_file: Input FASTA file path
            output_file: Output aligned FASTA file path

        Returns:
            True if alignment succeeded
        """
        candidates = [
            os.path.join(self.lib_path, "muscle3"),
            os.path.join(self.lib_path, "muscle"),
            "muscle3",
            "muscle",
        ]

        for muscle_cmd in candidates:
            # muscle5-style: -align input -output output
            for args in (
                [muscle_cmd, "-align", input_file, "-output", output_file],
                [muscle_cmd, "-in", input_file, "-out", output_file],   # muscle3-style
            ):
                try:
                    process = subprocess.run(args, capture_output=True, timeout=600)

                    if (process.returncode == 0
                            and os.path.isfile(output_file)
                            and os.path.getsize(output_file) > 0):
                        self._log(f"MUSCLE alignment succeeded using: {muscle_cmd}")
                        return True

                    if os.path.isfile(output_file):
                        os.remove(output_file)

                except (FileNotFoundError, PermissionError):
                    if os.path.isfile(output_file):
                        try:
                            os.remove(output_file)
                        except OSError:
                            pass
                    break  # This candidate doesn't exist; try next
                except subprocess.TimeoutExpired:
                    self._log(f"MUSCLE timed out with: {muscle_cmd}")
                    if os.path.isfile(output_file):
                        try:
                            os.remove(output_file)
                        except OSError:
                            pass

        return False

    # ── Haplotype processing ────────────────────────────────────────────────────

    def _parse_analysis_header(self, header: str) -> Tuple[str, int, str, str]:
        """
        Parse analysis FASTA header.

        Expected format:  name=quantity=continuous_traits$SPLIT$discrete_traits
        Falls back gracefully if fields are missing.

        Returns:
            (name, quantity, continuous_traits, discrete_traits)
        """
        if '$SPLIT$' in header:
            main_part, discrete_traits = header.split('$SPLIT$', 1)
        else:
            main_part = header
            discrete_traits = ""

        parts = main_part.split('=')
        name = parts[0] if parts else header

        try:
            quantity = int(parts[1]) if len(parts) > 1 else 1
        except (ValueError, TypeError):
            quantity = 1

        continuous_traits = parts[2] if len(parts) > 2 else "0"
        return name, quantity, continuous_traits, discrete_traits

    def _process_haplotypes(self, aligned_fasta: str, output_prefix: str,
                             result_writer) -> bool:
        """
        Process aligned FASTA sequences into haplotypes and write all required files.

        Reads aligned FASTA with headers:
            >name=quantity=continuous_traits$SPLIT$discrete_traits

        Produces:
            _seq.phy        – unique haplotypes in PHYLIP format  (fastHaN input)
            _hap.phy        – same content as _seq.phy (haplotype reference)
            _hap.fasta      – unique haplotypes in FASTA format
            _seq.fasta      – all sequences in FASTA format
            .meta           – tab-separated metadata per sample
            _hap_trait.csv  – aggregated trait data per haplotype
            _seq_trait.csv  – trait data per individual sequence
            _seq2hap.csv    – mapping: sample_name → haplotype_name

        Args:
            aligned_fasta: Path to aligned FASTA file
            output_prefix: Path prefix for all output files (no extension)
            result_writer:  csv.writer to record file status

        Returns:
            True on success
        """
        try:
            # ── Read aligned FASTA ────────────────────────────────────────────
            sequences: List[Tuple[str, int, str, str, str]] = []
            # each entry: (name, quantity, continuous_traits, discrete_traits, sequence)

            encoding = FileService.detect_encoding(aligned_fasta)
            with open(aligned_fasta, 'r', encoding=encoding) as f:
                current_header: Optional[str] = None
                seq_lines: List[str] = []

                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('>'):
                        if current_header is not None and seq_lines:
                            seq = ''.join(seq_lines).upper()
                            name, qty, cont, disc = self._parse_analysis_header(current_header)
                            sequences.append((name, qty, cont, disc, seq))
                        current_header = line[1:]
                        seq_lines = []
                    else:
                        seq_lines.append(line)

                # Flush last record
                if current_header is not None and seq_lines:
                    seq = ''.join(seq_lines).upper()
                    name, qty, cont, disc = self._parse_analysis_header(current_header)
                    sequences.append((name, qty, cont, disc, seq))

            if not sequences:
                self._log("No sequences found in aligned FASTA")
                return False

            seq_len = len(sequences[0][4])

            # ── Identify unique haplotypes ────────────────────────────────────
            seq_to_hap: dict = {}     # sequence_str  → hap_name
            hap_sequences: dict = {}  # hap_name      → sequence_str
            hap_info: dict = {}       # hap_name      → [(name, qty, cont, disc)]
            hap_counter = 0

            for name, qty, cont, disc, seq in sequences:
                if seq not in seq_to_hap:
                    hap_counter += 1
                    hap_name = f"H{hap_counter}"
                    seq_to_hap[seq] = hap_name
                    hap_sequences[hap_name] = seq
                    hap_info[hap_name] = []
                hap_name = seq_to_hap[seq]
                hap_info[hap_name].append((name, qty, cont, disc))

            hap_names = list(hap_sequences.keys())
            self._log(
                f"Identified {len(hap_names)} unique haplotypes from {len(sequences)} sequences")

            # ── Write _seq.phy (input for fastHaN) ───────────────────────────
            # Contains one row per unique haplotype in strict PHYLIP format.
            # Name field is 10 characters wide (padded / truncated).
            seq_phy = f"{output_prefix}_seq.phy"
            with open(seq_phy, 'w', encoding='utf-8') as f:
                f.write(f" {len(hap_names)} {seq_len}\n")
                for hap_name in hap_names:
                    padded = hap_name[:10].ljust(10)
                    f.write(f"{padded}{hap_sequences[hap_name]}\n")

            # ── Write _hap.phy ────────────────────────────────────────────────
            hap_phy = f"{output_prefix}_hap.phy"
            shutil.copy2(seq_phy, hap_phy)

            # ── Write _hap.fasta ──────────────────────────────────────────────
            hap_fasta_path = f"{output_prefix}_hap.fasta"
            with open(hap_fasta_path, 'w', encoding='utf-8') as f:
                for hap_name in hap_names:
                    f.write(f">{hap_name}\n{hap_sequences[hap_name]}\n")

            # ── Write _seq.fasta ──────────────────────────────────────────────
            seq_fasta_path = f"{output_prefix}_seq.fasta"
            with open(seq_fasta_path, 'w', encoding='utf-8') as f:
                for name, qty, cont, disc, seq in sequences:
                    f.write(f">{name}={qty}={cont}$SPLIT${disc}\n{seq}\n")

            # ── Write .meta ───────────────────────────────────────────────────
            meta_path = f"{output_prefix}.meta"
            with open(meta_path, 'w', encoding='utf-8') as f:
                f.write("name\tquantity\tcontinuous_traits\tdiscrete_traits\thaplotype\n")
                for name, qty, cont, disc, seq in sequences:
                    f.write(f"{name}\t{qty}\t{cont}\t{disc}\t{seq_to_hap[seq]}\n")

            # ── Write _seq2hap.csv ────────────────────────────────────────────
            seq2hap_path = f"{output_prefix}_seq2hap.csv"
            with open(seq2hap_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(
                    ['sequence_name', 'haplotype', 'quantity', 'continuous_traits',
                     'discrete_traits'])
                for name, qty, cont, disc, seq in sequences:
                    writer.writerow([name, seq_to_hap[seq], qty, cont, disc])

            # ── Write _hap_trait.csv ──────────────────────────────────────────
            hap_trait_path = f"{output_prefix}_hap_trait.csv"
            with open(hap_trait_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(
                    ['haplotype', 'total_quantity', 'continuous_traits',
                     'discrete_traits', 'samples'])
                for hap_name in hap_names:
                    members = hap_info[hap_name]
                    total_qty = sum(m[1] for m in members)
                    cont_traits = members[0][2] if members else "0"
                    disc_traits = ";".join(
                        sorted({m[3] for m in members if m[3]}))
                    samples = ";".join(m[0] for m in members)
                    writer.writerow([hap_name, total_qty, cont_traits, disc_traits, samples])

            # ── Write _seq_trait.csv ──────────────────────────────────────────
            seq_trait_path = f"{output_prefix}_seq_trait.csv"
            with open(seq_trait_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['name', 'quantity', 'continuous_traits', 'discrete_traits'])
                for name, qty, cont, disc, _ in sequences:
                    writer.writerow([name, qty, cont, disc])

            # ── Record files in result CSV ────────────────────────────────────
            if result_writer:
                result_writer.writerow(
                    ['Hap_seq_phylip', hap_phy, 'Success',
                     'Haplotype sequences in PHYLIP format'])
                result_writer.writerow(
                    ['Hap_seq_fasta', hap_fasta_path, 'Success',
                     'Haplotype sequences in FASTA format'])
                result_writer.writerow(
                    ['Seq_with_traits_phylip', seq_phy, 'Success',
                     'Aligned sequences with traits in PHYLIP format'])
                result_writer.writerow(
                    ['Seq_with_traits_fasta', seq_fasta_path, 'Success',
                     'Aligned sequences with traits in FASTA format'])
                result_writer.writerow(
                    ['Seq_metadata', meta_path, 'Success', 'Sequence metadata'])
                result_writer.writerow(
                    ['Hap_trait', hap_trait_path, 'Success', 'Haplotype trait information'])
                result_writer.writerow(
                    ['Seq_trait', seq_trait_path, 'Success', 'Sequence trait information'])
                result_writer.writerow(
                    ['Seq2Hap', seq2hap_path, 'Success', 'Sequence to haplotype mapping'])

            return True

        except Exception as e:
            self._log(f"Haplotype processing error: {str(e)}")
            self._log(traceback.format_exc())
            return False

    # ── Visualization helpers ───────────────────────────────────────────────────

    def _generate_visualization(self, timestamp: int, output_path: str,
                                 result_writer=None) -> bool:
        """Generate visualization files from GML network output."""
        try:
            config_executable = os.path.join(
                self.lib_path,
                "GenNetworkConfig2" + (".exe" if self._is_windows() else "")
            )

            subprocess.run(
                [config_executable,
                 f"{timestamp}.gml",
                 f"{timestamp}_seq2hap.csv",
                 str(timestamp)],
                cwd=output_path,
                capture_output=True
            )

            js_file = os.path.join(output_path, f"{timestamp}.js")
            if os.path.isfile(js_file):
                html_file = os.path.join(output_path, f"{timestamp}.html")
                self._generate_network_html(html_file, f"{timestamp}.js")

                if result_writer is not None:
                    result_writer.writerow(
                        ['HapNet_js', js_file, 'Success', 'Visualization JavaScript'])
                    result_writer.writerow(
                        ['HapNet_html', html_file, 'Success', 'Visualization HTML'])
                return True

            return False
        except Exception as e:
            self._log(f"Visualization error: {str(e)}")
            return False

    def _generate_network_html(self, html_file: str, js_file: str) -> None:
        """Generate network visualization HTML from template."""
        template_path = os.path.join(self.root_path, "statics", "en", "tcsBU.txt")
        if os.path.isfile(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            html = template.replace("$data$", js_file)
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html)

    # ── Report & history helpers ────────────────────────────────────────────────

    def generate_html_report(self, csv_path: str, html_path: str, timestamp: str,
                             analysis_time: str, success: bool) -> None:
        """Generate HTML report from results CSV."""
        try:
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write("""<!DOCTYPE html>
<html><head><meta charset='UTF-8'>
<title>Analysis Report - {timestamp}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #4CAF50; color: white; }}
.success {{ color: green; }} .failed {{ color: red; }}
</style></head><body>
<h1>Haplotype Network Analysis Report</h1>
<p><strong>Analysis Time:</strong> {analysis_time}</p>
<p><strong>Status:</strong> <span class='{status_class}'>{status}</span></p>
<h2>Generated Files</h2>
<table><tr><th>Type</th><th>File</th><th>Status</th><th>Description</th></tr>
""".format(
                    timestamp=timestamp,
                    analysis_time=analysis_time,
                    status_class='success' if success else 'failed',
                    status='Success' if success else 'Failed'
                ))

                if os.path.isfile(csv_path):
                    with open(csv_path, 'r', encoding='utf-8') as csv_file:
                        for line in csv_file:
                            if line.startswith('#') or line.startswith('FileType') or ',' not in line:
                                continue
                            parts = line.strip().split(',', 3)
                            if len(parts) >= 4:
                                status_class = 'success' if parts[2].lower() == 'success' else 'failed'
                                filename = os.path.basename(parts[1])
                                f.write(
                                    f"<tr><td>{parts[0]}</td>"
                                    f"<td><a href='{parts[1]}'>{filename}</a></td>"
                                    f"<td class='{status_class}'>{parts[2]}</td>"
                                    f"<td>{parts[3]}</td></tr>\n"
                                )

                f.write("</table></body></html>")
        except Exception as e:
            self._log(f"HTML report generation error: {str(e)}")

    def _append_to_history(self, output_path: str, time_str: str,
                            timestamp: int, description: str) -> None:
        """Append entry to history file in output directory."""
        history_file = os.path.join(output_path, "history.csv")
        file_exists = os.path.isfile(history_file)
        with open(history_file, 'a', encoding='utf-8') as f:
            if not file_exists:
                f.write("Time,Timestamp,Description\n")
            f.write(f"{time_str},{timestamp},{description}\n")

    # ── Generic executable helper ───────────────────────────────────────────────

    def run_executable(self, exe_name: str, arguments: List[str],
                       working_dir: str, expected_outputs: List[str] = None) -> bool:
        """
        Run an external executable from lib directory.

        Args:
            exe_name: Name of executable in lib directory
            arguments: Command line arguments
            working_dir: Working directory for execution
            expected_outputs: Optional list of expected output files
        """
        try:
            exe_path = os.path.join(self.lib_path, exe_name)
            cmd = [exe_path] + arguments

            process = subprocess.run(cmd, cwd=working_dir, capture_output=True)

            if expected_outputs:
                for output_file in expected_outputs:
                    if not os.path.isfile(output_file):
                        return False

            return process.returncode == 0
        except Exception as e:
            self._log(f"Executable error: {str(e)}")
            return False

    def show_in_explorer(self, file_path: str) -> None:
        """Show file in system file explorer."""
        try:
            if self._is_windows():
                subprocess.run(['explorer', '/select,', file_path])
            elif self._is_mac():
                subprocess.run(['open', '-R', file_path])
            else:
                subprocess.run(['xdg-open', os.path.dirname(file_path)])
        except Exception as e:
            self._log(f"Explorer error: {str(e)}")

    # ── Platform helpers ────────────────────────────────────────────────────────

    def _get_network_executable(self) -> str:
        """
        Get the appropriate fastHaN executable for the current platform.

        Searches the lib directory for candidates in order of preference and
        returns the first one that actually exists on disk.
        Falls back to the first candidate name even if not found (so the
        subprocess call will produce a clear FileNotFoundError).
        """
        arch = platform.machine().lower()

        if self._is_windows():
            candidates = [
                "fastHaN_win_arm.exe" if 'arm' in arch else "fastHaN_win_intel.exe",
                "fastHaN.exe",
                "fastHaN",
            ]
        elif self._is_mac():
            candidates = [
                "fastHaN_mac_arm" if 'arm' in arch else "fastHaN_mac_intel",
                "fastHaN",
            ]
        else:  # Linux
            candidates = [
                "fastHaN_linux",
                "fastHaN",
            ]

        for name in candidates:
            if os.path.isfile(os.path.join(self.lib_path, name)):
                return name

        return candidates[0]  # Return first even if absent; subprocess will report the error

    @staticmethod
    def _is_windows() -> bool:
        return sys.platform.startswith('win')

    @staticmethod
    def _is_mac() -> bool:
        return sys.platform == 'darwin'
