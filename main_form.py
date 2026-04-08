"""
Main Window Business Logic Module

Implements the main window business logic, inheriting from MainWindowUI base class.
"""

import csv
import os
import sys
from typing import Optional, Dict, Callable

from PyQt6.QtCore import QUrl, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QMessageBox, QInputDialog
)

from model.taxon_table_model import TaxonTableModel
from service.analysis_service import AnalysisService, AnalysisResult, AlignmentResult
from service.file_service import FileService
from ui import MainWindowUI
from ui.csv_traits_import_dialog import CsvTraitsImportDialog
from ui.haplotype_network_dialog import HaplotypeNetworkDialog
from ui.language_manager import lang_manager
from ui.sequence_alignment_dialog import SequenceAlignmentDialog, SequenceAlignmentConfig
from ui.standardization_dialog import StandardizationDialog

# Fix path issues - ensure current directory is in Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# macOS WebEngine GPU crash fix
# Disable GPU hardware acceleration for WebEngine to fix crashes on Apple Silicon Macs
# running x86_64 Python via Rosetta
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS',
                      '--no-sandbox '
                      '--disable-gpu '
                      '--disable-software-rasterizer '
                      '--disable-gpu-compositing '
                      '--disable-gpu-rasterization '
                      '--disable-gpu-sandbox '
                      '--in-process-gpu'
                      )


class AnalysisWorker(QThread):
    """Worker thread for running analysis tasks in background."""

    finished = pyqtSignal(object)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)

    def __init__(self, analysis_service: AnalysisService, network_type: str,
                 taxons: list, output_path: str, prefix: str,
                 extra_args: list = None):
        super().__init__()
        self.analysis_service = analysis_service
        self.network_type = network_type
        self.taxons = taxons
        self.output_path = output_path
        self.prefix = prefix
        self.extra_args = extra_args or []

    def run(self):
        """Execute analysis task in child thread."""
        self.analysis_service.set_progress_callback(lambda v: self.progress.emit(v))
        self.analysis_service.set_log_callback(lambda m: self.log.emit(m))

        result = self.analysis_service.run_network_analysis(
            self.network_type, self.taxons, self.output_path, self.prefix,
            extra_args=self.extra_args
        )
        self.finished.emit(result)


class AlignmentWorker(QThread):
    """Worker thread for running standalone sequence alignment in the background."""

    finished = pyqtSignal(object)  # AlignmentResult
    log = pyqtSignal(str)

    def __init__(self, analysis_service: AnalysisService, taxons: list,
                 output_path: str, prefix: str, config: SequenceAlignmentConfig):
        super().__init__()
        self.analysis_service = analysis_service
        self.taxons = taxons
        self.output_path = output_path
        self.prefix = prefix
        self.config = config

    def run(self):
        self.analysis_service.set_log_callback(lambda m: self.log.emit(m))
        result = self.analysis_service.run_alignment(
            self.taxons, self.output_path, self.prefix, self.config)
        self.finished.emit(result)


class HaplotypeWorker(QThread):
    """Worker thread for MSA + haplotype calculation (no network construction)."""

    finished = pyqtSignal(object)  # AnalysisResult
    progress = pyqtSignal(int)
    log = pyqtSignal(str)

    def __init__(self, analysis_service: AnalysisService, taxons: list,
                 output_path: str, prefix: str, config: SequenceAlignmentConfig):
        super().__init__()
        self.analysis_service = analysis_service
        self.taxons = taxons
        self.output_path = output_path
        self.prefix = prefix
        self.config = config

    def run(self):
        self.analysis_service.set_progress_callback(lambda v: self.progress.emit(v))
        self.analysis_service.set_log_callback(lambda m: self.log.emit(m))
        result = self.analysis_service.run_haplotype_calculation(
            self.taxons, self.output_path, self.prefix, self.config)
        self.finished.emit(result)


