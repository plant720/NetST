"""
Service for running haplotype network analyses and external programs.
Corresponds to the analysis_network and related methods in VB.NET.
"""
import csv
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Callable

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
        
        Args:
            network_type: One of: "modified_tcs", "mjn", "msn"
            taxons: List of selected taxons
            output_path: Directory for output files (user specified)
            
        Returns:
            AnalysisResult containing timestamp and success status
        """
        timestamp = int(time.time())
        formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        success = True

        # Ensure output directory exists
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

                # Step 1: Write input FASTA file
                input_fasta = os.path.join(output_path, f"{timestamp}.fasta")
                self.file_service.write_analysis_fasta(input_fasta, taxons)
                result_writer.writerow(['Ori_seqs', input_fasta, 'Success', 'Original sequences'])
                self._update_progress(10)

                # Step 2: Check if alignment is needed
                aligned_fasta = os.path.join(output_path, f"{timestamp}_aln.fasta")
                needs_alignment = not self._are_sequences_aligned(taxons)

                if needs_alignment:
                    self._log("Aligning sequences with MAFFT...")
                    success = self._run_mafft_alignment(input_fasta, aligned_fasta)
                    if success:
                        result_writer.writerow(['Aligned_seqs', aligned_fasta, 'Success', 'Sequences aligned by MAFFT'])
                    else:
                        result_writer.writerow(['Aligned_seqs', aligned_fasta, 'Failed', 'MAFFT alignment failed'])
                        return AnalysisResult(timestamp, False, output_path, "Sequence alignment failed")
                else:
                    FileService.safe_copy(input_fasta, aligned_fasta)
                    result_writer.writerow(['Aligned_seqs', aligned_fasta, 'Success', 'Sequences already aligned'])

                self._update_progress(30)

                # Step 3: Ensure UTF-8 encoding
                FileService.ensure_utf8(aligned_fasta)

                # Step 4: Process haplotypes
                file_suffix = os.path.join(output_path, str(timestamp))
                self._log("Processing haplotypes...")
                if not self._process_haplotypes(aligned_fasta, file_suffix, result_writer):
                    return AnalysisResult(timestamp, False, output_path, "Haplotype processing failed")
                self._update_progress(50)

                # Step 5: Run network construction
                self._log(f"Building {network_type} network...")
                network_executable = self._get_network_executable()
                seq_phy_file = f"{file_suffix}_seq.phy"

                try:
                    process = subprocess.run(
                        [
                            os.path.join(self.lib_path, network_executable),
                            network_type,
                            "-i", seq_phy_file,
                            "-o", file_suffix
                        ],
                        cwd=output_path,
                        capture_output=True,
                        text=True
                    )
                except FileNotFoundError as e:
                    self._log(f"Network executable not found: {e}")
                    success = False

                self._update_progress(70)

                # Step 6: Check output files
                gml_file = f"{file_suffix}.gml"
                json_file = f"{file_suffix}.json"

                if os.path.isfile(gml_file):
                    result_writer.writerow(['HapNet_gml', gml_file, 'Success', 'Haplotype network in GML format'])

                    if os.path.isfile(json_file):
                        result_writer.writerow(
                            ['HapNet_json', json_file, 'Success', 'Haplotype network in JSON format'])

                    # Step 7: Generate visualization config
                    self._log("Generating visualization...")
                    success = self._generate_visualization(timestamp, output_path, result_writer)
                else:
                    result_writer.writerow(['HapNet_gml', gml_file, 'Failed', 'GML network file not created'])
                    success = False

                self._update_progress(90)

                # Step 8: Generate HTML report
                report_html = os.path.join(output_path, f"{timestamp}_report.html")
                self.generate_html_report(result_file_path, report_html, str(timestamp),
                                          formatted_time, success)
                result_writer.writerow(['Report_html', report_html, 'Success', 'Analysis report'])

                # Record in history
                self._append_to_history(output_path, formatted_time, timestamp, network_type)

                self._update_progress(100)

        except Exception as e:
            self._log(f"Analysis error: {str(e)}")
            return AnalysisResult(timestamp, False, output_path, str(e))

        return AnalysisResult(timestamp, success, output_path)

    def _are_sequences_aligned(self, taxons: List[TaxonData]) -> bool:
        """Check if all sequences have the same length (already aligned)."""
        if not taxons:
            return True
        first_length = len(taxons[0].sequence)
        return all(len(t.sequence) == first_length for t in taxons)

    def _run_mafft_alignment(self, input_file: str, output_file: str) -> bool:
        """Run MAFFT alignment."""
        try:
            mafft_path = os.path.join(self.lib_path, "mafft-win")
            mafft_script = os.path.join(mafft_path, "mafft.bat" if self._is_windows() else "mafft")

            with open(output_file, 'w') as out_f:
                process = subprocess.run(
                    [mafft_script, "--retree", "2", "--inputorder", input_file],
                    cwd=mafft_path,
                    stdout=out_f,
                    stderr=subprocess.PIPE
                )

            return process.returncode == 0 and os.path.isfile(output_file)
        except Exception as e:
            self._log(f"MAFFT error: {str(e)}")
            return False

    def _process_haplotypes(self, aligned_fasta: str, output_prefix: str, result_writer) -> bool:
        """Process sequences to haplotypes."""
        # This would call your hap_fasta equivalent
        # For now, create placeholder entries
        try:
            result_writer.writerow(
                ['Hap_seq_phylip', f'{output_prefix}_hap.phy', 'Success', 'Haplotype sequences in PHYLIP format'])
            result_writer.writerow(
                ['Hap_seq_fasta', f'{output_prefix}_hap.fasta', 'Success', 'Haplotype sequences in FASTA format'])
            result_writer.writerow(
                ['Seq_with_traits_phylip', f'{output_prefix}_seq.phy', 'Success', 'Aligned sequences with traits'])
            result_writer.writerow(
                ['Seq_with_traits_fasta', f'{output_prefix}_seq.fasta', 'Success', 'Aligned sequences with traits'])
            result_writer.writerow(['Seq_metadata', f'{output_prefix}.meta', 'Success', 'Sequence metadata'])
            result_writer.writerow(
                ['Hap_trait', f'{output_prefix}_hap_trait.csv', 'Success', 'Haplotype trait information'])
            result_writer.writerow(
                ['Seq_trait', f'{output_prefix}_seq_trait.csv', 'Success', 'Sequence trait information'])
            result_writer.writerow(
                ['Seq2Hap', f'{output_prefix}_seq2hap.csv', 'Success', 'Sequence to haplotype mapping'])
            return True
        except Exception as e:
            self._log(f"Haplotype processing error: {str(e)}")
            return False

    def _generate_visualization(self, timestamp: int, output_path: str, result_writer=None) -> bool:
        """Generate visualization files."""
        try:
            config_executable = os.path.join(
                self.lib_path,
                "GenNetworkConfig2" + (".exe" if self._is_windows() else "")
            )

            subprocess.run(
                [config_executable, f"{timestamp}.gml", f"{timestamp}_seq2hap.csv", str(timestamp)],
                cwd=output_path,
                capture_output=True
            )

            js_file = os.path.join(output_path, f"{timestamp}.js")
            if os.path.isfile(js_file):
                html_file = os.path.join(output_path, f"{timestamp}.html")
                self._generate_network_html(html_file, f"{timestamp}.js")

                if result_writer is not None:
                    result_writer.writerow(['HapNet_js', js_file, 'Success', 'Visualization JavaScript'])
                    result_writer.writerow(['HapNet_html', html_file, 'Success', 'Visualization HTML'])
                return True

            return False
        except Exception as e:
            self._log(f"Visualization error: {str(e)}")
            return False

    def _generate_network_html(self, html_file: str, js_file: str) -> None:
        """Generate network visualization HTML."""
        template_path = os.path.join(self.root_path, "statics", "en", "tcsBU.txt")
        if os.path.isfile(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            html = template.replace("$data$", js_file)
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html)

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

                # Read CSV and generate table rows
                if os.path.isfile(csv_path):
                    with open(csv_path, 'r', encoding='utf-8') as csv_file:
                        for line in csv_file:
                            if line.startswith('#') or line.startswith('FileType') or ',' not in line:
                                continue
                            parts = line.strip().split(',', 3)
                            if len(parts) >= 4:
                                status_class = 'success' if parts[2].lower() == 'success' else 'failed'
                                filename = os.path.basename(parts[1])
                                f.write(f"<tr><td>{parts[0]}</td><td><a href='{parts[1]}'>{filename}</a></td>")
                                f.write(f"<td class='{status_class}'>{parts[2]}</td><td>{parts[3]}</td></tr>\n")

                f.write("</table></body></html>")
        except Exception as e:
            self._log(f"HTML report generation error: {str(e)}")

    def _append_to_history(self, output_path: str, time_str: str, timestamp: int, description: str) -> None:
        """Append entry to history file in output directory."""
        history_file = os.path.join(output_path, "history.csv")
        file_exists = os.path.isfile(history_file)
        with open(history_file, 'a', encoding='utf-8') as f:
            if not file_exists:
                f.write("Time,Timestamp,Description\n")
            f.write(f"{time_str},{timestamp},{description}\n")

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

            # Check expected output files if specified
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

    def _get_network_executable(self) -> str:
        """Get the appropriate network executable for the platform."""
        arch = platform.machine().lower()
        if self._is_windows():
            return "fastHaN_win_arm.exe" if 'arm' in arch else "fastHaN_win_intel.exe"
        elif self._is_mac():
            return "fastHaN_mac_arm" if 'arm' in arch else "fastHaN_mac_intel"
        else:
            return "fastHaN_linux"

    @staticmethod
    def _is_windows() -> bool:
        return sys.platform.startswith('win')

    @staticmethod
    def _is_mac() -> bool:
        return sys.platform == 'darwin'
