"""
Service for running haplotype network analyses and external programs.
Corresponds to the analysis_network and related methods in VB.NET.
"""
import csv
import os
import platform
import sys
import tempfile
import traceback
from dataclasses import dataclass
from typing import List, Optional, Callable, Sequence, Tuple

from model.taxon_data import TaxonData
from service.file_service import FileService
from service.format_conversion_service import (
    read_fasta,
    write_phylip,
)
from service.gen_network_config import generate_network_config
from service.haplotype_service import HaplotypeCalculation, identify_haplotypes
from service.mcan_adapter import (
    McanAdapterError,
    McanVcfInput,
    convert_graphml_to_tcsbu_gml,
    parse_mcan_options,
    prepare_mcan_input,
    prepare_mcan_vcf_input,
)
from service.process_service import (
    ManagedProcessRunner,
    ProcessCancelled,
    ProcessTimedOut,
)
from service.rmst_service import (
    RMSTCancelled,
    RMSTError,
    build_rmst_network,
    parse_rmst_options,
)
from service.validation_service import has_meaningful_continuous_trait


class AnalysisEngineError(RuntimeError):
    """Raised when an external analysis engine completes unsuccessfully."""


_NETWORK_TYPES = {
    "original_tcs", "modified_tcs", "mjn", "msn", "mcan", "rmst",
}


@dataclass
class AlignmentResult:
    """Result of a standalone alignment operation."""
    success: bool
    output_file: str = ""
    error_message: Optional[str] = None
    cancelled: bool = False
    displayable_fasta: bool = True


@dataclass
class AnalysisResult:
    """Result of an analysis operation."""
    prefix: str  # project name / file prefix
    success: bool
    output_path: str = ""
    error_message: Optional[str] = None
    # True as soon as _process_haplotypes() succeeds, even if later steps fail.
    # The haplotype tab should be shown whenever this is True.
    haplotype_ready: bool = False
    # True when at least one taxon has a meaningful (non-zero, non-empty) continuous trait.
    # Controls whether traitconf.csv is generated and loaded in the visualization.
    has_continuous_traits: bool = False
    # Path to the aligned FASTA produced during the analysis (empty if skipped).
    aligned_fasta: str = ""
    # Distinguishes an intentional user cancellation from an analysis failure.
    cancelled: bool = False

