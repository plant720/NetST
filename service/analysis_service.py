"""
Service for running haplotype network analyses and external programs.
Corresponds to the analysis_network and related methods in VB.NET.
"""
import csv
import os
import platform
import subprocess
import sys
import traceback
from dataclasses import dataclass
from typing import List, Optional, Callable, Tuple

from model.taxon_data import TaxonData
from service.file_service import FileService
from service.gen_network_config import generate_network_config


@dataclass
class AnalysisResult:
    """Result of an analysis operation."""
    prefix: str          # project name / file prefix
    success: bool
    output_path: str = ""
    error_message: Optional[str] = None
    # True as soon as _process_haplotypes() succeeds, even if later steps fail.
    # The haplotype tab should be shown whenever this is True.
    haplotype_ready: bool = False

    def get_visualization_path(self) -> str:
        return os.path.join(self.output_path, f"{self.prefix}.html")


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

        self._progress_callback: Optional[Callable[[int], None]] = None
        self._log_callback: Optional[Callable[[str], None]] = None

    def set_progress_callback(self, callback: Callable[[int], None]) -> None:
        self._progress_callback = callback

    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        self._log_callback = callback

    def _update_progress(self, value: int) -> None:
        if self._progress_callback:
            self._progress_callback(value)

    def _log(self, message: str) -> None:
        if self._log_callback:
            self._log_callback(message)

    # ── Main analysis entry point ───────────────────────────────────────────────

    def run_network_analysis(self, network_type: str, taxons: List[TaxonData],
                             output_path: str, prefix: str) -> AnalysisResult:
        """
        Run haplotype network analysis.

        Workflow:
          1. Write input FASTA
          2. Align with MAFFT (or MUSCLE fallback) if sequences have different lengths
          3. Process haplotypes: identify unique sequences, write PHYLIP + supporting files
          4. Call fastHaN to build the network (msn / mjn / modified_tcs)
          5. Generate visualization via GenNetworkConfig2

        All output files are named  <output_path>/<prefix>_*.

        Args:
            network_type: One of "modified_tcs", "mjn", "msn"
            taxons: List of selected taxons
            output_path: Directory for output files
            prefix: Project name used as output file name prefix

        Returns:
            AnalysisResult with prefix and success status
        """
        FileService.ensure_directory(output_path)

        # Tracks whether _process_haplotypes() wrote its output files.
        # The haplotype tab should be shown whenever this is True, even if
        # downstream steps (fastHaN, visualization) fail.
        haplotype_ready = False

        try:
            # ── Step 1: Write input FASTA ──────────────────────────────────────
            input_fasta = os.path.join(output_path, f"{prefix}.fasta")
            self.file_service.write_analysis_fasta(input_fasta, taxons)
            self._update_progress(10)

            # ── Step 2: Alignment ──────────────────────────────────────────────
            aligned_fasta = os.path.join(output_path, f"{prefix}_aln.fasta")
            needs_alignment = not self._are_sequences_aligned(taxons)

            if needs_alignment:
                self._log("Sequences are not aligned. Running MAFFT...")
                aligned = self._run_mafft_alignment(input_fasta, aligned_fasta)
                if not aligned:
                    self._log("MAFFT not available or failed. Trying MUSCLE...")
                    aligned = self._run_muscle_alignment(input_fasta, aligned_fasta)

                if not aligned:
                    return AnalysisResult(prefix, False, output_path,
                                          "Sequence alignment failed")
            else:
                FileService.safe_copy(input_fasta, aligned_fasta)
                self._log("Sequences already aligned — skipping alignment step")

            self._update_progress(30)

            # ── Step 3: Ensure UTF-8 encoding ─────────────────────────────────
            FileService.ensure_utf8(aligned_fasta)

            # ── Step 4: Process haplotypes → PHYLIP + supporting files ─────────
            file_suffix = os.path.join(output_path, prefix)
            self._log("Processing haplotypes...")
            if not self._process_haplotypes(aligned_fasta, file_suffix):
                return AnalysisResult(prefix, False, output_path,
                                      "Haplotype processing failed")

            # CSV / mapping files are now on disk — haplotype tab can be shown
            haplotype_ready = True
            self._update_progress(50)

            # ── Step 5: Run fastHaN ────────────────────────────────────────────
            self._log(f"Building {network_type} haplotype network with fastHaN...")
            network_executable = self._get_network_executable()
            exe_path = os.path.join(self.lib_path, network_executable)
            seq_phy_file = f"{file_suffix}_seq.phy"

            if not os.path.isfile(exe_path):
                self._log(f"Network executable not found: {exe_path}")
                return AnalysisResult(prefix, False, output_path,
                                      f"Executable not found: {network_executable}",
                                      haplotype_ready=haplotype_ready)

            success = True
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

            # ── Step 6: Check GML output ───────────────────────────────────────
            gml_file = f"{file_suffix}.gml"
            if not os.path.isfile(gml_file):
                self._log("GML network file was not created by fastHaN")
                success = False

            if success:
                # ── Step 7: Generate visualization ────────────────────────────
                self._log("Generating visualization...")
                success = self._generate_visualization(prefix, output_path)

            self._update_progress(100)

        except Exception as e:
            self._log(f"Analysis error: {str(e)}")
            self._log(traceback.format_exc())
            return AnalysisResult(prefix, False, output_path, str(e),
                                  haplotype_ready=haplotype_ready)

        return AnalysisResult(prefix, success, output_path,
                              haplotype_ready=haplotype_ready)

    # ── Alignment helpers ───────────────────────────────────────────────────────

    def _are_sequences_aligned(self, taxons: List[TaxonData]) -> bool:
        """Return True if all sequences have the same length."""
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

        candidates: List[Tuple[str, Optional[str]]] = []

        if self._is_windows():
            mafft_dir = os.path.join(self.lib_path, "mafft-win")
            candidates.append((os.path.join(mafft_dir, "mafft.bat"), mafft_dir))
        elif self._is_mac():
            mafft_dir = os.path.join(self.lib_path, "mafft-mac", "mafftdir", "bin")
            candidates.append((os.path.join(mafft_dir, "mafft"), mafft_dir))
        else:
            linux_lib_mafft = os.path.join(self.lib_path, "mafft")
            if os.path.isfile(linux_lib_mafft):
                candidates.append((linux_lib_mafft, None))

        candidates.append(("mafft", None))  # system fallback

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
            for args in (
                [muscle_cmd, "-align", input_file, "-output", output_file],  # muscle5
                [muscle_cmd, "-in",    input_file, "-out",    output_file],  # muscle3
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
                    break  # this candidate doesn't exist; try next
                except subprocess.TimeoutExpired:
                    self._log(f"MUSCLE timed out: {muscle_cmd}")
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

    def _process_haplotypes(self, aligned_fasta: str, output_prefix: str) -> bool:
        """
        Process aligned FASTA sequences into haplotypes and write all required files.

        Reads aligned FASTA with headers:
            >name=quantity=continuous_traits$SPLIT$discrete_traits

        Produces:
            _seq.fasta       – all sequences with original sequence IDs (fastHaN pipeline input)
            _seq.phy         – PHYLIP format of _seq.fasta, all sequences (fastHaN input)
            _hap.fasta       – unique (non-redundant) haplotype sequences labeled H1, H2, …
            _hap_trait.csv   – aggregated trait data per haplotype
            _seq_trait.csv   – trait data per individual sequence
            _seq.meta.csv    – per-sample metadata: sequence_name, haplotype, quantity, traits

        Args:
            aligned_fasta: Path to aligned FASTA file
            output_prefix: Path prefix for all output files (no extension)

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

            # ── Write _seq.fasta ──────────────────────────────────────────────
            # All sequences with original sequence IDs (no analysis metadata in header).
            with open(f"{output_prefix}_seq.fasta", 'w', encoding='utf-8') as f:
                for name, qty, cont, disc, seq in sequences:
                    f.write(f">{name}\n{seq}\n")

            # ── Write _seq.phy (fastHaN input) ────────────────────────────────
            # All sequences in PHYLIP format with full original names.
            seq_phy = f"{output_prefix}_seq.phy"
            with open(seq_phy, 'w', encoding='utf-8') as f:
                f.write(f" {len(sequences)} {seq_len}\n")
                for name, qty, cont, disc, seq in sequences:
                    f.write(f"{name} {seq}\n")

            # ── Write _hap.fasta ──────────────────────────────────────────────
            # Non-redundant unique haplotype sequences labeled H1, H2, …
            with open(f"{output_prefix}_hap.fasta", 'w', encoding='utf-8') as f:
                for hap_name in hap_names:
                    f.write(f">{hap_name}\n{hap_sequences[hap_name]}\n")

            # ── Write _seq.meta.csv ───────────────────────────────────────────
            # Per-sample metadata: replaces both the old .meta and _seq2hap.csv files.
            with open(f"{output_prefix}_seq.meta.csv", 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(
                    ['sequence_name', 'haplotype', 'quantity',
                     'continuous_traits', 'discrete_traits'])
                for name, qty, cont, disc, seq in sequences:
                    writer.writerow([name, seq_to_hap[seq], qty, cont, disc])

            # ── Write _hap_trait.csv ──────────────────────────────────────────
            with open(f"{output_prefix}_hap_trait.csv", 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(
                    ['haplotype', 'total_quantity', 'continuous_traits',
                     'discrete_traits', 'samples'])
                for hap_name in hap_names:
                    members = hap_info[hap_name]
                    total_qty = sum(m[1] for m in members)
                    cont_traits = members[0][2] if members else "0"
                    disc_traits = ";".join(sorted({m[3] for m in members if m[3]}))
                    samples = ";".join(m[0] for m in members)
                    writer.writerow([hap_name, total_qty, cont_traits, disc_traits, samples])

            # ── Write _seq_trait.csv ──────────────────────────────────────────
            with open(f"{output_prefix}_seq_trait.csv", 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['name', 'quantity', 'continuous_traits', 'discrete_traits'])
                for name, qty, cont, disc, _ in sequences:
                    writer.writerow([name, qty, cont, disc])

            return True

        except Exception as e:
            self._log(f"Haplotype processing error: {str(e)}")
            self._log(traceback.format_exc())
            return False

    # ── Visualization helpers ───────────────────────────────────────────────────

    def _generate_visualization(self, prefix: str, output_path: str, _=None) -> bool:
        """Generate visualization files from GML network output."""
        try:
            gml_file = os.path.join(output_path, f"{prefix}.gml")
            hap_file = os.path.join(output_path, f"{prefix}_seq.meta.csv")
            out_prefix = os.path.join(output_path, prefix)

            generate_network_config(gml_file, hap_file, out_prefix)

            js_file = os.path.join(output_path, f"{prefix}.js")
            if os.path.isfile(js_file):
                html_file = os.path.join(output_path, f"{prefix}.html")
                self._generate_network_html(html_file, f"{prefix}.js")
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
            process = subprocess.run(
                [exe_path] + arguments, cwd=working_dir, capture_output=True)

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
            candidates = ["fastHaN_linux", "fastHaN"]

        for name in candidates:
            if os.path.isfile(os.path.join(self.lib_path, name)):
                return name

        return candidates[0]

    @staticmethod
    def _is_windows() -> bool:
        return sys.platform.startswith('win')

    @staticmethod
    def _is_mac() -> bool:
        return sys.platform == 'darwin'
