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
class AlignmentResult:
    """Result of a standalone alignment operation."""
    success: bool
    output_file: str = ""
    error_message: Optional[str] = None


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
    # True when at least one taxon has a meaningful (non-zero, non-empty) continuous trait.
    # Controls whether traitconf.csv is generated and loaded in the visualization.
    has_continuous_traits: bool = False

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
                             output_path: str, prefix: str,
                             extra_args: List[str] = None) -> AnalysisResult:
        """
        Run haplotype network analysis.

        Workflow:
          1. Write input FASTA
          2. Align with MAFFT (or MUSCLE fallback) if sequences have different lengths
          3. Process haplotypes: identify unique sequences, write PHYLIP + supporting files
          4. Call fastHaN to build the network (original_tcs / modified_tcs / msn / mjn)
          5. Generate visualization via GenNetworkConfig2

        All output files are named  <output_path>/<prefix>_*.

        Args:
            network_type: One of "original_tcs", "modified_tcs", "mjn", "msn"
            taxons: List of selected taxons
            output_path: Directory for output files
            prefix: Project name used as output file name prefix
            extra_args: Additional CLI arguments passed to fastHaN (e.g. ['-t', '4', '-e', '1'])

        Returns:
            AnalysisResult with prefix and success status
        """
        if extra_args is None:
            extra_args = []
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
            taxon_lookup = {t.name: (t.continuous_traits, t.discrete_traits) for t in taxons}
            self._log("Processing haplotypes...")
            hap_ok, has_continuous_traits = self._process_haplotypes(
                aligned_fasta, file_suffix, taxon_lookup)
            if not hap_ok:
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
                cmd = [exe_path, network_type, "-i", seq_phy_file] + extra_args + ["-o", file_suffix]
                self._log(f"Running: {' '.join(cmd)}")
                process = subprocess.run(
                    cmd,
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
                success = self._generate_visualization(
                    prefix, output_path, has_continuous_traits)

            self._update_progress(100)

        except Exception as e:
            self._log(f"Analysis error: {str(e)}")
            self._log(traceback.format_exc())
            return AnalysisResult(prefix, False, output_path, str(e),
                                  haplotype_ready=haplotype_ready)

        return AnalysisResult(prefix, success, output_path,
                              haplotype_ready=haplotype_ready,
                              has_continuous_traits=has_continuous_traits)

    # ── Alignment helpers ───────────────────────────────────────────────────────

    def _are_sequences_aligned(self, taxons: List[TaxonData]) -> bool:
        """Return True if all sequences have the same length."""
        if not taxons:
            return True
        first_length = len(taxons[0].sequence)
        return all(len(t.sequence) == first_length for t in taxons)

    def run_alignment(self, taxons: List[TaxonData], output_path: str, prefix: str,
                      config) -> "AlignmentResult":
        """
        Run a standalone multiple sequence alignment (without full network analysis).

        Args:
            taxons:      Selected sequences to align
            output_path: Directory for output files
            prefix:      Project name used as file name prefix
            config:      SequenceAlignmentConfig with tool + parameter settings

        Returns:
            AlignmentResult with success flag and output file path
        """
        FileService.ensure_directory(output_path)
        input_fasta  = os.path.join(output_path, f"{prefix}.fasta")
        output_fasta = os.path.join(output_path, f"{prefix}_aln.fasta")

        try:
            self.file_service.write_analysis_fasta(input_fasta, taxons)
            self._log(f"Input FASTA written: {input_fasta}")

            if config.tool == "muscle":
                extra_args = config.to_muscle_extra_args()
                self._log(f"Running MUSCLE with args: {extra_args}")
                ok = self._run_muscle_alignment(input_fasta, output_fasta,
                                                extra_args=extra_args)
                tool_name = "MUSCLE"
            else:
                method_args = config.to_mafft_method_args()
                add_inputorder = not config.mafft_reorder
                self._log(f"Running MAFFT with args: {method_args}")
                ok = self._run_mafft_alignment(input_fasta, output_fasta,
                                               method_args=method_args,
                                               add_inputorder=add_inputorder)
                tool_name = "MAFFT"

            if ok:
                self._log(f"{tool_name} alignment succeeded → {output_fasta}")
                return AlignmentResult(success=True, output_file=output_fasta)
            else:
                return AlignmentResult(
                    success=False,
                    error_message=f"{tool_name} alignment failed or binary not found")

        except Exception as e:
            self._log(f"Alignment error: {e}")
            return AlignmentResult(success=False, error_message=str(e))

    def _run_mafft_alignment(self, input_file: str, output_file: str,
                              method_args: List[str] = None,
                              add_inputorder: bool = True) -> bool:
        """
        Run MAFFT multiple sequence alignment.

        Tries platform-specific lib binary first, then falls back to system mafft.

        Args:
            input_file:      Input FASTA file path
            output_file:     Output aligned FASTA file path
            method_args:     MAFFT algorithm/option arguments (default: ['--retree', '2'])
            add_inputorder:  Prepend --inputorder flag (default: True).
                             Set to False when method_args already contains --reorder.

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
                order_flag = ["--inputorder"] if add_inputorder else []
                cmd = [mafft_cmd] + order_flag + method_args + [input_file]
                with open(output_file, 'w') as out_f:
                    process = subprocess.run(
                        cmd,
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

    def _run_muscle_alignment(self, input_file: str, output_file: str,
                               extra_args: List[str] = None) -> bool:
        """
        Run MUSCLE alignment.

        Args:
            input_file:  Input FASTA file path
            output_file: Output aligned FASTA file path
            extra_args:  Additional MUSCLE options (e.g. ['-diags', '-maxiters', '8'])

        Returns:
            True if alignment succeeded
        """
        if extra_args is None:
            extra_args = []

        candidates = [
            os.path.join(self.lib_path, "muscle3"),
            os.path.join(self.lib_path, "muscle"),
            "muscle3",
            "muscle",
        ]

        for muscle_cmd in candidates:
            for base_args in (
                [muscle_cmd, "-align", input_file, "-output", output_file],  # muscle5
                [muscle_cmd, "-in",    input_file, "-out",    output_file],  # muscle3
            ):
                try:
                    cmd = base_args + extra_args
                    process = subprocess.run(cmd, capture_output=True, timeout=600)

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

    def _parse_analysis_header(self, header: str) -> str:
        """
        Parse analysis FASTA header.

        Expected format: name (plain sequence name only)

        Returns:
            name
        """
        return header

    def _process_haplotypes(self, aligned_fasta: str, output_prefix: str,
                             taxon_lookup: dict = None) -> Tuple[bool, bool]:
        """
        Process aligned FASTA sequences into haplotypes and write all required files.

        Reads aligned FASTA with headers: >name (plain sequence name only)

        Traits (continuous_traits, discrete_traits) are resolved from taxon_lookup
        keyed by sequence name: {name: (continuous_traits, discrete_traits)}

        Produces:
            _seq.fasta       – all sequences with original sequence IDs (fastHaN pipeline input)
            _seq.phy         – PHYLIP format of _seq.fasta, all sequences (fastHaN input)
            _hap.fasta       – unique (non-redundant) haplotype sequences labeled H1, H2, …
            _hap_trait.csv   – aggregated trait data per haplotype
            _seq_trait.csv   – trait data per individual sequence
            _seq.meta.csv    – per-sample metadata: sequence_name, haplotype, continuous_traits, discrete_traits
            _traitconf.csv   – continuous trait per sequence (only when continuous traits exist)

        Args:
            aligned_fasta: Path to aligned FASTA file
            output_prefix: Path prefix for all output files (no extension)
            taxon_lookup: Optional dict {name: (continuous_traits, discrete_traits)}

        Returns:
            (success, has_continuous_traits) tuple
        """
        if taxon_lookup is None:
            taxon_lookup = {}

        # Determine upfront whether any taxon carries a meaningful continuous trait.
        has_continuous = any(
            cont.strip() not in ("", "0")
            for cont, _ in taxon_lookup.values()
        )

        try:
            # ── Read aligned FASTA ────────────────────────────────────────────
            sequences: List[Tuple[str, str]] = []
            # each entry: (name, sequence)

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
                            name = self._parse_analysis_header(current_header)
                            sequences.append((name, seq))
                        current_header = line[1:]
                        seq_lines = []
                    else:
                        seq_lines.append(line)

                if current_header is not None and seq_lines:
                    seq = ''.join(seq_lines).upper()
                    name = self._parse_analysis_header(current_header)
                    sequences.append((name, seq))

            if not sequences:
                self._log("No sequences found in aligned FASTA")
                return False

            seq_len = len(sequences[0][1])

            # ── Identify unique haplotypes ────────────────────────────────────
            seq_to_hap: dict = {}     # sequence_str  → hap_name
            hap_sequences: dict = {}  # hap_name      → sequence_str
            hap_info: dict = {}       # hap_name      → [(name, cont, disc)]
            hap_counter = 0

            for name, seq in sequences:
                if seq not in seq_to_hap:
                    hap_counter += 1
                    hap_name = f"H{hap_counter}"
                    seq_to_hap[seq] = hap_name
                    hap_sequences[hap_name] = seq
                    hap_info[hap_name] = []
                hap_name = seq_to_hap[seq]
                cont, disc = taxon_lookup.get(name, ("0", ""))
                hap_info[hap_name].append((name, cont, disc))

            hap_names = list(hap_sequences.keys())
            self._log(
                f"Identified {len(hap_names)} unique haplotypes from {len(sequences)} sequences")

            # ── Write _seq.fasta ──────────────────────────────────────────────
            # All sequences with original sequence IDs (no analysis metadata in header).
            with open(f"{output_prefix}_seq.fasta", 'w', encoding='utf-8') as f:
                for name, seq in sequences:
                    f.write(f">{name}\n{seq}\n")

            # ── Write _seq.phy (fastHaN input) ────────────────────────────────
            # All sequences in PHYLIP format with full original names.
            seq_phy = f"{output_prefix}_seq.phy"
            with open(seq_phy, 'w', encoding='utf-8') as f:
                f.write(f" {len(sequences)} {seq_len}\n")
                for name, seq in sequences:
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
                    ['sequence_name', 'haplotype', 'continuous_traits', 'discrete_traits'])
                for name, seq in sequences:
                    cont, disc = taxon_lookup.get(name, ("0", ""))
                    writer.writerow([name, seq_to_hap[seq], cont, disc])

            # ── Write _traitconf.csv (only when meaningful continuous traits exist) ──
            # Continuous trait per sequence: seqname;continuous_traits
            if has_continuous:
                with open(f"{output_prefix}_traitconf.csv", 'w', encoding='utf-8') as f:
                    for name, _ in sequences:
                        cont, _ = taxon_lookup.get(name, ("0", ""))
                        f.write(f"{name};{cont}\n")

            # ── Write _hap_trait.csv ──────────────────────────────────────────
            with open(f"{output_prefix}_hap_trait.csv", 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(
                    ['haplotype', 'total_quantity', 'continuous_traits',
                     'discrete_traits', 'samples'])
                for hap_name in hap_names:
                    members = hap_info[hap_name]
                    total_qty = len(members)
                    cont_traits = members[0][1] if members else "0"
                    disc_traits = ";".join(sorted({m[2] for m in members if m[2]}))
                    samples = ";".join(m[0] for m in members)
                    writer.writerow([hap_name, total_qty, cont_traits, disc_traits, samples])

            # ── Write _seq_trait.csv ──────────────────────────────────────────
            with open(f"{output_prefix}_seq_trait.csv", 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['name', 'quantity', 'continuous_traits', 'discrete_traits'])
                for name, _ in sequences:
                    cont, disc = taxon_lookup.get(name, ("0", ""))
                    writer.writerow([name, 1, cont, disc])

            return True, has_continuous

        except Exception as e:
            self._log(f"Haplotype processing error: {str(e)}")
            self._log(traceback.format_exc())
            return False, False

    # ── Visualization helpers ───────────────────────────────────────────────────

    def _generate_visualization(self, prefix: str, output_path: str,
                                 has_continuous_traits: bool = False) -> bool:
        """Generate visualization files from GML network output."""
        try:
            gml_file = os.path.join(output_path, f"{prefix}.gml")
            hap_file = os.path.join(output_path, f"{prefix}_seq.meta.csv")
            out_prefix = os.path.join(output_path, prefix)

            generate_network_config(gml_file, hap_file, out_prefix,
                                    has_continuous_traits=has_continuous_traits)

            js_file = os.path.join(output_path, f"{prefix}.js")
            if os.path.isfile(js_file):
                html_file = os.path.join(output_path, f"{prefix}.html")
                self._generate_network_html(html_file, js_file)
                return True

            return False
        except Exception as e:
            self._log(f"Visualization error: {str(e)}")
            return False

    def _generate_network_html(self, html_file: str, js_file: str) -> None:
        """Generate network visualization HTML that uses statics/tcsbu/ resources.

        The generated HTML embeds the data script (js_file) before tcsBU.js so
        that the auto-load block in tcsBU.js can call loadGraph/loadGroups/
        loadHaplotypes/loadTraits immediately on page ready.

        Uses pathlib.Path.as_uri() for file:// URL construction so this method
        is safe to call from a worker thread (no Qt objects needed).
        """
        from pathlib import Path

        tcsbu_dir = os.path.join(self.root_path, "statics", "tcsbu")

        def fu(name: str) -> str:
            """Return an absolute file:// URL for a tcsbu asset."""
            return Path(os.path.join(tcsbu_dir, name)).as_uri()

        js_url = Path(js_file).as_uri()

        html = (
            '<!DOCTYPE html>\n'
            '<html>\n'
            '<head>\n'
            '<title>tcsBU - TCS Beautifier</title>\n'
            '  <meta charset="UTF-8">\n'
            '  <meta name="viewport" content="initial-scale=1.0, user-scalable=no">\n'
            f'  <link rel="stylesheet" type="text/css" href="{fu("w2ui.min.css")}" />\n'
            f'  <link rel="stylesheet" type="text/css" href="{fu("tcsBU.min.css")}" />\n'
            f'  <script type="text/javascript" src="{fu("jquery-3.2.1.min.js")}"></script>\n'
            f'  <script type="text/javascript" src="{fu("w2ui.min.js")}"></script>\n'
            f'  <script type="text/javascript" src="{fu("d3.min.js")}"></script>\n'
            f'  <script type="text/javascript" src="{fu("FileSaver.min.js")}"></script>\n'
            f'  <script type="text/javascript" src="{js_url}"></script>\n'
            f'  <script type="text/javascript" src="{fu("tcsBU.js")}"></script>\n'
            '</head>\n'
            '<body>\n'
            '<div id="layout" style="width: 100%; height: 100%;"></div>\n'
            '</body>\n'
            '</html>\n'
        )
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