class AnalysisService:
    """Service for running haplotype network analyses."""

    def __init__(self, application_path: str):
        """
        Initialize analysis service.

        Args:
            application_path: Root application directory
        """
        # External tools run with the output directory as cwd, so every
        # application/resource path must be absolute before spawning them.
        self.root_path = os.path.abspath(application_path)
        self.lib_path = os.path.join(self.root_path, "lib")
        self.file_service = FileService()
        self.process_runner = ManagedProcessRunner()

        self._progress_callback: Optional[Callable[[int], None]] = None
        self._log_callback: Optional[Callable[[str], None]] = None
        self._cancel_callback: Optional[Callable[[], bool]] = None

    def set_progress_callback(self, callback: Callable[[int], None]) -> None:
        self._progress_callback = callback

    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        self._log_callback = callback

    def set_cancel_callback(self, callback: Optional[Callable[[], bool]]) -> None:
        """Set a callback checked while an external process is running."""
        self._cancel_callback = callback

    def _update_progress(self, value: int) -> None:
        if self._progress_callback:
            self._progress_callback(value)

    def _log(self, message: str) -> None:
        if self._log_callback:
            self._log_callback(message)

    def _check_cancelled(self) -> None:
        if self._cancel_callback is not None and self._cancel_callback():
            raise ProcessCancelled("Analysis cancelled")

    # ── Main analysis entry point ───────────────────────────────────────────────

    def run_network_analysis(self, network_type: str, taxons: List[TaxonData],
                             output_path: str, prefix: str,
                             extra_args: List[str] = None,
                             mcan_vcf_input: Optional[McanVcfInput] = None) -> AnalysisResult:
        """
        Run haplotype network analysis.

        Workflow:
          1. Write input FASTA
          2. Align with MAFFT (or MUSCLE fallback) if sequences have different lengths
          3. Process haplotypes: identify unique sequences, write PHYLIP + supporting files
          4. Call fastHaN/McAN or the internal RMST engine to build the network
          5. Adapt the engine output to GML and generate a tcsBU visualization

        All output files are named  <output_path>/<prefix>_*.

        Args:
            network_type: One of "original_tcs", "modified_tcs", "mjn", "msn",
                          "mcan", "rmst"
            taxons: List of selected taxons
            output_path: Directory for output files
            prefix: Project name used as output file name prefix
            extra_args: Allow-listed engine arguments (for example ['-t', '4']
                        or ['--method', 'exact'])

        Returns:
            AnalysisResult with prefix and success status
        """
        if extra_args is None:
            extra_args = []
        if network_type not in _NETWORK_TYPES:
            return AnalysisResult(
                prefix, False, output_path,
                f"Unsupported network algorithm: {network_type}",
            )
        FileService.ensure_directory(output_path)

        # Tracks whether _process_haplotypes() wrote its output files.
        # The haplotype tab should be shown whenever this is True, even if
        # downstream steps (fastHaN, visualization) fail.
        haplotype_ready = False

        produced_aligned_fasta = ""
        try:
            self._check_cancelled()
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

            # Track the aligned FASTA so the caller can display it in the Alignment tab.
            produced_aligned_fasta = aligned_fasta if os.path.isfile(aligned_fasta) else ""

            self._update_progress(30)
            self._check_cancelled()

            # ── Step 3: Ensure UTF-8 encoding ─────────────────────────────────
            FileService.ensure_utf8(aligned_fasta)

            # ── Step 4: Process haplotypes → PHYLIP + supporting files ─────────
            file_suffix = os.path.join(output_path, prefix)
            taxon_lookup = {
                str(t.name).strip(): (t.continuous_traits, t.discrete_traits)
                for t in taxons
            }
            self._log("Processing haplotypes...")
            hap_ok, has_continuous_traits = self._process_haplotypes(
                aligned_fasta, file_suffix, taxon_lookup)
            if not hap_ok:
                return AnalysisResult(prefix, False, output_path,
                                      "Haplotype processing failed",
                                      aligned_fasta=produced_aligned_fasta)

            # CSV / mapping files are now on disk — haplotype tab can be shown
            haplotype_ready = True
            self._update_progress(50)
            self._check_cancelled()

            # ── Step 5: Run selected network engine ───────────────────────────
            success = True
            failure_message: Optional[str] = None
            engine_name = {
                "mcan": "McAN",
                "rmst": "RMST",
            }.get(network_type, "fastHaN")
            self._log(f"Building {network_type} haplotype network with {engine_name}...")

            # Never let a failed rerun reuse a GML left by the same project
            # prefix. Every engine must create the result for this invocation.
            gml_file = f"{file_suffix}.gml"
            if os.path.isfile(gml_file):
                os.remove(gml_file)
            try:
                if network_type == "mcan":
                    exe_path = self._get_mcan_executable_path()
                    if not exe_path or not os.path.isfile(exe_path):
                        expected = exe_path or "McAN"
                        self._log(f"McAN executable not found: {expected}")
                        return AnalysisResult(
                            prefix, False, output_path,
                            f"McAN executable not found: {expected}",
                            haplotype_ready=haplotype_ready,
                            has_continuous_traits=has_continuous_traits,
                            aligned_fasta=produced_aligned_fasta,
                        )
                    self._run_mcan(
                        exe_path, aligned_fasta, file_suffix, extra_args, output_path,
                        mcan_vcf_input=mcan_vcf_input,
                        selected_names=[taxon.name for taxon in taxons],
                    )
                elif network_type == "rmst":
                    rmst_options = parse_rmst_options(extra_args)
                    rmst_result = build_rmst_network(
                        f"{file_suffix}_hap.fasta",
                        f"{file_suffix}_seq.meta.csv",
                        file_suffix,
                        rmst_options,
                        cancel_requested=self._cancel_callback,
                    )
                    self._log(
                        "RMST completed: "
                        f"{len(rmst_result.nodes)} nodes, {len(rmst_result.edges)} edges, "
                        f"{rmst_result.included_site_count}/"
                        f"{rmst_result.alignment_length} retained sites "
                        f"({rmst_result.method})"
                    )
                    for warning in rmst_result.warnings:
                        self._log(f"RMST warning: {warning}")
                else:
                    network_executable = self._get_network_executable()
                    exe_path = os.path.join(self._get_platform_lib_path(), network_executable)
                    seq_phy_file = f"{file_suffix}_seq.phy"
                    if not os.path.isfile(exe_path):
                        self._log(f"Network executable not found: {exe_path}")
                        return AnalysisResult(
                            prefix, False, output_path,
                            f"Executable not found: {network_executable}",
                            haplotype_ready=haplotype_ready,
                            has_continuous_traits=has_continuous_traits,
                            aligned_fasta=produced_aligned_fasta,
                        )
                    cmd = [exe_path, network_type, "-i", seq_phy_file]
                    cmd += extra_args + ["-o", file_suffix]
                    self._log(f"Running: {' '.join(cmd)}")
                    process = self.process_runner.run(
                        cmd,
                        cwd=output_path,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=600,
                        cancel_requested=self._cancel_callback,
                    )
                    self._log_process_output("fastHaN", process.stdout, process.stderr)
                    if process.returncode != 0:
                        raise AnalysisEngineError(
                            f"fastHaN exited with code {process.returncode}"
                        )
            except ProcessTimedOut:
                self._log(f"{engine_name} timed out after 600 seconds")
                success = False
                failure_message = f"{engine_name} timed out after 600 seconds"
            except (McanAdapterError, RMSTError, AnalysisEngineError,
                    FileNotFoundError, PermissionError, OSError) as e:
                self._log(f"{engine_name} network construction error: {e}")
                self._log(traceback.format_exc())
                success = False
                failure_message = f"{engine_name} network construction error: {e}"

            self._update_progress(70)
            self._check_cancelled()

            # ── Step 6: Check GML output ───────────────────────────────────────
            if not os.path.isfile(gml_file):
                self._log(f"GML network file was not created by {engine_name}")
                success = False
                if failure_message is None:
                    failure_message = f"GML network file was not created by {engine_name}"

            if success:
                # ── Step 7: Generate visualization ────────────────────────────
                self._check_cancelled()
                self._log("Generating visualization...")
                success = self._generate_visualization(
                    prefix, output_path, has_continuous_traits)
                if not success:
                    failure_message = "Network visualization generation failed"

            self._update_progress(100)

        except (ProcessCancelled, RMSTCancelled):
            self._log("Analysis cancelled by user")
            return AnalysisResult(prefix, False, output_path, "Analysis cancelled",
                                  haplotype_ready=haplotype_ready,
                                  aligned_fasta=produced_aligned_fasta,
                                  cancelled=True)
        except Exception as e:
            self._log(f"Analysis error: {str(e)}")
            self._log(traceback.format_exc())
            return AnalysisResult(prefix, False, output_path, str(e),
                                  haplotype_ready=haplotype_ready)

        return AnalysisResult(prefix, success, output_path, failure_message,
                              haplotype_ready=haplotype_ready,
                              has_continuous_traits=has_continuous_traits,
                              aligned_fasta=produced_aligned_fasta)

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
        input_fasta = os.path.join(output_path, f"{prefix}.fasta")
        if config.tool == "mafft":
            output_extension = ".aln" if config.mafft_clustalout else ".fasta"
            displayable_fasta = not config.mafft_clustalout
        else:
            output_extension = {
                "fasta": ".fasta",
                "html": ".html",
                "msf": ".msf",
                "clw": ".aln",
                "clwstrict": ".aln",
            }.get(config.muscle_output_format, ".fasta")
            displayable_fasta = config.muscle_output_format == "fasta"
        output_file = os.path.join(output_path, f"{prefix}_aln{output_extension}")

        try:
            self._check_cancelled()
            self.file_service.write_analysis_fasta(input_fasta, taxons)
            self._log(f"Input FASTA written: {input_fasta}")

            if config.tool == "muscle":
                extra_args = config.to_muscle_extra_args()
                self._log(f"Running MUSCLE with args: {extra_args}")
                ok = self._run_muscle_alignment(input_fasta, output_file,
                                                extra_args=extra_args)
                tool_name = "MUSCLE"
            else:
                method_args = config.to_mafft_method_args()
                add_inputorder = not config.mafft_reorder
                self._log(f"Running MAFFT with args: {method_args}")
                ok = self._run_mafft_alignment(input_fasta, output_file,
                                               method_args=method_args,
                                               add_inputorder=add_inputorder)
                tool_name = "MAFFT"

            if ok:
                self._log(f"{tool_name} alignment succeeded → {output_file}")
                return AlignmentResult(
                    success=True,
                    output_file=output_file,
                    displayable_fasta=displayable_fasta,
                )
            else:
                return AlignmentResult(
                    success=False,
                    error_message=f"{tool_name} alignment failed or binary not found")

        except ProcessCancelled:
            self._log("Alignment cancelled by user")
            return AlignmentResult(
                success=False,
                error_message="Alignment cancelled",
                cancelled=True,
            )
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
            mafft_dir = os.path.join(self._get_platform_lib_path(), "mafft-win")
            candidates.append((os.path.join(mafft_dir, "mafft.bat"), mafft_dir))
        elif self._is_mac():
            mafft_dir = os.path.join(self._get_platform_lib_path(), "mafft-mac")
            candidates.append((os.path.join(mafft_dir, "mafft.bat"), mafft_dir))
        else:
            linux_lib_mafft = os.path.join(self.lib_path, "mafft")
            if os.path.isfile(linux_lib_mafft):
                candidates.append((linux_lib_mafft, None))

        candidates.append(("mafft", None))  # system fallback

        for mafft_cmd, work_dir in candidates:
            try:
                order_flag = ["--inputorder"] if add_inputorder else []
                cmd = [mafft_cmd] + order_flag + method_args + [input_file]
                with open(output_file, 'w', encoding='utf-8') as out_f:
                    process = self.process_runner.run(
                        cmd,
                        cwd=work_dir,
                        stdout=out_f,
                        timeout=600,
                        cancel_requested=self._cancel_callback,
                    )

                stderr_text = process.stderr
                if isinstance(stderr_text, bytes):
                    stderr_text = stderr_text.decode('utf-8', errors='replace')
                if stderr_text and stderr_text.strip():
                    self._log(f"MAFFT: {stderr_text.strip()}")

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
            except ProcessTimedOut:
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

        platform_lib = self._get_platform_lib_path()
        if self._is_windows():
            candidates = [
                os.path.join(platform_lib, "muscle3.exe"),
                os.path.join(platform_lib, "muscle.exe"),
            ]
        else:
            candidates = [
                os.path.join(platform_lib, "muscle3"),
                os.path.join(platform_lib, "muscle"),
            ]

        for muscle_cmd in candidates:
            for base_args in (
                    [muscle_cmd, "-align", input_file, "-output", output_file],  # muscle5
                    [muscle_cmd, "-in", input_file, "-out", output_file],  # muscle3
            ):
                try:
                    cmd = base_args + extra_args
                    process = self.process_runner.run(
                        cmd,
                        timeout=600,
                        cancel_requested=self._cancel_callback,
                    )

                    for stream_bytes, label in ((process.stdout, "MUSCLE"), (process.stderr, "MUSCLE")):
                        if stream_bytes:
                            text = stream_bytes.decode('utf-8', errors='replace').strip()
                            if text:
                                self._log(f"{label}: {text}")

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
                except ProcessTimedOut:
                    self._log(f"MUSCLE timed out: {muscle_cmd}")
                    if os.path.isfile(output_file):
                        try:
                            os.remove(output_file)
                        except OSError:
                            pass

        return False

    # ── Haplotype processing ────────────────────────────────────────────────────

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

        try:
            # ── Read aligned FASTA through the shared strict parser ───────────
            records = read_fasta(aligned_fasta)
            calculation = identify_haplotypes(records, self._check_cancelled)
            assignment_map = calculation.assignment_map()

            # Only traits belonging to samples that survived/read from the
            # alignment affect this result.  This prevents a stale lookup entry
            # from creating a trait configuration file for unrelated samples.
            traits_by_sample = {}
            for record in calculation.records:
                continuous, discrete = taxon_lookup.get(record.name, ("0", ""))
                traits_by_sample[record.name] = (
                    "0" if continuous is None else str(continuous),
                    "" if discrete is None else str(discrete),
                )
            has_continuous = any(
                has_meaningful_continuous_trait(continuous)
                for continuous, _ in traits_by_sample.values()
            )

            self._log(
                f"Identified {len(calculation.haplotypes)} unique haplotypes "
                f"from {len(calculation.records)} sequences")

            # Generate every result in a temporary directory first.  A parse,
            # write, or cancellation failure therefore cannot leave a mixture
            # of old and partially-written haplotype files behind.
            output_directory = os.path.dirname(os.path.abspath(output_prefix))
            os.makedirs(output_directory, exist_ok=True)
            output_stem = os.path.basename(output_prefix)
            with tempfile.TemporaryDirectory(
                prefix=f".{output_stem}_hap_", dir=output_directory,
            ) as temporary_directory:
                temporary_prefix = os.path.join(temporary_directory, output_stem)
                generated_suffixes = self._write_haplotype_outputs(
                    calculation,
                    temporary_prefix,
                    traits_by_sample,
                    assignment_map,
                    has_continuous,
                )
                self._check_cancelled()
                for suffix in generated_suffixes:
                    os.replace(
                        temporary_prefix + suffix,
                        output_prefix + suffix,
                    )

            # A successful rerun without continuous traits must not reuse a
            # trait configuration left by an earlier run with the same prefix.
            traitconf_path = f"{output_prefix}_traitconf.csv"
            if not has_continuous and os.path.isfile(traitconf_path):
                os.remove(traitconf_path)

            return True, has_continuous

        except ProcessCancelled:
            raise
        except Exception as e:
            self._log(f"Haplotype processing error: {str(e)}")
            self._log(traceback.format_exc())
            return False, False

    def _write_haplotype_outputs(
        self,
        calculation: HaplotypeCalculation,
        output_prefix: str,
        traits_by_sample: dict,
        assignment_map: dict,
        has_continuous: bool,
    ) -> Tuple[str, ...]:
        """Write one internally consistent set of haplotype result files."""
        generated_suffixes = [
            "_seq.fasta",
            "_seq.phy",
            "_hap.fasta",
            "_seq.meta.csv",
            "_hap_trait.csv",
            "_seq_trait.csv",
        ]

        with open(f"{output_prefix}_seq.fasta", "w", encoding="utf-8", newline="\n") as handle:
            for record in calculation.records:
                self._check_cancelled()
                handle.write(f">{record.name}\n{record.sequence}\n")

        write_phylip(f"{output_prefix}_seq.phy", calculation.records)

        with open(f"{output_prefix}_hap.fasta", "w", encoding="utf-8", newline="\n") as handle:
            for haplotype in calculation.haplotypes:
                self._check_cancelled()
                handle.write(f">{haplotype.name}\n{haplotype.sequence}\n")

        with open(
            f"{output_prefix}_seq.meta.csv", "w", encoding="utf-8", newline="",
        ) as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "sequence_name", "haplotype", "continuous_traits", "discrete_traits",
            ])
            for record in calculation.records:
                self._check_cancelled()
                continuous, discrete = traits_by_sample[record.name]
                writer.writerow([
                    record.name, assignment_map[record.name], continuous, discrete,
                ])

        if has_continuous:
            generated_suffixes.append("_traitconf.csv")
            with open(
                f"{output_prefix}_traitconf.csv", "w", encoding="utf-8", newline="\n",
            ) as handle:
                for record in calculation.records:
                    self._check_cancelled()
                    continuous, _ = traits_by_sample[record.name]
                    # tcsBU splits this legacy format on semicolons before it
                    # normalizes identifiers, so protect valid sample names
                    # that themselves contain the delimiter.
                    trait_name = record.name.replace(";", "_")
                    handle.write(f"{trait_name};{continuous}\n")

        with open(
            f"{output_prefix}_hap_trait.csv", "w", encoding="utf-8", newline="",
        ) as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "haplotype", "total_quantity", "continuous_traits",
                "discrete_traits", "samples",
            ])
            for haplotype in calculation.haplotypes:
                self._check_cancelled()
                member_traits = [traits_by_sample[name] for name in haplotype.samples]
                continuous_values = list(dict.fromkeys(
                    str(continuous) for continuous, _ in member_traits
                ))
                discrete_values = sorted({
                    str(discrete) for _, discrete in member_traits if str(discrete)
                })
                writer.writerow([
                    haplotype.name,
                    haplotype.sample_count,
                    ";".join(continuous_values),
                    ";".join(discrete_values),
                    ";".join(haplotype.samples),
                ])

        with open(
            f"{output_prefix}_seq_trait.csv", "w", encoding="utf-8", newline="",
        ) as handle:
            writer = csv.writer(handle)
            writer.writerow(["name", "quantity", "continuous_traits", "discrete_traits"])
            for record in calculation.records:
                self._check_cancelled()
                continuous, discrete = traits_by_sample[record.name]
                writer.writerow([record.name, 1, continuous, discrete])

        return tuple(generated_suffixes)

    def run_haplotype_calculation(self, taxons: List[TaxonData], output_path: str,
                                  prefix: str, config) -> AnalysisResult:
        """
        Run MSA then calculate haplotypes without building a network.

        Workflow:
          1. Write input FASTA
          2. Align with the tool chosen in config (MAFFT or MUSCLE)
          3. Process haplotypes: identify unique sequences, write supporting files

        Args:
            taxons:      Selected sequences
            output_path: Directory for output files
            prefix:      Project name used as file name prefix
            config:      SequenceAlignmentConfig with tool + parameter settings

        Returns:
            AnalysisResult with haplotype_ready=True on success
        """
        FileService.ensure_directory(output_path)
        haplotype_ready = False
        produced_aligned_fasta = ""

        try:
            self._check_cancelled()
            # ── Step 1: Write input FASTA ──────────────────────────────────────
            input_fasta = os.path.join(output_path, f"{prefix}.fasta")
            self.file_service.write_analysis_fasta(input_fasta, taxons)
            self._update_progress(10)

            # ── Step 2: Alignment ──────────────────────────────────────────────
            aligned_fasta = os.path.join(output_path, f"{prefix}_aln.fasta")
            # This workflow explicitly asks the user for an aligner/config, so
            # always align even when raw sequences happen to have equal length.
            if config.tool == "muscle":
                extra_args = config.to_muscle_extra_args(force_fasta=True)
                self._log("Running MUSCLE alignment...")
                aligned = self._run_muscle_alignment(input_fasta, aligned_fasta,
                                                     extra_args=extra_args)
                if not aligned:
                    self._log("MUSCLE failed, trying MAFFT...")
                    aligned = self._run_mafft_alignment(input_fasta, aligned_fasta)
            else:
                method_args = config.to_mafft_method_args(force_fasta=True)
                add_inputorder = not config.mafft_reorder
                self._log("Running MAFFT alignment...")
                aligned = self._run_mafft_alignment(input_fasta, aligned_fasta,
                                                    method_args=method_args,
                                                    add_inputorder=add_inputorder)
                if not aligned:
                    self._log("MAFFT failed, trying MUSCLE...")
                    aligned = self._run_muscle_alignment(input_fasta, aligned_fasta)

            if not aligned:
                return AnalysisResult(prefix, False, output_path,
                                      "Sequence alignment failed")

            produced_aligned_fasta = aligned_fasta if os.path.isfile(aligned_fasta) else ""
            self._update_progress(50)
            self._check_cancelled()

            # ── Step 3: Ensure UTF-8 ───────────────────────────────────────────
            FileService.ensure_utf8(aligned_fasta)

            # ── Step 4: Process haplotypes ─────────────────────────────────────
            file_suffix = os.path.join(output_path, prefix)
            taxon_lookup = {
                str(t.name).strip(): (t.continuous_traits, t.discrete_traits)
                for t in taxons
            }
            self._log("Processing haplotypes...")
            hap_ok, has_continuous_traits = self._process_haplotypes(
                aligned_fasta, file_suffix, taxon_lookup)

            if not hap_ok:
                return AnalysisResult(prefix, False, output_path,
                                      "Haplotype processing failed",
                                      aligned_fasta=produced_aligned_fasta)

            haplotype_ready = True
            self._update_progress(100)
            self._log("Haplotype calculation finished.")

            return AnalysisResult(prefix, True, output_path,
                                  haplotype_ready=haplotype_ready,
                                  has_continuous_traits=has_continuous_traits,
                                  aligned_fasta=produced_aligned_fasta)

        except ProcessCancelled:
            self._log("Haplotype calculation cancelled by user")
            return AnalysisResult(
                prefix, False, output_path, "Haplotype calculation cancelled",
                haplotype_ready=haplotype_ready,
                aligned_fasta=produced_aligned_fasta,
                cancelled=True,
            )
        except Exception as e:
            self._log(f"Haplotype calculation error: {str(e)}")
            self._log(traceback.format_exc())
            return AnalysisResult(prefix, False, output_path, str(e),
                                  haplotype_ready=haplotype_ready)

    # ── McAN adapter ────────────────────────────────────────────────────────────

    def _run_mcan(self, executable: str, aligned_fasta: str, output_prefix: str,
                  extra_args: List[str], cwd: str,
                  mcan_vcf_input: Optional[McanVcfInput] = None,
                  selected_names: Sequence[str] = ()) -> None:
        """Prepare, execute and adapt one isolated McAN network run."""
        options = parse_mcan_options(extra_args)
        if mcan_vcf_input is not None:
            if options.reference_name or options.exclude_ambiguous_sites:
                raise McanAdapterError(
                    "Reference selection and ambiguous-site filtering apply only "
                    "to aligned FASTA McAN input, not native VCF input"
                )
            prepared = prepare_mcan_vcf_input(
                mcan_vcf_input,
                output_prefix,
                selected_names,
                check_cancelled=self._check_cancelled,
            )
            self._log("Using original VCF and metadata as native McAN input")
        else:
            prepared = prepare_mcan_input(
                aligned_fasta,
                output_prefix,
                options,
                check_cancelled=self._check_cancelled,
            )
        self._log(
            "McAN input prepared: "
            f"{len(prepared.alias_to_name)} samples, "
            f"{prepared.included_site_count}/{prepared.sequence_length} sites"
        )

        graphml_file = os.path.join(prepared.output_directory, "haplotype_loci.graphml")
        json_file = os.path.join(prepared.output_directory, "haplotype_loci.json")
        time_file = os.path.join(prepared.output_directory, "time")
        for stale_output in (graphml_file, json_file, time_file):
            if os.path.isfile(stale_output):
                os.remove(stale_output)

        input_args = (
            ["--vcf", prepared.vcf_file]
            if prepared.vcf_file
            else ["--mutation", prepared.mutation_file]
        )
        cmd = [executable] + input_args + [
            "--meta", prepared.metadata_file,
            "--sitemask", prepared.site_mask_file,
            "--outDir", prepared.output_directory,
            "--oGraphML",
            "--oJSON",
            "--nthread", str(options.threads),
        ]
        self._log(f"Running: {' '.join(cmd)}")
        process = self.process_runner.run(
            cmd,
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            cancel_requested=self._cancel_callback,
        )
        self._log_process_output("McAN", process.stdout, process.stderr)
        if process.returncode != 0:
            raise AnalysisEngineError(f"McAN exited with code {process.returncode}")
        if not os.path.isfile(graphml_file) or os.path.getsize(graphml_file) == 0:
            raise McanAdapterError("McAN did not create haplotype_loci.graphml")

        gml_file = output_prefix + ".gml"
        convert_graphml_to_tcsbu_gml(
            graphml_file, gml_file, prepared.alias_to_name
        )
        self._log(f"McAN GraphML converted for tcsBU: {gml_file}")

    def _log_process_output(self, program: str, stdout, stderr) -> None:
        if stdout:
            text = str(stdout).strip()
            if program == "McAN":
                # McAN 1.2 prints unsigned-clock underflow as enormous negative
                # timing values on current macOS.  They are not run failures
                # and obscure the useful progress messages in NetST's log.
                text = "\n".join(
                    line for line in text.splitlines()
                    if not (line.startswith("-") and " s for " in line)
                ).strip()
            if text:
                self._log(f"{program} stdout: {text}")
        if stderr:
            text = str(stderr).strip()
            if text:
                self._log(f"{program} stderr: {text}")

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
        """Generate network visualization HTML that uses static/tcsbu/ resources.

        The generated HTML embeds the data script (js_file) before tcsBU.js so
        that the auto-load block in tcsBU.js can call loadGraph/loadGroups/
        loadHaplotypes/loadTraits immediately on page ready.

        Uses pathlib.Path.as_uri() for file:// URL construction so this method
        is safe to call from a worker thread (no Qt objects needed).
        """
        from pathlib import Path

        tcsbu_dir = os.path.join(self.root_path, "static", "tcsbu")

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

        platform_lib = self._get_platform_lib_path()
        for name in candidates:
            if os.path.isfile(os.path.join(platform_lib, name)):
                return name

        return candidates[0]

    def _get_mcan_executable_path(self) -> str:
        """Return a bundled McAN executable or an explicit environment override."""
        override = os.environ.get("NETST_MCAN_EXECUTABLE", "").strip()
        if override:
            return os.path.abspath(os.path.expanduser(override))

        platform_lib = self._get_platform_lib_path()
        if self._is_windows():
            candidates = ["McAN.exe", "mcan.exe", "McAN", "mcan"]
        else:
            candidates = ["McAN", "mcan"]

        for name in candidates:
            path = os.path.join(platform_lib, name)
            if os.path.isfile(path):
                return path
        return os.path.join(platform_lib, candidates[0])

    def _get_platform_lib_path(self) -> str:
        """Get the platform-specific lib subdirectory path.

        Returns:
            lib/win       on Windows
            lib/mac_arm64 on Apple Silicon macOS
            lib/mac_intel (or lib/) on Intel macOS
            lib/          on Linux (fallback)
        """
        if self._is_windows():
            return os.path.join(self.lib_path, "win")
        elif self._is_mac():
            arch = platform.machine().lower()
            if 'arm' in arch or 'aarch64' in arch:
                return os.path.join(self.lib_path, "mac_arm64")
            intel_path = os.path.join(self.lib_path, "mac_intel")
            return intel_path if os.path.isdir(intel_path) else self.lib_path
        else:
            return self.lib_path

    @staticmethod
    def _is_windows() -> bool:
        return sys.platform.startswith('win')

    @staticmethod
    def _is_mac() -> bool:
        return sys.platform == 'darwin'
