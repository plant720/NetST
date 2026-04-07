"""
Main Window Business Logic Module

Implements the main window business logic, inheriting from MainWindowUI base class.
"""

import os
import sys
from typing import Optional, Dict, Callable

from PyQt6.QtCore import QUrl, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QMessageBox, QInputDialog
)

from model.taxon_table_model import TaxonTableModel
from service.analysis_service import AnalysisService, AnalysisResult
from service.file_service import FileService
from ui import MainWindowUI
from ui.language_manager import lang_manager
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
                 taxons: list, output_path: str, prefix: str):
        super().__init__()
        self.analysis_service = analysis_service
        self.network_type = network_type
        self.taxons = taxons
        self.output_path = output_path
        self.prefix = prefix

    def run(self):
        """Execute analysis task in child thread."""
        self.analysis_service.set_progress_callback(lambda v: self.progress.emit(v))
        self.analysis_service.set_log_callback(lambda m: self.log.emit(m))

        result = self.analysis_service.run_network_analysis(
            self.network_type, self.taxons, self.output_path, self.prefix
        )
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

        # Worker thread reference
        self.analysis_worker: Optional[AnalysisWorker] = None

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
            'export_fasta': self._export_sequence,
            'exit': self.close,

            # Analysis Menu
            'network_msn': lambda: self._run_network_analysis("msn"),
            'network_mjn': lambda: self._run_network_analysis("mjn"),
            'network_tcs': lambda: self._run_network_analysis("modified_tcs"),

            # MAFFT alignment
            'mafft_auto': lambda: self._run_mafft_alignment("--auto"),
            'mafft_fftns1': lambda: self._run_mafft_alignment("--retree 1"),
            'mafft_fftns2': lambda: self._run_mafft_alignment("--retree 2"),
            'mafft_ginsi': lambda: self._run_mafft_alignment("--globalpair --maxiterate 1000"),
            'mafft_linsi': lambda: self._run_mafft_alignment("--localpair --maxiterate 1000"),
            'mafft_einsi': lambda: self._run_mafft_alignment("--genafpair --maxiterate 1000"),

            # MUSCLE alignment
            'muscle_ppp': lambda: self._run_muscle_alignment("ppp"),
            'muscle_super5': lambda: self._run_muscle_alignment("super5"),

            # Network analysis
            'network_visualization': self._network_visualization,
            'topology_analysis': self._topology_analysis,
            'modularity_analysis': self._modularity_analysis,
            'community_plot': self._community_plot,
            'sequence_analysis': self._sequence_analysis,
            'population_analysis': self._run_population_analysis,
            'trait_analysis': self._run_trait_analysis,

            'language_chinese': lambda: self._set_language("cn"),
            'language_english': lambda: self._set_language("en"),

            # Help Menu
            'about': self._show_about,
            'help_docs': self._show_help,
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

        self.log_tab.append_info("Application started")
        self.log_tab.append_info(f"Working directory: {self.current_directory}")

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
            self.log_tab.append_info(f"Loading: {file_path}")

            # Get sequence headers for preview
            headers = self.file_service.get_fasta_headers(file_path, limit=100)

            if not headers:
                QMessageBox.warning(self, "Warning", "No sequences found in file!")
                return

            # Show standardization dialog
            config = StandardizationDialog.get_standardization_config(headers, self)

            if config is None:
                # User cancelled
                self.log_tab.append_info("Load cancelled by user")
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

            self.log_tab.append_success(f"Loaded {len(taxons)} sequences")
            self._check_trait_completeness(taxons)
            self.switch_to_tab('data')

        except Exception as e:
            self.log_tab.append_error(f"Failed to load file: {str(e)}")
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
            self.log_tab.append_info(f"Adding sequences from: {file_path}")

            # Get sequence headers for preview
            headers = self.file_service.get_fasta_headers(file_path, limit=100)

            if not headers:
                QMessageBox.warning(self, "Warning", "No sequences found in file!")
                return

            # Show standardization dialog
            config = StandardizationDialog.get_standardization_config(headers, self)

            if config is None:
                # User cancelled
                self.log_tab.append_info("Add sequence cancelled by user")
                return

            # Get current max ID
            current_max_id = 0
            for i in range(self.table_model.rowCount()):
                taxon = self.table_model.get_taxon(i)
                if taxon and taxon.id > current_max_id:
                    current_max_id = taxon.id

            # Load sequences
            taxons = self.file_service.load_fasta_file(file_path, delimiter="|")

            # Apply standardization with ID starting from current max + 1
            taxons = self.file_service.apply_standardization(taxons, config, start_id=current_max_id + 1)

            self.table_model.add_taxons(taxons)

            self._update_selected_count()
            self.data_tab.update_counts(total=self.table_model.rowCount())

            self.log_tab.append_success(f"Added {len(taxons)} sequences")
            self._check_trait_completeness(taxons)

        except Exception as e:
            self.log_tab.append_error(f"Failed to add sequences: {str(e)}")
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
                self.log_tab.append_success(f"Sequences exported to: {file_path}")
                QMessageBox.information(self, "Success", "Export completed!")
            except Exception as e:
                self.log_tab.append_error(f"Failed to export: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")

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

    def _run_network_analysis(self, network_type: str):
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
            t.continuous_traits.strip() not in ("", "0") and self._is_numeric(t.continuous_traits)
            for t in selected
        )
        if not has_discrete:
            self.log_tab.append_warning(
                "所选数据无离散性状（Discrete Traits），可视化将使用默认分组（Default），无法进行分组可视化"
            )
        if not has_continuous:
            self.log_tab.append_info(
                "所选数据无有效连续性状（Continuous Traits），将仅生成基础单倍型网络图，无法进行双性状可视化"
            )

        # Clear any leftover pending JS before showing the waiting state
        self._pending_js = None

        self.switch_to_tab('network')
        waiting_page = os.path.join(self.current_directory, "statics", self.language, "waiting.html")
        if os.path.isfile(waiting_page):
            self.web_view_main.setUrl(QUrl.fromLocalFile(waiting_page))

        self.log_tab.append_info(f"Starting {network_type} network analysis...")
        self.log_tab.append_info(f"Project: {prefix}")
        self.log_tab.append_info(f"Output directory: {output_path}")
        self.set_status("Analyzing...")

        self.analysis_worker = AnalysisWorker(
            self.analysis_service, network_type, selected, output_path, prefix
        )
        self.analysis_worker.progress.connect(self.set_progress)
        self.analysis_worker.log.connect(self.log_tab.append_info)
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
            self.log_tab.append_success("Analysis completed!")
            js_file = os.path.join(result.output_path, f"{result.prefix}.js")
            if os.path.isfile(js_file):
                self._pending_js = self._build_network_js_injection(
                    js_file, result.has_continuous_traits
                )
                self.log_tab.append_info("Loading network visualization…")
            # Reload index.html to reset tcsBU state, then inject data via loadFinished handler.
            if os.path.isfile(index_html):
                self.web_view_main.setUrl(QUrl.fromLocalFile(index_html))
            self.switch_to_tab('network')
        else:
            self.log_tab.append_error(f"Analysis failed: {result.error_message}")
            QMessageBox.critical(self, "Error", f"Analysis failed: {result.error_message}")
            # Return to index.html (reset state, no pending JS)
            if os.path.isfile(index_html):
                self.web_view_main.setUrl(QUrl.fromLocalFile(index_html))

        # Show / refresh the Haplotype tab whenever haplotype data was produced,
        # regardless of whether downstream steps (fastHaN, visualization) succeeded.
        if result.haplotype_ready:
            self.show_haplotype_tab(result.output_path, result.prefix)

        self.set_progress(0)
        self.set_status("Ready")

    def _on_web_view_load_finished(self, ok: bool) -> None:
        """Inject pending network data JS after index.html finishes loading."""
        if self._pending_js is None:
            return
        js = self._pending_js
        self._pending_js = None
        if not ok:
            self.log_tab.append_warning("Network view page failed to load; visualization not injected.")
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

    def _run_mafft_alignment(self, method: str):
        """Run MAFFT alignment."""
        self.log_tab.append_info(f"MAFFT alignment with method: {method}")
        QMessageBox.information(self, "Info", "MAFFT alignment - to be implemented")

    def _run_muscle_alignment(self, method: str):
        """Run MUSCLE alignment."""
        self.log_tab.append_info(f"MUSCLE alignment with method: {method}")
        QMessageBox.information(self, "Info", "MUSCLE alignment - to be implemented")

    # ==================== Analysis Functions ====================

    def _network_visualization(self):
        """Network visualization."""
        self.log_tab.append_info("Network visualization")
        QMessageBox.information(self, "Info", "Network visualization - to be implemented")

    def _topology_analysis(self):
        """Topology analysis."""
        self.log_tab.append_info("Topology analysis")
        QMessageBox.information(self, "Info", "Topology analysis - to be implemented")

    def _modularity_analysis(self):
        """Modularity analysis."""
        self.log_tab.append_info("Modularity analysis")
        QMessageBox.information(self, "Info", "Modularity analysis - to be implemented")

    def _community_plot(self):
        """Community plot."""
        self.log_tab.append_info("Community plot")
        QMessageBox.information(self, "Info", "Community plot - to be implemented")

    def _sequence_analysis(self):
        """Sequence analysis."""
        self.log_tab.append_info("Sequence analysis")
        QMessageBox.information(self, "Info", "Sequence analysis - to be implemented")

    def _run_population_analysis(self):
        """Run population analysis."""
        self.log_tab.append_info("Population analysis")
        QMessageBox.information(self, "Info", "Population analysis - to be implemented")

    def _run_trait_analysis(self):
        """Run trait association analysis."""
        self.log_tab.append_info("Trait association analysis")
        QMessageBox.information(self, "Info", "Trait analysis - to be implemented")

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
            (self.data_tab,      'tab_data'),
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
        """Show help documentation."""
        help_html = os.path.join(self.current_directory, "statics", "help.html")

        if os.path.isfile(help_html):
            self.load_main_page(help_html)
            self.switch_to_tab('network')
        else:
            QMessageBox.information(self, "Help", "Help documentation is being written...")

    # ==================== Helper Methods ====================

    def _check_trait_completeness(self, taxons: list) -> None:
        """Check loaded taxons for missing discrete / continuous traits and warn the user."""
        has_discrete = any(t.discrete_traits.strip() for t in taxons)
        has_continuous = any(
            t.continuous_traits.strip() not in ("", "0") and t.is_valid_continuous_traits()
            for t in taxons
        )
        if not has_discrete:
            self.log_tab.append_warning(
                "数据中无离散性状（Discrete Traits），将无法进行分组（Group）可视化"
            )
        if not has_continuous:
            self.log_tab.append_info(
                "数据中无有效连续性状（Continuous Traits），将无法进行双性状可视化"
            )

    @staticmethod
    def _is_numeric(value: str) -> bool:
        """Check if string is numeric."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "statics", "icon", "netst.ico")
    if os.path.isfile(icon_path):
        from PyQt6.QtGui import QIcon
        app.setWindowIcon(QIcon(icon_path))

    window = MainForm()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