class MainForm(MainWindowUI):
    """
    Main Window Business Logic Class

    Inherits MainWindowUI and implements all business logic functions including:
    - File operations
    - Data management
    - Analysis functions
    - Menu callbacks
    """

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        # State variables
        self.data_loaded = False
        self.current_file = ""
        self.language = "en"

        # Service instances
        self.file_service = FileService()
        self.analysis_service = AnalysisService(self.current_directory)

        # Data model
        self.table_model = TaxonTableModel()

        # Worker thread references
        self.analysis_worker: Optional[AnalysisWorker] = None
        self.alignment_worker: Optional[AlignmentWorker] = None
        self.haplotype_worker: Optional[HaplotypeWorker] = None

        # Pending JavaScript to inject after the next successful page load in web_view_main.
        # Set by _on_analysis_finished; consumed by _on_web_view_load_finished.
        self._pending_js: Optional[str] = None

        # Initialization
        self._init_components()
        self._setup_menus()
        self._setup_connections()

        # Delayed loading of initial pages
        QTimer.singleShot(100, self._load_initial_pages)

    def _init_components(self):
        """Initialize components."""
        self.data_tab.set_model(self.table_model)
        self.data_tab.set_select_all_callback(self._select_all)
        self.data_tab.set_deselect_all_callback(self._deselect_all)

    def _setup_menus(self):
        """Setup menu bar."""
        callbacks = self._get_callbacks()
        self.setup_menus(callbacks)

    def _get_callbacks(self) -> Dict[str, Callable]:
        """Get all menu callback functions."""
        return {
            # File Menu
            'load_sequence': self._load_sequence,
            'add_sequence': self._add_sequence,
            'load_csv_traits': self._load_csv_traits,
            'export_fasta': self._export_sequence,
            'exit': self.close,

            # Analysis Menu
            'build_haplotype_network': self._build_haplotype_network,
            'calculate_haplotype': self._calculate_haplotype,

            # Multiple Sequence Alignment (unified MAFFT + MUSCLE dialog)
            'run_msa': self._run_sequence_alignment,

            'language_chinese': lambda: self._set_language("cn"),
            'language_english': lambda: self._set_language("en"),

            # Help Menu
            'about': self._show_about,
            'help_docs': self._show_help,
            'help_tcsbu': self._show_tcsbu_help,
            'help_netst': self._show_netst_help,
        }

    def _setup_connections(self):
        """Setup signal connections."""
        self.table_model.dataChanged.connect(self._update_selected_count)
        self.data_tab.selection_changed.connect(self._update_selected_count)
        # Connect WebEngine loadFinished so we can inject data JS after each analysis.
        if hasattr(self.web_view_main, 'loadFinished'):
            self.web_view_main.loadFinished.connect(self._on_web_view_load_finished)

    def _load_initial_pages(self):
        """Load initial HTML pages."""
        # Load the tcsBU interface as the default network tab view.
        index_html = os.path.join(self.current_directory, "statics", "tcsbu", "index.html")
        if os.path.isfile(index_html):
            self.load_main_page(index_html)

        self.output_panel.append_info("Application started")
        self.output_panel.append_info(f"Working directory: {self.current_directory}")

    # ==================== File Operations ====================

    def _load_sequence(self):
        """Load sequence data from FASTA file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Sequence File",
            "",
            "FASTA Files (*.fas *.fasta *.fa);;All Files (*.*)"
        )

        if not file_path:
            return

        try:
            self.output_panel.append_info(f"Loading: {file_path}")

            # Get sequence headers for preview
            headers = self.file_service.get_fasta_headers(file_path, limit=100)

            if not headers:
                QMessageBox.warning(self, "Warning", "No sequences found in file!")
                return

            # Show standardization dialog
            config = StandardizationDialog.get_standardization_config(headers, self)

            if config is None:
                # User cancelled
                self.output_panel.append_info("Load cancelled by user")
                return

            # Load sequences (using simple delimiter for initial load)
            taxons = self.file_service.load_fasta_file(file_path, delimiter="|")

            # Apply standardization
            taxons = self.file_service.apply_standardization(taxons, config)

            self.table_model.clear()
            self.table_model.add_taxons(taxons)

            self.current_file = file_path
            self.data_loaded = True

            self._update_selected_count()
            self.data_tab.update_counts(total=len(taxons))

            self.output_panel.append_success(f"Loaded {len(taxons)} sequences")
            self._check_trait_completeness(taxons)
            self.switch_to_tab('data')

        except Exception as e:
            self.output_panel.append_error(f"Failed to load file: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")

    def _add_sequence(self):
        """Add sequences to existing data."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Add Sequence File", "",
            "FASTA Files (*.fas *.fasta *.fa);;All Files (*.*)"
        )

        if not file_path:
            return

        try:
            self.output_panel.append_info(f"Adding sequences from: {file_path}")

            # Get sequence headers for preview
            headers = self.file_service.get_fasta_headers(file_path, limit=100)

            if not headers:
                QMessageBox.warning(self, "Warning", "No sequences found in file!")
                return

            # Show standardization dialog
            config = StandardizationDialog.get_standardization_config(headers, self)

            if config is None:
                # User cancelled
                self.output_panel.append_info("Add sequence cancelled by user")
                return

            current_max_id = max((t.id for t in self.table_model.get_all_taxons()), default=0)

            # Load sequences
            taxons = self.file_service.load_fasta_file(file_path, delimiter="|")

            # Apply standardization with ID starting from current max + 1
            taxons = self.file_service.apply_standardization(taxons, config, start_id=current_max_id + 1)

            self.table_model.add_taxons(taxons)

            self._update_selected_count()
            self.data_tab.update_counts(total=self.table_model.rowCount())

            self.output_panel.append_success(f"Added {len(taxons)} sequences")
            self._check_trait_completeness(taxons)

        except Exception as e:
            self.output_panel.append_error(f"Failed to add sequences: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to add sequences: {str(e)}")

    def _export_sequence(self):
        """Export sequences to FASTA file."""
        if self.table_model.rowCount() < 1:
            QMessageBox.warning(self, "Warning", "No data to export!")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export FASTA File", "", "FASTA Files (*.fasta);;All Files (*.*)"
        )

        if file_path:
            if not file_path.lower().endswith('.fasta'):
                file_path += '.fasta'

            delimiter, ok = QInputDialog.getText(
                self, "Delimiter", "Enter FASTA header delimiter:", text="|"
            )
            if not ok:
                delimiter = "|"

            try:
                self.file_service.export_to_fasta(
                    file_path, self.table_model.get_all_taxons(), delimiter
                )
                self.output_panel.append_success(f"Sequences exported to: {file_path}")
                QMessageBox.information(self, "Success", "Export completed!")
            except Exception as e:
                self.output_panel.append_error(f"Failed to export: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")

    def _load_csv_traits(self):
        """Import discrete / continuous traits from a CSV file.

        Workflow:
        1. Require that sequences have been loaded first.
        2. Let the user pick a CSV file.
        3. Read the CSV headers and first few rows; show a column-mapping dialog.
        4. Read all data rows using the chosen column indices.
        5. Validate that every sequence name in the loaded table appears in the
           CSV (and vice-versa).  Report any mismatches as an error and abort.
        6. If traits are already present, ask the user whether to overwrite them.
        7. Apply the new trait values to the table model.
        """
        # Step 1 – Sequence must be loaded first
        if self.table_model.rowCount() < 1:
            QMessageBox.warning(self, "Warning", "Please load a sequence file first before importing traits!")
            return

        # Step 2 – Choose CSV file
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load CSV Traits File",
            "",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        if not file_path:
            return

        try:
            # Step 3 – Read CSV and show column-mapping dialog
            encoding = self.file_service.detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='replace', newline='') as fh:
                reader = csv.reader(fh)
                all_rows = [row for row in reader if any(cell.strip() for cell in row)]

            if not all_rows:
                QMessageBox.warning(self, "Warning", "The CSV file is empty!")
                return

            headers = all_rows[0]
            data_rows = all_rows[1:]

            if not headers:
                QMessageBox.warning(self, "Warning", "The CSV file has no header row!")
                return

            if not data_rows:
                QMessageBox.warning(self, "Warning", "The CSV file contains no data rows!")
                return

            # Show at most 5 rows in the preview
            preview_rows = data_rows[:5]

            mapping = CsvTraitsImportDialog.get_column_mapping(headers, preview_rows, self)
            if mapping is None:
                self.output_panel.append_info("CSV trait import cancelled by user")
                return

            name_col = mapping['name_col']
            discrete_col = mapping['discrete_col']
            continuous_col = mapping['continuous_col']

            if name_col is None:
                QMessageBox.critical(self, "Error", "Sequence Name column must be selected!")
                return

            # Step 4 – Build lookup: csv_name -> (discrete, continuous)
            csv_trait_map: dict = {}
            for row in data_rows:
                if name_col >= len(row):
                    continue
                seq_name = row[name_col].strip()
                if not seq_name:
                    continue
                discrete = row[discrete_col].strip() if discrete_col is not None and discrete_col < len(row) else ""
                continuous = row[continuous_col].strip() if continuous_col is not None and continuous_col < len(
                    row) else "0"
                csv_trait_map[seq_name] = (discrete, continuous)

            # Step 5 – Validate names
            loaded_names = {t.name for t in self.table_model.get_all_taxons()}
            csv_names = set(csv_trait_map.keys())

            missing_in_csv = loaded_names - csv_names  # loaded but not in CSV
            extra_in_csv = csv_names - loaded_names  # in CSV but not loaded

            if missing_in_csv or extra_in_csv:
                msg_lines = ["Sequence name mismatch detected:\n"]
                if missing_in_csv:
                    msg_lines.append("Sequences in data table NOT found in CSV:")
                    for n in sorted(missing_in_csv):
                        msg_lines.append(f"  • {n}")
                if extra_in_csv:
                    if missing_in_csv:
                        msg_lines.append("")
                    msg_lines.append("Names in CSV NOT found in data table:")
                    for n in sorted(extra_in_csv):
                        msg_lines.append(f"  • {n}")
                QMessageBox.critical(self, "Name Mismatch Error", "\n".join(msg_lines))
                return

            # Step 6 – Ask whether to overwrite if traits already exist
            has_existing_discrete = any(
                self.table_model.get_taxon(i).discrete_traits.strip()
                for i in range(self.table_model.rowCount())
            )
            has_existing_continuous = any(
                self.table_model.get_taxon(i).continuous_traits.strip() not in ("", "0")
                for i in range(self.table_model.rowCount())
            )
            if has_existing_discrete or has_existing_continuous:
                reply = QMessageBox.question(
                    self,
                    "Update Traits",
                    "Trait data already exists for some sequences.\n"
                    "Do you want to overwrite the existing traits with the CSV data?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.output_panel.append_info("CSV trait import cancelled – existing traits kept")
                    return

            # Step 7 – Apply traits to model
            updated = 0
            for i in range(self.table_model.rowCount()):
                taxon = self.table_model.get_taxon(i)
                if taxon is None:
                    continue
                traits = csv_trait_map.get(taxon.name)
                if traits is None:
                    continue
                discrete, continuous = traits
                if discrete_col is not None:
                    taxon.discrete_traits = discrete
                if continuous_col is not None:
                    taxon.continuous_traits = continuous if continuous else "0"
                updated += 1

            # Notify the view that data changed
            if self.table_model.rowCount() > 0:
                top_left = self.table_model.index(0, 0)
                bottom_right = self.table_model.index(
                    self.table_model.rowCount() - 1,
                    self.table_model.columnCount() - 1
                )
                self.table_model.dataChanged.emit(top_left, bottom_right)

            self.output_panel.append_success(
                f"Traits imported from CSV: {updated} sequences updated"
            )
            self._check_trait_completeness(self.table_model.get_all_taxons())
            self.switch_to_tab('data')

        except Exception as e:
            self.output_panel.append_error(f"Failed to import CSV traits: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to import CSV traits:\n{str(e)}")

    # ==================== Data Selection ====================

    def _select_all(self):
        """Select all taxons."""
        self.table_model.select_all()
        self._update_selected_count()

    def _deselect_all(self):
        """Deselect all taxons."""
        self.table_model.deselect_all()
        self._update_selected_count()

    def _update_selected_count(self):
        """Update selected count display."""
        count = self.table_model.get_selected_count()
        total = self.table_model.rowCount()
        self.data_tab.update_counts(selected=count, total=total)

    # ==================== Network Analysis ====================

    def _build_haplotype_network(self):
        """Show algorithm/parameter dialog, then run the selected network analysis."""
        config = HaplotypeNetworkDialog.get_network_config(self)
        if config is None:
            return
        self._run_network_analysis(config.algorithm, extra_args=config.to_extra_args())

    def _run_network_analysis(self, network_type: str, extra_args: list = None):
        """Run haplotype network analysis."""
        if self.table_model.rowCount() < 1:
            QMessageBox.warning(self, "Warning", "Please load data first!")
            return

        selected = self.table_model.get_selected_taxons()
        if not selected:
            QMessageBox.warning(self, "Warning", "Please select sequences first!")
            return

        valid, message = self.table_model.validate_for_analysis()
        if not valid:
            QMessageBox.critical(self, "Validation Error", message)
            return

        # Get output path and project prefix from output panel
        output_path = self.get_output_path()
        if not output_path:
            QMessageBox.warning(self, "Warning", "Please set output directory first!")
            return

        prefix = self.get_project_prefix()
        if not prefix:
            QMessageBox.warning(self, "Warning", "Please enter a project name!")
            return

        # Warn if selected data lacks traits that affect visualization
        has_discrete = any(t.discrete_traits.strip() for t in selected)
        has_continuous = any(
            t.continuous_traits.strip() not in ("", "0") and t.is_valid_continuous_traits()
            for t in selected
        )
        if not has_discrete:
            self.output_panel.append_warning(
                "所选数据无离散性状（Discrete Traits），可视化将使用默认分组（Default），无法进行分组可视化"
            )
        if not has_continuous:
            self.output_panel.append_info(
                "所选数据无有效连续性状（Continuous Traits），将仅生成基础单倍型网络图，无法进行双性状可视化"
            )

        # Clear any leftover pending JS before showing the waiting state
        self._pending_js = None

        self.switch_to_tab('network')
        waiting_page = os.path.join(self.current_directory, "statics", self.language, "waiting.html")
        if os.path.isfile(waiting_page):
            self.web_view_main.setUrl(QUrl.fromLocalFile(waiting_page))

        self.output_panel.append_info(f"Starting {network_type} network analysis...")
        self.output_panel.append_info(f"Project: {prefix}")
        self.output_panel.append_info(f"Output directory: {output_path}")
        self.set_status("Analyzing...")

        self.analysis_worker = AnalysisWorker(
            self.analysis_service, network_type, selected, output_path, prefix,
            extra_args=extra_args or []
        )
        self.analysis_worker.progress.connect(self.set_progress)
        self.analysis_worker.log.connect(self.output_panel.append_info)
        self.analysis_worker.finished.connect(self._on_analysis_finished)
        self.analysis_worker.start()

    def _on_analysis_finished(self, result: AnalysisResult):
        """Handle analysis completion.

        On success the generated JS data file (prefix.js) is injected into the
        persistent index.html page so that tcsBU's loadGraph / loadGroups /
        loadHaplotypes / loadTraits functions are called without navigating away
        from index.html.
        """
        index_html = os.path.join(self.current_directory, "statics", "tcsbu", "index.html")

        if result.success:
            self.output_panel.append_success("Analysis completed!")
            js_file = os.path.join(result.output_path, f"{result.prefix}.js")
            if os.path.isfile(js_file):
                self._pending_js = self._build_network_js_injection(
                    js_file, result.has_continuous_traits
                )
                self.output_panel.append_info("Loading network visualization…")
            # Reload index.html to reset tcsBU state, then inject data via loadFinished handler.
            if os.path.isfile(index_html):
                self.web_view_main.setUrl(QUrl.fromLocalFile(index_html))
            self.switch_to_tab('network')
        else:
            self.output_panel.append_error(f"Analysis failed: {result.error_message}")
            QMessageBox.critical(self, "Error", f"Analysis failed: {result.error_message}")
            # Return to index.html (reset state, no pending JS)
            if os.path.isfile(index_html):
                self.web_view_main.setUrl(QUrl.fromLocalFile(index_html))

        # Show / refresh the Alignment tab whenever an aligned FASTA was produced.
        if result.aligned_fasta:
            self.show_alignment_tab(result.aligned_fasta)

        # Show / refresh the Haplotype tab whenever haplotype data was produced,
        # regardless of whether downstream steps (fastHaN, visualization) succeeded.
        if result.haplotype_ready:
            self.show_haplotype_tab(result.output_path, result.prefix)

        # Always end on the Network tab after building a haplotype network.
        if result.success:
            self.switch_to_tab('network')

        self.set_progress(0)
        self.set_status("Ready")

    def _on_web_view_load_finished(self, ok: bool) -> None:
        """Inject pending network data JS after index.html finishes loading."""
        if self._pending_js is None:
            return
        js = self._pending_js
        self._pending_js = None
        if not ok:
            self.output_panel.append_warning("Network view page failed to load; visualization not injected.")
            return
        # Delay slightly to let tcsBU's $(document).ready() and w2ui layout fully initialise.
        QTimer.singleShot(300, lambda: self.web_view_main.page().runJavaScript(js))

    def _build_network_js_injection(self, js_file: str, has_continuous_traits: bool) -> str:
        """Build the JavaScript string that loads analysis results into index.html.

        Reads the generated prefix.js (which embeds GML + CSV contents as JS
        File objects) and appends calls to the tcsBU window-level load functions.
        loadGroups is skipped when groupconf is empty (no discrete traits) to
        avoid a spurious tcsBU warning popup.
        """
        with open(js_file, 'r', encoding='utf-8') as fh:
            prefix_js = fh.read()

        # Check whether groupconf has any real entries (non-empty file means named groups exist)
        groupconf_path = js_file.replace('.js', '_groupconf.csv')
        has_named_groups = (
                os.path.isfile(groupconf_path) and
                os.path.getsize(groupconf_path) > 0
        )

        lines = [prefix_js, ""]
        lines.append("(function () {")
        lines.append("    if (typeof window.loadGraph !== 'function') { return; }")
        lines.append("    if (typeof gmlfile === 'undefined') { return; }")
        lines.append("    window.loadGraph(gmlfile);")
        if has_named_groups:
            lines.append("    if (typeof groupconffile !== 'undefined') window.loadGroups(groupconffile);")
        lines.append("    if (typeof hapconffile !== 'undefined') window.loadHaplotypes(hapconffile);")
        if has_continuous_traits:
            lines.append("    if (typeof traitconffile !== 'undefined') window.loadTraits(traitconffile);")
        lines.append("})();")
        return "\n".join(lines)

    # ==================== Alignment Functions ====================

    def _run_sequence_alignment(self):
        """Show Multiple Sequence Alignment dialog then run the selected aligner."""
        if self.table_model.rowCount() < 1:
            QMessageBox.warning(self, "Warning", "Please load data first!")
            return

        selected = self.table_model.get_selected_taxons()
        if not selected:
            QMessageBox.warning(self, "Warning", "Please select sequences first!")
            return

        config = SequenceAlignmentDialog.get_alignment_config(self)
        if config is None:
            return

        output_path = self.get_output_path()
        if not output_path:
            QMessageBox.warning(self, "Warning", "Please set output directory first!")
            return

        prefix = self.get_project_prefix()
        if not prefix:
            QMessageBox.warning(self, "Warning", "Please enter a project name!")
            return

        tool_label = "MAFFT" if config.tool == "mafft" else "MUSCLE"
        self.output_panel.append_info(
            f"Starting {tool_label} multiple sequence alignment "
            f"({len(selected)} sequences)...")
        self.set_status("Aligning...")

        self.alignment_worker = AlignmentWorker(
            self.analysis_service, selected, output_path, prefix, config)
        self.alignment_worker.log.connect(self.output_panel.append_info)
        self.alignment_worker.finished.connect(self._on_alignment_finished)
        self.alignment_worker.start()

    def _on_alignment_finished(self, result: AlignmentResult):
        """Handle standalone alignment completion."""
        self.set_status("Ready")
        if result.success:
            self.output_panel.append_success(
                f"Alignment completed → {result.output_file}")
            self.show_alignment_tab(result.output_file)
        else:
            self.output_panel.append_error(
                f"Alignment failed: {result.error_message}")
            QMessageBox.critical(
                self, "Alignment Failed",
                f"Alignment failed:\n{result.error_message}")

    # ==================== Haplotype Calculation ====================

    def _calculate_haplotype(self):
        """Show MSA dialog, run alignment + haplotype calculation, display in Haplotype tab."""
        if self.table_model.rowCount() < 1:
            QMessageBox.warning(self, "Warning", "Please load data first!")
            return

        selected = self.table_model.get_selected_taxons()
        if not selected:
            QMessageBox.warning(self, "Warning", "Please select sequences first!")
            return

        config = SequenceAlignmentDialog.get_alignment_config(self)
        if config is None:
            return

        output_path = self.get_output_path()
        if not output_path:
            QMessageBox.warning(self, "Warning", "Please set output directory first!")
            return

        prefix = self.get_project_prefix()
        if not prefix:
            QMessageBox.warning(self, "Warning", "Please enter a project name!")
            return

        tool_label = "MAFFT" if config.tool == "mafft" else "MUSCLE"
        self.output_panel.append_info(
            f"Starting haplotype calculation with {tool_label} alignment "
            f"({len(selected)} sequences)...")
        self.set_status("Calculating haplotypes...")

        self.haplotype_worker = HaplotypeWorker(
            self.analysis_service, selected, output_path, prefix, config)
        self.haplotype_worker.progress.connect(self.set_progress)
        self.haplotype_worker.log.connect(self.output_panel.append_info)
        self.haplotype_worker.finished.connect(self._on_haplotype_calculation_finished)
        self.haplotype_worker.start()

    def _on_haplotype_calculation_finished(self, result: AnalysisResult):
        """Handle haplotype calculation completion."""
        self.set_progress(0)
        self.set_status("Ready")

        if result.success:
            self.output_panel.append_success("Haplotype calculation completed!")
        else:
            self.output_panel.append_error(
                f"Haplotype calculation failed: {result.error_message}")
            QMessageBox.critical(
                self, "Error",
                f"Haplotype calculation failed:\n{result.error_message}")

        if result.aligned_fasta:
            self.show_alignment_tab(result.aligned_fasta)

        if result.haplotype_ready:
            self.show_haplotype_tab(result.output_path, result.prefix)

        # Always end on the Haplotype tab after haplotype calculation.
        if result.haplotype_ready:
            self.switch_to_tab('haplotype')

    # ==================== Tools Functions ====================

    def _set_language(self, lang: str):
        """Set interface language."""
        lang_manager.set_language(lang)
        self.language = lang

        # Rebuild menu bar
        if self.menu_builder:
            self.menu_builder.rebuild()

        # Update window title
        self.setWindowTitle(lang_manager.get('window_title'))

        # Update tab names using widget references so indices don't need to be hard-coded
        for widget, lang_key in [
            (self.web_view_main, 'tab_network'),
            (self.data_tab, 'tab_data'),
        ]:
            idx = self.tab_widget.indexOf(widget)
            if idx >= 0:
                self.tab_widget.setTabText(idx, lang_manager.get(lang_key))

        # Update component texts
        if self.data_tab:
            self.data_tab.update_language()
        if self.output_panel:
            self.output_panel.update_language()
        if self.status_bar_widget:
            self.status_bar_widget.set_status(lang_manager.get('status_ready'))

        self.output_panel.append_info(lang_manager.get('msg_language_changed'))

        # Reload main page
        main_page = os.path.join(self.current_directory, "statics", self.language, "main.html")
        if os.path.isfile(main_page):
            self.load_main_page(main_page)

    # ==================== Help Functions ====================

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About",
            "Haplotype Network Analysis Tool\n\n"
            "Version: 2.0.0\n\n"
            "Python version rebuilt with PyQt6\n\n"
            "For haplotype network construction and analysis"
        )

    def _show_help(self):
        """Show help documentation (legacy entry point)."""
        self._show_netst_help()

    def _show_tcsbu_help(self):
        """Open TCS-BU help PDF with the system default PDF viewer."""
        pdf_path = os.path.join(self.current_directory, "statics", "docs", "tcsbu.pdf")
        if not os.path.isfile(pdf_path):
            QMessageBox.warning(self, "TCS-BU Help",
                                f"TCS-BU help PDF not found:\n{pdf_path}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))

    def _show_netst_help(self):
        """Open NetST help PDF with the system default PDF viewer."""
        pdf_path = os.path.join(self.current_directory, "statics", "docs", "netst.pdf")
        if not os.path.isfile(pdf_path):
            QMessageBox.warning(self, "NetST Help",
                                f"NetST help PDF not found:\n{pdf_path}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))

    # ==================== Helper Methods ====================

    def _check_trait_completeness(self, taxons: list) -> None:
        """Check loaded taxons for missing discrete / continuous traits and warn the user."""
        has_discrete = any(t.discrete_traits.strip() for t in taxons)
        has_continuous = any(
            t.continuous_traits.strip() not in ("", "0") and t.is_valid_continuous_traits()
            for t in taxons
        )
        if not has_discrete:
            self.output_panel.append_warning(
                "数据中无离散性状（Discrete Traits），将无法进行分组（Group）可视化"
            )
        if not has_continuous:
            self.output_panel.append_info(
                "数据中无有效连续性状（Continuous Traits），将无法进行双性状可视化"
            )


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    _base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(_base, "statics", "icon", "netst.ico")
    if os.path.isfile(icon_path):
        from PyQt6.QtGui import QIcon
        app.setWindowIcon(QIcon(icon_path))

    window = MainForm()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
