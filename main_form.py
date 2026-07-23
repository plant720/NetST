"""
Main Window Business Logic Module

Implements the main window business logic, inheriting from MainWindowUI base class.
"""

import os
import sys
import json
import math
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Optional, Dict, Callable

from PyQt6.QtCore import QUrl, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QMessageBox
)

from model.taxon_data import TaxonData
from model.taxon_table_model import TaxonTableModel
from service.analysis_service import AnalysisService, AnalysisResult, AlignmentResult
from service.file_service import FileService
from service.format_conversion_service import (
    FormatConversionError,
    convert_file,
    import_vcf,
    read_fasta,
    read_metadata_rows,
)
from service.interpretation_models import AnalysisDataError, AnalysisDataset
from service.diversity_analysis_service import (
    AnalysisCancelled as DiversityAnalysisCancelled,
    analyze_diversity,
)
from service.distance_analysis_service import (
    DistanceAnalysisCancelled,
    analyze_distance_pcoa,
)
from service.mcan_adapter import McanVcfInput
from service.validation_service import (
    ValidationIssue,
    find_duplicates,
    has_meaningful_continuous_trait,
    validate_project_prefix,
    validate_taxons,
)
from ui.main_window_ui import MainWindowUI
from ui.alignment_tab_widget import AlignmentTabWidget
from ui.csv_traits_import_dialog import CsvTraitsImportDialog
from ui.format_conversion_dialog import FormatConversionDialog
from ui.haplotype_network_dialog import HaplotypeNetworkDialog
from ui.haplotype_tab_widget import HaplotypeTabWidget
from ui.language_manager import lang_manager
from ui.interpretation_options_dialog import InterpretationOptionsDialog
from ui.sequence_alignment_dialog import SequenceAlignmentDialog, SequenceAlignmentConfig
from ui.standardization_dialog import StandardizationDialog
from ui.vcf_import_dialog import VcfImportDialog

# Platform-specific WebEngine flags
if sys.platform.startswith('win'):
    # Windows x86_64: disable sandbox for compatibility in restricted environments
    os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--no-sandbox')


# macOS arm64 (native Apple Silicon Python): no flags needed.
# The GPU-disabling flags above were only required when running x86_64 Python
# through Rosetta, which caused GPU/sandbox crashes.  With native arm64 Python,
# WebEngine runs correctly without any workarounds.


class AnalysisWorker(QThread):
    """Worker thread for running analysis tasks in background."""

    finished = pyqtSignal(object)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)

    def __init__(self, analysis_service: AnalysisService, network_type: str,
                 taxons: list, output_path: str, prefix: str,
                 extra_args: list = None,
                 mcan_vcf_input: Optional[McanVcfInput] = None):
        super().__init__()
        self.analysis_service = analysis_service
        self.network_type = network_type
        self.taxons = taxons
        self.output_path = output_path
        self.prefix = prefix
        self.extra_args = extra_args or []
        self.mcan_vcf_input = mcan_vcf_input

    def run(self):
        """Execute analysis task in child thread."""
        self.analysis_service.set_progress_callback(lambda v: self.progress.emit(v))
        self.analysis_service.set_log_callback(lambda m: self.log.emit(m))
        self.analysis_service.set_cancel_callback(self.isInterruptionRequested)

        result = self.analysis_service.run_network_analysis(
            self.network_type, self.taxons, self.output_path, self.prefix,
            extra_args=self.extra_args,
            mcan_vcf_input=self.mcan_vcf_input,
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
        self.analysis_service.set_cancel_callback(self.isInterruptionRequested)
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
        self.analysis_service.set_cancel_callback(self.isInterruptionRequested)
        result = self.analysis_service.run_haplotype_calculation(
            self.taxons, self.output_path, self.prefix, self.config)
        self.finished.emit(result)


class AlignmentTabLoadWorker(QThread):
    """Parses an aligned FASTA file in the background so the Alignment tab
    can be populated without blocking the UI thread."""

    finished = pyqtSignal(object)  # parse_alignment_data() dict

    def __init__(self, fasta_path: str):
        super().__init__()
        self.fasta_path = fasta_path

    def run(self):
        data = AlignmentTabWidget.parse_alignment_data(
            self.fasta_path, cancel_check=self.isInterruptionRequested)
        self.finished.emit(data)


class HaplotypeTabLoadWorker(QThread):
    """Parses haplotype result files (FASTA + CSVs) in the background so the
    Haplotype tab can be populated without blocking the UI thread."""

    finished = pyqtSignal(object)  # parse_result_data() dict

    def __init__(self, output_path: str, prefix: str):
        super().__init__()
        self.output_path = output_path
        self.prefix = prefix

    def run(self):
        data = HaplotypeTabWidget.parse_result_data(
            self.output_path, self.prefix,
            cancel_check=self.isInterruptionRequested,
        )
        self.finished.emit(data)


class InterpretationWorker(QThread):
    """Run pure auxiliary analyses without blocking the Qt event loop."""

    finished = pyqtSignal(object)

    def __init__(self, kind: str, payload, options: Optional[dict] = None):
        super().__init__()
        self.kind = kind
        self.payload = payload
        self.options = options or {}

    def run(self):
        try:
            if self.kind == 'diversity':
                result = analyze_diversity(
                    self.payload,
                    group_trait='group',
                    missing_policy=self.options.get(
                        'missing_policy', 'complete_deletion'),
                    cancel_check=self.isInterruptionRequested,
                )
            elif self.kind == 'distance':
                result = analyze_distance_pcoa(
                    self.payload.samples,
                    minimum_comparable_sites=int(self.options.get(
                        'minimum_comparable_sites', 1)),
                    minimum_coverage=float(self.options.get(
                        'minimum_coverage', 0.5)),
                    cancel_requested=self.isInterruptionRequested,
                )
            elif self.kind == 'topology':
                from service.topology_analysis_service import analyze_gml
                result = analyze_gml(
                    self.payload,
                    cancel_requested=self.isInterruptionRequested,
                )
            else:
                raise ValueError(f'Unsupported interpretation analysis: {self.kind}')
            self.finished.emit({
                'kind': self.kind, 'success': True, 'result': result,
                'cancelled': False, 'error': '',
            })
        except (DiversityAnalysisCancelled, DistanceAnalysisCancelled) as exc:
            self.finished.emit({
                'kind': self.kind, 'success': False, 'result': None,
                'cancelled': True, 'error': str(exc),
            })
        except Exception as exc:
            # Topology cancellation uses its own exception type and is imported
            # lazily; treating an interrupted worker as cancelled keeps this
            # adapter independent of the topology module's implementation.
            self.finished.emit({
                'kind': self.kind, 'success': False, 'result': None,
                'cancelled': self.isInterruptionRequested(), 'error': str(exc),
            })


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
        self._mcan_vcf_input: Optional[McanVcfInput] = None
        self._vcf_sequence_snapshot: Dict[str, str] = {}

        # Service instances
        self.file_service = FileService()
        self.analysis_service = AnalysisService(self.current_directory)

        # Data model
        self.table_model = TaxonTableModel()

        # Worker thread references
        self.analysis_worker: Optional[AnalysisWorker] = None
        self.alignment_worker: Optional[AlignmentWorker] = None
        self.haplotype_worker: Optional[HaplotypeWorker] = None
        self.interpretation_worker: Optional[InterpretationWorker] = None
        self._active_worker: Optional[QThread] = None
        # Background loaders for the Alignment and Haplotype tabs. They parse
        # result files so the tabs can be populated without blocking the UI.
        self.alignment_tab_loader: Optional[AlignmentTabLoadWorker] = None
        self.haplotype_tab_loader: Optional[HaplotypeTabLoadWorker] = None
        self._last_interpretation_kind: Optional[str] = None
        self._last_interpretation_result = None

        # Result files remain on disk between projects. Track which editable
        # input revision produced them so interpretation never silently reuses
        # an older alignment or network that only happens to share a prefix.
        self._input_generation = 0
        self._aligned_result_generation: Optional[int] = None
        self._network_result_generation: Optional[int] = None

        # Network-page navigation is asynchronous. Generation tokens prevent a
        # late loadFinished/timer callback from injecting an older result into
        # the current tcsBU page.
        self._network_view_generation = 0
        self._pending_js: Optional[str] = None
        self._pending_js_generation: Optional[int] = None

        # Initialization
        self._init_components()
        self._setup_menus()
        self._setup_connections()

        # Delayed loading of initial pages
        QTimer.singleShot(100, self._load_initial_pages)

    @staticmethod
    def _stop_worker(worker: Optional[QThread]) -> None:
        """Stop a previous QThread worker so a new one can take its place.

        Prevents abandoned threads when the user kicks off a new analysis
        (or tab loader) before the previous one has finished.
        """
        if worker is None or not worker.isRunning():
            return
        worker.requestInterruption()
        # run() is synchronous, so quit() alone cannot stop it. The analysis
        # service observes requestInterruption() and terminates its process tree.
        if not worker.wait(7000):
            worker.terminate()
            worker.wait()

    def _init_components(self):
        """Initialize components."""
        self.data_tab.set_model(self.table_model)
        self.data_tab.set_select_all_callback(self._select_all)
        self.data_tab.set_deselect_all_callback(self._deselect_all)

    def _set_active_worker(self, worker: QThread) -> None:
        """Expose cancellation for the currently running analysis worker."""
        self._active_worker = worker
        self.status_bar_widget.set_cancel_callback(self._cancel_active_task)
        self._set_analysis_actions_enabled(False)

    def _start_active_worker(self, worker: QThread) -> None:
        """Register a worker before it starts so fast completion cannot race UI state."""
        self._set_active_worker(worker)
        try:
            worker.start()
        except Exception:
            self._clear_active_worker(worker)
            raise

    def _clear_active_worker(self, worker: QThread) -> None:
        if self._active_worker is worker:
            self._active_worker = None
            self.status_bar_widget.set_cancel_callback(None)
            self._set_analysis_actions_enabled(True)

    def _set_analysis_actions_enabled(self, enabled: bool) -> None:
        if not self.menu_builder:
            return
        for key in (
            'load_sequence', 'load_nexus', 'load_phylip', 'load_vcf',
            'load_csv_traits',
            'build_haplotype_network', 'run_msa', 'calculate_haplotype',
            'analyze_diversity_qc', 'analyze_distance_pcoa', 'analyze_topology',
        ):
            self.menu_builder.set_action_enabled(key, enabled)
        # The table and output target are inputs to background work. Locking
        # them prevents one run from observing a mixture of old and new data.
        self.data_tab.setEnabled(enabled)
        self.output_panel.project_name_edit.setEnabled(enabled)
        self.output_panel.btn_change.setEnabled(enabled)

    def _cancel_active_task(self) -> None:
        worker = self._active_worker
        if worker is not None and worker.isRunning():
            if worker is self.interpretation_worker:
                self._append_localized_log(
                    'warning', 'log_interpretation_cancel_requested',
                    'Cancellation requested; stopping interpretation analysis…')
            else:
                self._append_localized_log(
                    'warning', 'log_cancel_requested',
                    'Cancellation requested; stopping external process…')
            worker.requestInterruption()

    def _setup_menus(self):
        """Setup menu bar."""
        callbacks = self._get_callbacks()
        self.setup_menus(callbacks)

    def _get_callbacks(self) -> Dict[str, Callable]:
        """Get all menu callback functions."""
        return {
            # File Menu
            'load_sequence': self._load_sequence,
            'load_nexus': self._load_nexus,
            'load_phylip': self._load_phylip,
            'load_vcf': self._load_vcf,
            'load_csv_traits': self._load_csv_traits,
            'export_sequences': self._export_sequences,
            'export_traits': self._export_traits,
            'exit': self.close,

            # Analysis Menu
            'build_haplotype_network': self._build_haplotype_network,
            'analyze_diversity_qc': self._analyze_diversity_qc,
            'analyze_distance_pcoa': self._analyze_distance_pcoa,
            'analyze_topology': self._analyze_topology,

            # Tools Menu
            'run_msa': self._run_sequence_alignment,
            'calculate_haplotype': self._calculate_haplotype,
            'format_conversion': self._convert_sequence_format,
            'language_chinese': lambda: self._set_language("cn"),
            'language_english': lambda: self._set_language("en"),

            # Help Menu
            'about': self._show_about,
            'help_tcsbu': self._show_tcsbu_help,
            'help_netst': self._show_netst_help,
        }

    def _setup_connections(self):
        """Setup signal connections."""
        self.table_model.dataChanged.connect(self._on_table_data_changed)
        self.data_tab.selection_changed.connect(self._update_selected_count)
        # Connect WebEngine loadFinished so we can inject data JS after each analysis.
        if hasattr(self.web_view_main, 'loadFinished'):
            self.web_view_main.loadFinished.connect(self._on_web_view_load_finished)

    def _load_initial_pages(self):
        """Load initial HTML pages."""
        # Load the tcsBU interface as the default network tab view.
        index_html = os.path.join(self.current_directory, "static", "tcsbu", "index.html")
        if os.path.isfile(index_html):
            self.load_main_page(index_html)

        self._append_localized_log('info', 'log_app_started', 'Application started')
        self._append_localized_log(
            'info', 'log_working_directory', 'Working directory: {path}',
            path=self.current_directory)

    # ==================== File Operations ====================

    def _clear_vcf_source(self) -> None:
        self._mcan_vcf_input = None
        self._vcf_sequence_snapshot = {}

    def _invalidate_derived_results(self) -> None:
        """Remove result views that no longer match the editable input table."""
        self._input_generation += 1
        self._aligned_result_generation = None
        self._network_result_generation = None
        self._network_view_generation += 1
        self._pending_js = None
        self._pending_js_generation = None
        self._last_interpretation_kind = None
        self._last_interpretation_result = None

        # Loader results are guarded by identity checks, so requesting
        # interruption and dropping the current token is enough to make any
        # late result harmless without force-terminating a Python thread.
        for attr in ('alignment_tab_loader', 'haplotype_tab_loader'):
            worker = getattr(self, attr)
            if worker is not None and worker.isRunning():
                worker.requestInterruption()
            setattr(self, attr, None)

        for attr in ('alignment_tab', 'haplotype_tab', 'interpretation_tab'):
            widget = getattr(self, attr)
            if widget is None:
                continue
            index = self.tab_widget.indexOf(widget)
            if index >= 0:
                self.tab_widget.removeTab(index)
            widget.deleteLater()
            setattr(self, attr, None)

        index_html = os.path.join(
            self.current_directory, 'static', 'tcsbu', 'index.html')
        if os.path.isfile(index_html):
            self.web_view_main.setUrl(QUrl.fromLocalFile(index_html))

    def _on_table_data_changed(self, top_left, bottom_right, _roles=None) -> None:
        """Invalidate derived output after selection or editable input changes."""
        # Name, sequence, and trait edits invalidate the original native VCF
        # provenance. Selection-only changes can still reuse the VCF subset.
        if top_left.column() <= 5 and bottom_right.column() >= 2:
            self._clear_vcf_source()
        self._invalidate_derived_results()

    def _current_mcan_vcf_input(self) -> Optional[McanVcfInput]:
        """Return native VCF input only while imported names/sequences are unchanged."""
        if self._mcan_vcf_input is None or not self._vcf_sequence_snapshot:
            return None
        current = {
            taxon.name: taxon.sequence
            for taxon in self.table_model.get_all_taxons()
        }
        if current != self._vcf_sequence_snapshot:
            return None
        return self._mcan_vcf_input

    def _load_vcf(self):
        """Import VCF samples and metadata as aligned sequence-table records."""
        config = VcfImportDialog.get_import_config(self)
        if config is None:
            return
        try:
            result = import_vcf(
                config['vcf_path'],
                config['metadata_path'],
                config['reference_fasta'],
            )
            taxons = list(result.taxons)
            self.table_model.clear()
            self.table_model.add_taxons(taxons)
            self._invalidate_derived_results()
            self._vcf_sequence_snapshot = {
                taxon.name: taxon.sequence for taxon in taxons
            }

            # Native McAN VCF mode requires its six-column tab-delimited
            # metadata. Generic CSV metadata still imports traits, but McAN
            # falls back to the aligned-FASTA adapter.
            try:
                read_metadata_rows(config['metadata_path'])
                self._mcan_vcf_input = McanVcfInput(
                    config['vcf_path'], config['metadata_path'])
            except FormatConversionError:
                self._mcan_vcf_input = None
                self._append_localized_log(
                    'warning', 'log_vcf_metadata_not_native',
                    'Metadata was imported, but it is not McAN six-column TSV; '
                    'McAN will use the converted alignment instead of native VCF mode.')

            self._update_selected_count()
            self.data_tab.update_counts(total=len(taxons))
            mode = lang_manager.get(
                'vcf_mode_full' if result.full_length else 'vcf_mode_variable',
                'full-length alignment' if result.full_length else 'variable-site alignment')
            self._append_localized_log(
                'success', 'log_vcf_loaded',
                'Loaded {samples} VCF samples and {records} variant records '
                'as a {mode} ({length} sites).',
                samples=len(taxons), records=result.variant_records,
                mode=mode, length=result.alignment_length)
            for warning in result.warnings:
                self.log_tab.append_warning(warning)
            self._check_trait_completeness(taxons)
            self.switch_to_tab('data')
            QMessageBox.information(
                self, lang_manager.get('title_success', 'Success'),
                lang_manager.get(
                    'msg_vcf_import_complete',
                    'Imported {samples} samples from {records} VCF records as a {mode}.'
                ).format(samples=len(taxons), records=result.variant_records, mode=mode))
        except (FormatConversionError, OSError) as e:
            self._append_localized_log(
                'error', 'log_vcf_import_failed', 'VCF import failed: {error}',
                error=str(e))
            QMessageBox.critical(
                self, lang_manager.get('title_error', 'Error'),
                lang_manager.get('msg_vcf_import_failed',
                                 'VCF import failed: {error}').format(error=str(e)))

    def _convert_sequence_format(self):
        """Run an explicit FASTA/PHYLIP/VCF conversion from the Tools menu."""
        config = FormatConversionDialog.get_conversion_config(self)
        if config is None:
            return
        try:
            convert_file(
                config['input_path'],
                config['output_path'],
                input_format=config['input_format'],
                output_format=config['output_format'],
                reference_fasta=config['reference_fasta'],
                reference_name=config['reference_name'],
            )
            self._append_localized_log(
                'success', 'log_conversion_complete',
                'Format conversion completed: {path}', path=config['output_path'])
            QMessageBox.information(
                self, lang_manager.get('title_success', 'Success'),
                lang_manager.get('msg_conversion_complete',
                                 'Format conversion completed:\n{path}').format(
                                     path=config['output_path']))
        except (FormatConversionError, OSError) as e:
            self._append_localized_log(
                'error', 'log_conversion_failed',
                'Format conversion failed: {error}', error=str(e))
            QMessageBox.critical(
                self, lang_manager.get('title_error', 'Error'),
                lang_manager.get('msg_conversion_failed',
                                 'Format conversion failed: {error}').format(error=str(e)))

    def _load_sequence(self):
        """Load sequence data from FASTA file."""
        self._load_sequence_format('fasta')

    def _load_nexus(self):
        """Load a NEXUS DATA/CHARACTERS matrix as the current raw data."""
        self._load_sequence_format('nexus')

    def _load_phylip(self):
        """Load a PHYLIP alignment as the current raw data."""
        self._load_sequence_format('phylip')

    def _load_sequence_format(self, file_format: str) -> None:
        """Load and standardize one supported sequence file format."""
        options = {
            'fasta': (
                'dlg_load_seq_title', 'Load FASTA File',
                'filter_fasta', 'FASTA Files (*.fas *.fasta *.fa *.fna *.ffn);;All Files (*.*)',
                self.file_service.load_fasta_file,
            ),
            'nexus': (
                'dlg_load_nexus_title', 'Import NEXUS File',
                'filter_nexus', 'NEXUS Files (*.nex *.nexus *.nxs);;All Files (*.*)',
                self.file_service.load_nexus_file,
            ),
            'phylip': (
                'dlg_load_phylip_title', 'Import PHYLIP File',
                'filter_phylip', 'PHYLIP Files (*.phy *.phylip);;All Files (*.*)',
                self.file_service.load_phylip_file,
            ),
        }
        title_key, title_default, filter_key, filter_default, loader = options[file_format]
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            lang_manager.get(title_key, title_default),
            "",
            lang_manager.get(filter_key, filter_default),
        )

        if not file_path:
            return

        try:
            self._append_localized_log(
                'info', 'log_loading_file', 'Loading: {path}', path=file_path)

            # Parse once before opening the standardization preview. This also
            # guarantees malformed NEXUS/PHYLIP files cannot partially replace
            # the current table.
            taxons = loader(file_path)
            headers = [taxon.name for taxon in taxons[:100]]

            if not headers:
                QMessageBox.warning(self, lang_manager.get('title_warning', 'Warning'),
                                    lang_manager.get('msg_no_sequences_in_file',
                                                     'No sequences found in file!'))
                return

            # Show standardization dialog
            config = StandardizationDialog.get_standardization_config(headers, self)

            if config is None:
                # User cancelled
                self._append_localized_log(
                    'info', 'log_load_cancelled', 'Load cancelled by user')
                return

            # Apply standardization
            taxons = self.file_service.apply_standardization(taxons, config)

            if not taxons:
                QMessageBox.warning(
                    self, lang_manager.get('title_warning', 'Warning'),
                    lang_manager.get('msg_no_valid_sequences'))
                return

            self.table_model.clear()
            self.table_model.add_taxons(taxons)

            self._clear_vcf_source()
            self._invalidate_derived_results()

            self._update_selected_count()
            self.data_tab.update_counts(total=len(taxons))

            self._append_localized_log(
                'success', 'log_loaded_sequence_format',
                'Loaded {count} sequences from {format}',
                count=len(taxons), format=file_format.upper())
            self._check_trait_completeness(taxons)
            self.switch_to_tab('data')

        except Exception as e:
            self._append_localized_log(
                'error', 'msg_load_failed', 'Failed to load file: {err}', err=str(e))
            QMessageBox.critical(self, lang_manager.get('title_error', 'Error'),
                                 lang_manager.get('msg_load_failed',
                                                  'Failed to load file: {err}').format(err=str(e)))

    def _export_sequences(self):
        """Export all table sequences as FASTA, NEXUS, PHYLIP, or VCF."""
        if self.table_model.rowCount() < 1:
            QMessageBox.warning(self, lang_manager.get('title_warning', 'Warning'),
                                lang_manager.get('msg_no_export', 'No data to export!'))
            return

        formats = [
            ('fasta', 'filter_export_fasta', 'FASTA Files (*.fasta *.fas *.fa)',
             '.fasta', ('.fasta', '.fas', '.fa')),
            ('nexus', 'filter_export_nexus', 'NEXUS Files (*.nex *.nexus *.nxs)',
             '.nex', ('.nex', '.nexus', '.nxs')),
            ('phylip', 'filter_export_phylip', 'PHYLIP Files (*.phy *.phylip)',
             '.phy', ('.phy', '.phylip')),
            ('vcf', 'filter_export_vcf', 'VCF Files (*.vcf)',
             '.vcf', ('.vcf',)),
        ]
        filters = [lang_manager.get(key, default) for _, key, default, _, _ in formats]
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            lang_manager.get('dlg_export_sequences_title', 'Export Sequences'),
            "",
            ";;".join(filters),
        )
        if not file_path:
            return

        selected_index = filters.index(selected_filter) if selected_filter in filters else 0
        file_format, _, _, extension, accepted = formats[selected_index]
        if not file_path.lower().endswith(accepted):
            file_path += extension

        try:
            output_files = self.file_service.export_sequences(
                file_path, self.table_model.get_all_taxons(), file_format)
            paths = "\n".join(output_files)
            self._append_localized_log(
                'success', 'log_exported_sequences',
                'Sequences exported to: {path}', path=paths)
            QMessageBox.information(
                self, lang_manager.get('title_success', 'Success'),
                lang_manager.get(
                    'msg_export_files_complete',
                    'Export completed:\n{paths}').format(paths=paths))
        except Exception as e:
            self._show_export_error(e)

    def _export_traits(self):
        """Export table traits independently as a CSV file."""
        if self.table_model.rowCount() < 1:
            QMessageBox.warning(
                self, lang_manager.get('title_warning', 'Warning'),
                lang_manager.get('msg_no_export', 'No data to export!'))
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            lang_manager.get('dlg_export_traits_title', 'Export Traits'),
            "",
            lang_manager.get('filter_export_traits', 'CSV Files (*.csv)'),
        )
        if not file_path:
            return
        if not file_path.lower().endswith('.csv'):
            file_path += '.csv'
        try:
            self.file_service.export_traits(
                file_path, self.table_model.get_all_taxons())
            self._append_localized_log(
                'success', 'log_exported_traits',
                'Traits exported to: {path}', path=file_path)
            QMessageBox.information(
                self, lang_manager.get('title_success', 'Success'),
                lang_manager.get(
                    'msg_export_files_complete',
                    'Export completed:\n{paths}').format(paths=file_path))
        except Exception as e:
            self._show_export_error(e)

    def _show_export_error(self, error: Exception) -> None:
        self._append_localized_log(
            'error', 'msg_export_failed',
            'Failed to export: {err}', err=str(error))
        QMessageBox.critical(
            self, lang_manager.get('title_error', 'Error'),
            lang_manager.get(
                'msg_export_failed',
                'Failed to export: {err}').format(err=str(error)))

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
        import csv

        # Step 1 – Sequence must be loaded first
        if self.table_model.rowCount() < 1:
            QMessageBox.warning(self, lang_manager.get('title_warning', 'Warning'),
                                lang_manager.get('msg_load_seq_first',
                                                 'Please load a sequence file first before importing traits!'))
            return

        # Step 2 – Choose CSV file
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            lang_manager.get('dlg_load_csv_title', 'Load CSV Traits File'),
            "",
            lang_manager.get('filter_csv', 'CSV Files (*.csv);;All Files (*.*)')
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
                QMessageBox.warning(self, lang_manager.get('title_warning', 'Warning'),
                                    lang_manager.get('msg_csv_empty', 'The CSV file is empty!'))
                return

            headers = all_rows[0]
            data_rows = all_rows[1:]

            if not headers:
                QMessageBox.warning(self, lang_manager.get('title_warning', 'Warning'),
                                    lang_manager.get('msg_csv_no_header',
                                                     'The CSV file has no header row!'))
                return

            if not data_rows:
                QMessageBox.warning(self, lang_manager.get('title_warning', 'Warning'),
                                    lang_manager.get('msg_csv_no_data',
                                                     'The CSV file contains no data rows!'))
                return

            # Show at most 5 rows in the preview
            preview_rows = data_rows[:5]

            mapping = CsvTraitsImportDialog.get_column_mapping(headers, preview_rows, self)
            if mapping is None:
                self._append_localized_log(
                    'info', 'log_csv_cancelled', 'CSV trait import cancelled by user')
                return

            name_col = mapping['name_col']
            discrete_col = mapping['discrete_col']
            continuous_col = mapping['continuous_col']

            if name_col is None:
                QMessageBox.critical(self, lang_manager.get('title_error', 'Error'),
                                     lang_manager.get('msg_csv_need_name_col',
                                                      'Sequence Name column must be selected!'))
                return

            csv_sequence_names = [
                row[name_col].strip()
                for row in data_rows
                if name_col < len(row) and row[name_col].strip()
            ]
            duplicate_csv_names = find_duplicates(csv_sequence_names)
            if duplicate_csv_names:
                QMessageBox.critical(
                    self,
                    lang_manager.get('title_duplicate_names', 'Duplicate Names'),
                    lang_manager.get(
                        'msg_csv_duplicate_names',
                        'The CSV contains duplicate sequence names:\n{names}'
                    ).format(names="\n".join(f"  • {n}" for n in duplicate_csv_names)),
                )
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
            loaded_name_list = [
                self.table_model.get_taxon(i).name
                for i in range(self.table_model.rowCount())
            ]
            duplicate_loaded_names = find_duplicates(loaded_name_list)
            if duplicate_loaded_names:
                QMessageBox.critical(
                    self,
                    lang_manager.get('title_duplicate_names', 'Duplicate Names'),
                    lang_manager.get('msg_data_duplicate_names').format(
                        names="\n".join(f"  • {name}" for name in duplicate_loaded_names)
                    ),
                )
                return
            loaded_names = set(loaded_name_list)
            csv_names = set(csv_trait_map.keys())

            missing_in_csv = loaded_names - csv_names  # loaded but not in CSV
            extra_in_csv = csv_names - loaded_names  # in CSV but not loaded

            if missing_in_csv or extra_in_csv:
                msg_lines = [lang_manager.get('msg_name_mismatch_header',
                                              'Sequence name mismatch detected:\n')]
                if missing_in_csv:
                    msg_lines.append(lang_manager.get('msg_name_mismatch_missing',
                                                      'Sequences in data table NOT found in CSV:'))
                    for n in sorted(missing_in_csv):
                        msg_lines.append(f"  • {n}")
                if extra_in_csv:
                    if missing_in_csv:
                        msg_lines.append("")
                    msg_lines.append(lang_manager.get('msg_name_mismatch_extra',
                                                      'Names in CSV NOT found in data table:'))
                    for n in sorted(extra_in_csv):
                        msg_lines.append(f"  • {n}")
                QMessageBox.critical(self, lang_manager.get('title_name_mismatch',
                                                            'Name Mismatch Error'),
                                     "\n".join(msg_lines))
                return

            # Step 6 – Ask whether to overwrite if traits already exist
            has_existing_discrete = any(
                self.table_model.get_taxon(i).discrete_traits.strip()
                for i in range(self.table_model.rowCount())
            )
            has_existing_continuous = any(
                has_meaningful_continuous_trait(
                    self.table_model.get_taxon(i).continuous_traits)
                for i in range(self.table_model.rowCount())
            )
            if has_existing_discrete or has_existing_continuous:
                reply = QMessageBox.question(
                    self,
                    lang_manager.get('title_update_traits', 'Update Traits'),
                    lang_manager.get('msg_traits_overwrite',
                                     'Trait data already exists for some sequences.\n'
                                     'Do you want to overwrite the existing traits with the CSV data?'),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self._append_localized_log(
                        'info', 'log_csv_existing_kept',
                        'CSV trait import cancelled; existing traits kept')
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

            self._append_localized_log(
                'success', 'log_csv_imported',
                'Traits imported from CSV: {count} sequences updated', count=updated)
            self._check_trait_completeness(self.table_model.get_all_taxons())
            self.switch_to_tab('data')

        except Exception as e:
            self._append_localized_log(
                'error', 'msg_csv_import_failed',
                'Failed to import CSV traits:\n{err}', err=str(e))
            QMessageBox.critical(self, lang_manager.get('title_error', 'Error'),
                                 lang_manager.get('msg_csv_import_failed',
                                                  'Failed to import CSV traits:\n{err}').format(err=str(e)))

    # ==================== Data Selection ====================

    def _select_all(self):
        """Select all taxons."""
        self.table_model.select_all()

    def _deselect_all(self):
        """Deselect all taxons."""
        self.table_model.deselect_all()

    def _update_selected_count(self):
        """Update selected count display."""
        count = self.table_model.get_selected_count()
        total = self.table_model.rowCount()
        self.data_tab.update_counts(selected=count, total=total)

    # ==================== Interpretation Analysis ====================

    def _aligned_interpretation_dataset(self) -> AnalysisDataset:
        """Snapshot selected aligned data, using the current result alignment if needed."""
        selected = self.table_model.get_selected_taxons()
        if not selected:
            raise AnalysisDataError(lang_manager.get(
                'msg_select_seq_first', 'Please select sequences first!'))
        try:
            return AnalysisDataset.from_taxons(
                selected, trait_name='group', source_label='current data table')
        except AnalysisDataError as exc:
            if 'equal length' not in str(exc):
                raise

        aligned_path = os.path.join(
            self.get_output_path(), f"{self.get_project_prefix()}_aln.fasta")
        if (
            self._aligned_result_generation != self._input_generation
            or not os.path.isfile(aligned_path)
        ):
            raise AnalysisDataError(lang_manager.get(
                'msg_interpretation_aligned_required',
                'This analysis requires equal-length aligned sequences.'))
        aligned = {record.name: record.sequence for record in read_fasta(aligned_path)}
        missing = [taxon.name for taxon in selected if taxon.name not in aligned]
        if missing:
            raise AnalysisDataError(lang_manager.get(
                'msg_interpretation_aligned_required',
                'This analysis requires equal-length aligned sequences.'))
        records = [{
            'name': taxon.name,
            'sequence': aligned[taxon.name],
            'discrete_traits': taxon.discrete_traits,
            'continuous_traits': taxon.continuous_traits,
        } for taxon in selected]
        return AnalysisDataset.from_records(
            records, default_trait_name='group', source_label=aligned_path)

    def _analyze_diversity_qc(self):
        try:
            dataset = self._aligned_interpretation_dataset()
        except (AnalysisDataError, OSError, FormatConversionError) as exc:
            QMessageBox.warning(
                self, lang_manager.get('title_warning', 'Warning'), str(exc))
            return
        options = InterpretationOptionsDialog.get_config(
            'diversity', dataset.alignment_length, self)
        if options is not None:
            self._start_interpretation('diversity', dataset, options)

    def _analyze_distance_pcoa(self):
        try:
            dataset = self._aligned_interpretation_dataset()
        except (AnalysisDataError, OSError, FormatConversionError) as exc:
            QMessageBox.warning(
                self, lang_manager.get('title_warning', 'Warning'), str(exc))
            return
        options = InterpretationOptionsDialog.get_config(
            'distance', dataset.alignment_length, self)
        if options is not None:
            self._start_interpretation('distance', dataset, options)

    def _analyze_topology(self):
        gml_path = os.path.join(
            self.get_output_path(), f"{self.get_project_prefix()}.gml")
        if (
            self._network_result_generation != self._input_generation
            or not os.path.isfile(gml_path)
        ):
            self._append_localized_log(
                'warning', 'msg_topology_gml_required',
                'The current project has no network GML; select an existing file.')
            gml_path, _ = QFileDialog.getOpenFileName(
                self,
                lang_manager.get('dlg_select_gml', 'Select Haplotype Network GML'),
                self.get_output_path(),
                lang_manager.get(
                    'filter_gml', 'GML Network Files (*.gml);;All Files (*.*)'),
            )
        if gml_path:
            self._start_interpretation('topology', gml_path, {})

    def _start_interpretation(self, kind: str, payload, options: dict) -> None:
        self._stop_worker(self.interpretation_worker)
        name = self._interpretation_name(kind)
        self._append_localized_log(
            'info', 'log_interpretation_started', 'Starting {analysis}.',
            analysis=name)
        self.set_status_key('status_interpreting', 'Running interpretation analysis...')
        self.set_progress(0)
        worker = InterpretationWorker(kind, payload, options)
        worker.output_path = self.get_output_path()
        worker.prefix = self.get_project_prefix()
        self.interpretation_worker = worker
        worker.finished.connect(
            lambda outcome, source=worker: self._on_interpretation_finished(source, outcome))
        self._start_active_worker(worker)

    def _on_interpretation_finished(self, worker: InterpretationWorker,
                                    outcome: dict) -> None:
        if worker is not self.interpretation_worker:
            return
        self._clear_active_worker(worker)
        kind = outcome.get('kind', 'interpretation')
        name = self._interpretation_name(kind)
        if outcome.get('cancelled'):
            self.set_status_key('status_ready', 'Ready')
            self.set_progress(0)
            self._append_localized_log(
                'warning', 'log_cancel_requested', 'Analysis was cancelled.')
            return
        if not outcome.get('success'):
            error = outcome.get('error') or 'Unknown error'
            self.set_status_key('status_ready', 'Ready')
            self.set_progress(0)
            self._append_localized_log(
                'error', 'log_interpretation_failed', '{analysis} failed: {error}',
                analysis=name, error=error)
            QMessageBox.critical(
                self, lang_manager.get('title_error', 'Error'),
                lang_manager.get(
                    'msg_interpretation_failed',
                    'Interpretation analysis failed: {error}').format(error=error))
            return

        result = outcome['result']
        self._last_interpretation_kind = kind
        self._last_interpretation_result = result
        report = self._build_interpretation_report(kind, result)
        self.show_interpretation_tab(report)
        try:
            output_file = self._export_interpretation_result(
                kind, result, output_path=worker.output_path, prefix=worker.prefix)
        except OSError as exc:
            output_file = lang_manager.get('report_not_saved', 'not saved')
            self.log_tab.append_warning(str(exc))
        self.set_status_key('status_complete', 'Complete')
        self.set_progress(0)
        self._append_localized_log(
            'success', 'log_interpretation_complete',
            '{analysis} completed; results saved to {path}.',
            analysis=name, path=output_file)

    def _interpretation_name(self, kind: str) -> str:
        keys = {
            'diversity': ('analysis_diversity_title', 'Sequence Quality and Genetic Diversity'),
            'distance': ('analysis_distance_title', 'Genetic Distance and PCoA'),
            'topology': ('analysis_topology_title', 'Haplotype Network Topology Metrics'),
        }
        key, default = keys.get(kind, ('tab_interpretation', 'Interpretation'))
        return lang_manager.get(key, default)

    def _build_interpretation_report(self, kind: str, result) -> dict:
        if kind == 'diversity':
            return self._build_diversity_report(result)
        if kind == 'distance':
            return self._build_distance_report(result)
        if kind == 'topology':
            return self._build_topology_report(result)
        raise ValueError(f'Unsupported interpretation report: {kind}')

    def _report_shell(self, title_key: str, description_key: str) -> dict:
        return {
            'title': lang_manager.get(title_key),
            'description': lang_manager.get(description_key),
            'overview_title': lang_manager.get('report_overview', 'Overview'),
            'summary_columns': [
                lang_manager.get('report_metric', 'Metric'),
                lang_manager.get('report_value', 'Value'),
            ],
            'warnings_title': lang_manager.get('report_warnings', 'Warnings'),
            'notes_title': lang_manager.get('report_notes', 'Interpretation notes'),
        }

    def _build_diversity_report(self, result) -> dict:
        tr = self._bi
        quality = result.quality
        overall = result.overall
        report = self._report_shell(
            'analysis_diversity_title', 'analysis_diversity_description')
        report['summary'] = [
            (tr('样本数', 'Samples'), quality.sample_count),
            (tr('比对长度', 'Alignment length'), quality.alignment_length),
            (tr('缺失数据策略', 'Missing-data policy'), result.missing_policy.value),
            (tr('总体缺失率', 'Overall missing rate'), quality.total_missing_rate),
            (tr('有效位点', 'Effective sites'), quality.effective_site_count),
            (tr('变异位点', 'Variable sites'), quality.variable_site_count),
            (tr('简约信息位点', 'Parsimony-informative sites'),
             quality.parsimony_informative_site_count),
            (tr('单倍型丰富度', 'Haplotype richness'), overall.haplotype_richness),
            (tr('单倍型多样性 Hd', 'Haplotype diversity (Hd)'), overall.hd),
            (tr('核苷酸多样性 π', 'Nucleotide diversity (pi)'), overall.pi),
            (tr("Watterson's θW", "Watterson's theta W"), overall.theta_w),
        ]
        group_rows = [(
            group.label, group.sample_count, group.callable_site_count,
            group.segregating_site_count, group.haplotype_richness,
            group.private_haplotype_count, group.hd, group.pi, group.theta_w,
            group.private_haplotypes,
        ) for group in result.groups]
        sample_rows = [(
            sample.sample_name, sample.missing_count, sample.missing_rate,
            sample.gap_count, sample.unknown_count, sample.ambiguity_count,
        ) for sample in quality.samples[:1000]]
        informative_sites = [
            site for site in quality.sites if site.missing_count or site.variable
        ]
        site_rows = [(
            site.position, site.callable_count, site.missing_count,
            site.missing_rate, '; '.join(f'{base}:{count}' for base, count in site.alleles),
            site.variable, site.parsimony_informative,
        ) for site in informative_sites[:1000]]
        report['tables'] = [{
            'title': tr('分组多样性', 'Group diversity'),
            'columns': [tr('分组', 'Group'), tr('样本数', 'N'),
                        tr('有效位点', 'Callable sites'), tr('分离位点', 'S'),
                        tr('单倍型数', 'Haplotypes'), tr('私有单倍型数', 'Private'),
                        'Hd', 'π', 'θW', tr('私有单倍型', 'Private haplotypes')],
            'rows': group_rows,
        }, {
            'title': tr('样本质量', 'Sample quality'),
            'columns': [tr('样本', 'Sample'), tr('缺失数', 'Missing'),
                        tr('缺失率', 'Missing rate'), tr('缺口', 'Gaps'),
                        tr('未知', 'Unknown'), tr('模糊', 'Ambiguous')],
            'rows': sample_rows,
        }, {
            'title': tr('异常与变异位点', 'Missing and variable sites'),
            'columns': [tr('位置', 'Position'), tr('有效样本', 'Callable'),
                        tr('缺失数', 'Missing'), tr('缺失率', 'Missing rate'),
                        tr('等位状态', 'Alleles'), tr('变异', 'Variable'),
                        tr('简约信息', 'Parsimony informative')],
            'rows': site_rows,
        }]
        warnings = [
            self._localized_interpretation_message(value)
            for value in (*result.warnings, *overall.warnings)
        ]
        for group in result.groups:
            warnings.extend(
                f'{group.label}: {self._localized_interpretation_message(value)}'
                for value in group.warnings)
        if len(quality.samples) > len(sample_rows) or len(informative_sites) > len(site_rows):
            warnings.append(tr(
                '界面表格仅显示前 1000 行；JSON 文件保留完整结果。',
                'The UI shows the first 1,000 rows; the JSON file retains the complete result.'))
        report['warnings'] = warnings
        report['notes'] = [
            tr('缺口、N、? 和 IUPAC 模糊状态不作为确定等位基因。',
               'Gaps, N, ?, and IUPAC ambiguity states are not treated as called alleles.'),
            tr('Tajima’s D 未自动计算，因为可靠解释需要额外的人口历史与零模型假设。',
               "Tajima's D is not calculated automatically because defensible interpretation requires demographic and null-model assumptions."),
            tr('组间数值比较应同时考虑样本量与缺失率。',
               'Compare groups together with their sample sizes and missing-data rates.'),
        ]
        return report

    def _build_distance_report(self, result) -> dict:
        tr = self._bi
        report = self._report_shell(
            'analysis_distance_title', 'analysis_distance_description')
        pair_count = len(result.labels) * (len(result.labels) - 1) // 2
        unavailable = sum(
            not math.isfinite(result.distance_matrix[i][j])
            for i in range(len(result.labels)) for j in range(i + 1, len(result.labels)))
        report['summary'] = [
            (tr('序列数', 'Sequences'), len(result.labels)),
            (tr('比对长度', 'Alignment length'), result.alignment_length),
            (tr('序列对数量', 'Pairwise comparisons'), pair_count),
            (tr('覆盖不足的序列对', 'Unavailable low-coverage pairs'), unavailable),
            (tr('最少可比较位点', 'Minimum comparable sites'),
             result.minimum_comparable_sites),
            (tr('最低可比较覆盖率', 'Minimum comparable coverage'),
             result.minimum_coverage),
            (tr('PCoA 轴数', 'PCoA axes returned'), result.pcoa.axis_count),
            (tr('负特征值比例', 'Negative eigenvalue ratio'),
             result.pcoa.negative_eigenvalue_ratio),
        ]
        report['summary'].extend((
            tr(f'PCoA 轴 {index + 1} 解释比例',
               f'PCoA axis {index + 1} positive-eigenvalue proportion'), ratio)
            for index, ratio in enumerate(
                result.pcoa.explained_variance_ratio[:result.pcoa.axis_count]))
        display_count = min(len(result.labels), 100)
        labels = result.labels[:display_count]
        distance_rows = [
            (result.labels[index],) + result.distance_matrix[index][:display_count]
            for index in range(display_count)]
        site_rows = [
            (result.labels[index],) + result.comparable_sites[index][:display_count]
            for index in range(display_count)]
        coordinate_rows = [
            (result.labels[index],) + result.pcoa.coordinates[index]
            for index in range(len(result.labels))]
        report['tables'] = [{
            'title': tr('p-distance 矩阵', 'p-distance matrix'),
            'columns': [tr('样本', 'Sample')] + list(labels),
            'rows': distance_rows,
        }, {
            'title': tr('有效比较位点', 'Comparable sites'),
            'columns': [tr('样本', 'Sample')] + list(labels),
            'rows': site_rows,
        }]
        if result.pcoa.axis_count:
            report['tables'].append({
                'title': tr('PCoA 坐标', 'PCoA coordinates'),
                'columns': [tr('样本', 'Sample')] + [
                    tr(f'轴 {index + 1}', f'Axis {index + 1}')
                    for index in range(result.pcoa.axis_count)],
                'rows': coordinate_rows,
            })
        warnings = [
            self._localized_interpretation_message(value)
            for value in (*result.warnings, *result.pcoa.warnings)
        ]
        if display_count < len(result.labels):
            warnings.append(tr(
                '距离矩阵界面仅显示前 100 个样本；JSON 文件保留完整矩阵。',
                'The UI shows the first 100 samples in matrices; JSON retains all values.'))
        report['warnings'] = warnings
        report['notes'] = [
            tr('距离按序列对删除不可调用位点计算，并同时报告实际比较位点数。',
               'Distances use pairwise deletion and report the effective sites for every pair.'),
            tr('PCoA 基于经典多维尺度分析，不对缺失距离进行插补。',
               'PCoA uses classical multidimensional scaling and does not impute missing distances.'),
            tr('PCoA 聚类仅用于探索，不能单独证明群体、祖先或传播关系。',
               'PCoA proximity is exploratory and does not establish populations, ancestry, or transmission.'),
        ]
        return report

    def _build_topology_report(self, result) -> dict:
        tr = self._bi
        graph = result.graph
        node_rows = result.nodes[:5000]
        edge_rows = result.edges[:5000]
        report = self._report_shell(
            'analysis_topology_title', 'analysis_topology_description')
        report['summary'] = [
            (tr('节点数', 'Nodes'), graph.node_count),
            (tr('边数', 'Edges'), graph.edge_count),
            (tr('连通分量', 'Connected components'), graph.component_count),
            (tr('网络密度', 'Density'), graph.density),
            (tr('环秩', 'Cycle rank'), graph.cycle_rank),
            (tr('观测单倍型节点', 'Observed haplotype nodes'),
             graph.observed_node_count),
            (tr('中间节点', 'Intermediate nodes'), graph.intermediate_node_count),
            (tr('源网络有向', 'Source graph directed'), graph.source_directed),
            (tr('分析投影', 'Analysis projection'), graph.analysis_projection),
        ]
        report['tables'] = [{
            'title': tr('节点指标', 'Node metrics'),
            'columns': [tr('节点 ID', 'Node ID'), tr('度', 'Degree'),
                        tr('相邻突变距离和', 'Mutation-distance sum'),
                        tr('接近中心性', 'Closeness'),
                        tr('介数中心性', 'Betweenness'),
                        tr('分量', 'Component'), tr('割点', 'Articulation'),
                        tr('中间节点', 'Intermediate')],
            'rows': [(
                node.node_id, node.degree, node.mutation_distance_sum,
                node.closeness, node.betweenness, node.component,
                node.articulation_point, node.is_intermediate,
            ) for node in node_rows],
        }, {
            'title': tr('边指标', 'Edge metrics'),
            'columns': [tr('边编号', 'Edge'), tr('起点', 'Source'),
                        tr('终点', 'Target'), tr('突变距离', 'Mutation distance'),
                        tr('桥', 'Bridge'), tr('边介数', 'Edge betweenness')],
            'rows': [(
                edge.edge_index, edge.source, edge.target,
                edge.mutation_distance, edge.bridge, edge.betweenness,
            ) for edge in edge_rows],
        }]
        report['warnings'] = []
        if len(result.nodes) > len(node_rows) or len(result.edges) > len(edge_rows):
            report['warnings'].append(tr(
                '拓扑表格在界面中仅显示前 5000 行；JSON 文件保留完整结果。',
                'Topology tables show the first 5,000 rows in the UI; JSON retains the complete result.'))
        report['notes'] = [
            tr('突变数始终作为距离，不作为更强的连接权重。',
               'Mutation count is treated as distance, never as stronger connectivity.'),
            tr('中心性、割点和桥仅描述图结构，不能识别祖先、起源地或传播源。',
               result.interpretation_note),
        ]
        if graph.source_directed:
            report['notes'].append(tr(
                '源 GML 为有向网络；当前拓扑指标基于无向投影，方向信息仅作为来源记录保留。',
                'The source GML is directed; these metrics use an undirected projection and retain direction only as provenance.'))
        return report

    @staticmethod
    def _json_compatible(value):
        if is_dataclass(value):
            return MainForm._json_compatible(asdict(value))
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, dict):
            return {str(key): MainForm._json_compatible(item)
                    for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [MainForm._json_compatible(item) for item in value]
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value

    def _export_interpretation_result(self, kind: str, result, *,
                                      output_path: Optional[str] = None,
                                      prefix: Optional[str] = None) -> str:
        prefix = prefix or self.get_project_prefix() or 'project'
        if validate_project_prefix(prefix) is not None:
            prefix = 'project'
        output_path = output_path or self.get_output_path()
        os.makedirs(output_path, exist_ok=True)
        destination = os.path.join(output_path, f'{prefix}_{kind}_analysis.json')
        payload = self._json_compatible(result)
        if kind == 'diversity' and isinstance(payload, dict):
            dataset = result.dataset
            payload['dataset'] = {
                'sample_names': [sample.name for sample in dataset.samples],
                'sample_count': dataset.sample_count,
                'alignment_length': dataset.alignment_length,
                'source_label': dataset.source_label,
            }
        with open(destination, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
        return destination

    @staticmethod
    def _bi(chinese: str, english: str) -> str:
        return chinese if lang_manager.get_language() == 'cn' else english

    @staticmethod
    def _localized_interpretation_message(message: str) -> str:
        """Localize known computation warnings while retaining raw JSON provenance."""
        if lang_manager.get_language() != 'cn':
            return message
        exact = {
            'At least two samples are required for Hd, pi and theta_w':
                '计算 Hd、π 和 θW 至少需要两个样本。',
            'No sample pair has callable sites for nucleotide diversity':
                '没有任何样本对具有可用于核苷酸多样性的有效位点。',
            "No callable sites are available for Watterson's theta":
                '没有可用于计算 Watterson θW 的有效位点。',
            'No globally complete sites; haplotype metrics cannot distinguish samples':
                '没有全局完整位点，单倍型指标无法区分样本。',
            'Haplotype metrics use globally complete sites so missing patterns do not create haplotypes':
                '单倍型指标仅使用全局完整位点，避免缺失模式被误判为新单倍型。',
            'Pairwise pi values can use different callable sites for different sample pairs':
                '成对删除时，不同样本对的 π 可能基于不同的有效位点集。',
            'PCoA requires at least two sequences; no axes were returned.':
                'PCoA 至少需要两条序列，因此未返回坐标轴。',
            'PCoA was not calculated because one or more pairwise distances are unavailable (NaN). Review comparable-site coverage or use a complete subset; missing distances were not imputed.':
                '由于存在不可用的成对距离（NaN），未计算 PCoA。请检查有效位点覆盖率或使用完整子集；程序未对缺失距离进行插补。',
            'The PCoA eigensolver reached its iteration limit; coordinates may be numerically approximate.':
                'PCoA 特征求解器已达迭代上限，坐标可能为数值近似。',
            'All samples have zero or numerically negligible separation; no positive PCoA axis was available.':
                '所有样本的分离均为零或数值上可忽略，没有可用的正特征值 PCoA 轴。',
        }
        if message in exact:
            return exact[message]
        if message.startswith("Discrete trait '"):
            return "离散性状可用分组少于两组。"
        if 'sequence pair(s) had fewer than' in message:
            details = message.split(': ', 1)
            count = message.split(' ', 1)[0]
            suffix = f'：{details[1]}' if len(details) == 2 else ''
            return f'{count} 对序列未达有效位点阈值，距离记为 NaN{suffix}'
        if message.startswith('Unrecognised sequence symbols were treated as missing:'):
            symbols = message.split(':', 1)[1]
            return f'未识别的序列字符已按缺失处理：{symbols.strip()}'
        if message.startswith('PCoA was skipped for'):
            return '样本数超过无第三方依赖求解器的默认上限，已跳过 PCoA。'
        if message.startswith('Negative eigenvalues account for'):
            ratio = message.split('account for', 1)[1].split('of', 1)[0].strip()
            return f'负特征值占特征谱绝对值的 {ratio}，表明距离结构不完全符合欧氏空间。'
        return message

    def _selected_taxons_for_analysis(self) -> Optional[list]:
        """Validate and return the current analysis selection.

        Network construction, standalone alignment, and haplotype calculation
        share the same input requirements. Keeping the checks here prevents the
        three entry points from drifting into subtly different behaviour.
        """
        if self.table_model.rowCount() < 1:
            QMessageBox.warning(
                self, lang_manager.get('title_warning', 'Warning'),
                lang_manager.get('msg_load_data_first', 'Please load data first!'))
            return None

        selected_records = self.table_model.get_selected_taxons()
        if not selected_records:
            QMessageBox.warning(
                self, lang_manager.get('title_warning', 'Warning'),
                lang_manager.get('msg_select_seq_first', 'Please select sequences first!'))
            return None

        issue = validate_taxons(selected_records)
        if issue is not None:
            QMessageBox.critical(
                self, lang_manager.get('title_validation_error', 'Validation Error'),
                self._format_validation_issue(issue))
            return None
        # Workers must not retain references to editable table rows. A snapshot
        # keeps names, sequences, and traits consistent for the entire run.
        return [TaxonData.from_dict(taxon.to_dict()) for taxon in selected_records]

    def _analysis_output_target(self) -> Optional[tuple]:
        """Validate and return the output directory and project prefix."""
        output_path = self.get_output_path()
        if not output_path:
            QMessageBox.warning(
                self, lang_manager.get('title_warning', 'Warning'),
                lang_manager.get(
                    'msg_set_output_first', 'Please set output directory first!'))
            return None

        prefix = self.get_project_prefix()
        prefix_issue = validate_project_prefix(prefix)
        if prefix_issue is not None:
            QMessageBox.warning(
                self, lang_manager.get('title_warning', 'Warning'),
                self._format_validation_issue(prefix_issue))
            return None
        return output_path, prefix

    # ==================== Network Analysis ====================

    def _build_haplotype_network(self):
        """Show algorithm/parameter dialog, then run the selected network analysis."""
        selected_names = [
            taxon.name for taxon in self.table_model.get_selected_taxons()
        ]
        config = HaplotypeNetworkDialog.get_network_config(
            self, sample_names=selected_names,
            native_mcan_vcf=self._current_mcan_vcf_input() is not None,
        )
        if config is None:
            return
        self._run_network_analysis(config.algorithm, extra_args=config.to_extra_args())

    def _run_network_analysis(self, network_type: str, extra_args: list = None):
        """Run haplotype network analysis."""
        selected = self._selected_taxons_for_analysis()
        if selected is None:
            return
        output_target = self._analysis_output_target()
        if output_target is None:
            return
        output_path, prefix = output_target

        # Warn if selected data lacks traits that affect visualization
        has_discrete = any(t.discrete_traits.strip() for t in selected)
        has_continuous = any(
            has_meaningful_continuous_trait(t.continuous_traits)
            for t in selected
        )
        if not has_discrete:
            self._append_localized_log(
                'warning', 'log_no_discrete_selected',
                'Selected data has no discrete traits; the network will use the Default group.')
        if not has_continuous:
            self._append_localized_log(
                'info', 'log_no_continuous_selected',
                'Selected data has no valid continuous traits; continuous-trait visualization is unavailable.')

        # Clear any leftover pending JS before showing the waiting state. A
        # new page generation also invalidates delayed callbacks from a prior
        # network load.
        self._network_view_generation += 1
        self._pending_js = None
        self._pending_js_generation = None

        self.switch_to_tab('network')
        self.show_waiting_page()

        self._append_localized_log(
            'info', 'log_starting_network', 'Starting {algorithm} network analysis…',
            algorithm=network_type)
        self._append_localized_log('info', 'log_project', 'Project: {prefix}', prefix=prefix)
        self._append_localized_log(
            'info', 'log_output_directory', 'Output directory: {path}', path=output_path)
        self.set_status_key('status_analyzing', 'Analyzing...')

        self._stop_worker(self.analysis_worker)
        mcan_vcf_input = (
            self._current_mcan_vcf_input() if network_type == 'mcan' else None
        )
        if network_type == 'mcan' and self._mcan_vcf_input is not None and mcan_vcf_input is None:
            self._append_localized_log(
                'warning', 'log_vcf_source_modified',
                'VCF-derived sequence names or sequences were modified; '
                'McAN will use the current aligned table instead of the original VCF.')
        worker = AnalysisWorker(
            self.analysis_service, network_type, selected, output_path, prefix,
            extra_args=extra_args or [],
            mcan_vcf_input=mcan_vcf_input,
        )
        worker.input_generation = self._input_generation
        worker.network_view_generation = self._network_view_generation
        self.analysis_worker = worker
        worker.progress.connect(self.set_progress)
        worker.log.connect(self.log_tab.append_info)
        worker.finished.connect(
            lambda result, source=worker: self._on_analysis_finished(source, result))
        self._start_active_worker(worker)

    def _on_analysis_finished(self, worker: AnalysisWorker, result: AnalysisResult):
        """Handle network-analysis completion.

        The Network page is rendered first (via tcsBU's loadGraph/... calls
        injected into index.html). The Alignment and Haplotype tabs are then
        populated by independent background loaders — neither blocks the
        Network view nor each other.
        """
        index_html = os.path.join(self.current_directory, "static", "tcsbu", "index.html")

        if worker is not self.analysis_worker:
            return
        self._clear_active_worker(worker)

        if result.cancelled:
            self._append_localized_log(
                'warning', 'log_analysis_cancelled', 'Analysis cancelled.')
            if os.path.isfile(index_html):
                self.web_view_main.setUrl(QUrl.fromLocalFile(index_html))
        elif result.success:
            self._append_localized_log(
                'success', 'log_analysis_completed', 'Analysis completed.')
            js_file = os.path.join(result.output_path, f"{result.prefix}.js")
            if os.path.isfile(js_file):
                self._pending_js = self._build_network_js_injection(
                    js_file, result.has_continuous_traits
                )
                self._pending_js_generation = worker.network_view_generation
                self._append_localized_log(
                    'info', 'log_loading_visualization', 'Loading network visualization…')
            # Reload index.html to reset tcsBU state, then inject data via loadFinished handler.
            if os.path.isfile(index_html):
                self.web_view_main.setUrl(QUrl.fromLocalFile(index_html))
            self.switch_to_tab('network')
            if worker.input_generation == self._input_generation:
                self._network_result_generation = worker.input_generation
        else:
            self._append_localized_log(
                'error', 'log_analysis_failed', 'Analysis failed: {error}',
                error=result.error_message)
            QMessageBox.critical(self, lang_manager.get('title_error', 'Error'),
                                 lang_manager.get('msg_analysis_failed',
                                                  'Analysis failed: {err}').format(err=result.error_message))
            # Return to index.html (reset state, no pending JS)
            if os.path.isfile(index_html):
                self.web_view_main.setUrl(QUrl.fromLocalFile(index_html))

        # Kick off Alignment tab population in the background (decoupled from
        # the Haplotype tab load below).
        if result.aligned_fasta:
            if (
                worker.input_generation == self._input_generation
                and os.path.isfile(result.aligned_fasta)
            ):
                self._aligned_result_generation = worker.input_generation
            self._load_alignment_tab_async(result.aligned_fasta)

        # Kick off Haplotype tab population in the background whenever
        # haplotype data was produced, regardless of whether downstream steps
        # (fastHaN, visualization) succeeded.
        if result.haplotype_ready:
            self._load_haplotype_tab_async(result.output_path, result.prefix)

        self.set_progress(0)
        self.set_status_key('status_ready', 'Ready')

    def _on_web_view_load_finished(self, ok: bool) -> None:
        """Inject pending network data JS after index.html finishes loading."""
        if self._pending_js is None:
            return
        generation = self._pending_js_generation
        if generation != self._network_view_generation:
            return
        if not ok:
            self._pending_js = None
            self._pending_js_generation = None
            self._append_localized_log(
                'warning', 'log_network_page_failed',
                'Network view page failed to load; visualization was not injected.')
            return
        # A waiting-page loadFinished signal can arrive after the result has
        # queued index.html. Probe for tcsBU instead of consuming the payload on
        # whichever navigation happens to finish first.
        self._try_inject_network_js(generation, attempts_remaining=20)

    def _try_inject_network_js(self, generation: int,
                               attempts_remaining: int) -> None:
        if (
            generation != self._network_view_generation
            or generation != self._pending_js_generation
            or self._pending_js is None
        ):
            return

        def on_probe(ready) -> None:
            if (
                generation != self._network_view_generation
                or generation != self._pending_js_generation
                or self._pending_js is None
            ):
                return
            if ready:
                js = self._pending_js
                self._pending_js = None
                self._pending_js_generation = None
                self.web_view_main.page().runJavaScript(js)
            elif attempts_remaining > 1:
                QTimer.singleShot(
                    100,
                    lambda: self._try_inject_network_js(
                        generation, attempts_remaining - 1),
                )
            else:
                self._append_localized_log(
                    'warning', 'log_network_page_failed',
                    'Network view page was not ready; visualization was not injected.')

        self.web_view_main.page().runJavaScript(
            "typeof window.loadGraph === 'function'", on_probe)

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
        selected = self._selected_taxons_for_analysis()
        if selected is None:
            return

        config = SequenceAlignmentDialog.get_alignment_config(self)
        if config is None:
            return

        output_target = self._analysis_output_target()
        if output_target is None:
            return
        output_path, prefix = output_target

        tool_label = "MAFFT" if config.tool == "mafft" else "MUSCLE"
        self._append_localized_log(
            'info', 'log_starting_alignment',
            'Starting {tool} alignment for {count} sequences…',
            tool=tool_label, count=len(selected))
        self.set_status_key('status_aligning', 'Aligning...')

        self._stop_worker(self.alignment_worker)
        worker = AlignmentWorker(
            self.analysis_service, selected, output_path, prefix, config)
        worker.input_generation = self._input_generation
        self.alignment_worker = worker
        worker.log.connect(self.log_tab.append_info)
        worker.finished.connect(
            lambda result, source=worker: self._on_alignment_finished(source, result))
        self._start_active_worker(worker)

    def _on_alignment_finished(self, worker: AlignmentWorker, result: AlignmentResult):
        """Handle standalone alignment completion."""
        if worker is not self.alignment_worker:
            return
        self._clear_active_worker(worker)
        self.set_status_key('status_ready', 'Ready')
        if result.cancelled:
            self._append_localized_log(
                'warning', 'log_alignment_cancelled', 'Alignment cancelled.')
        elif result.success:
            self._append_localized_log(
                'success', 'log_alignment_completed', 'Alignment completed → {path}',
                path=result.output_file)
            if result.displayable_fasta:
                if worker.input_generation == self._input_generation:
                    self._aligned_result_generation = worker.input_generation
                self._load_alignment_tab_async(result.output_file, focus=True)
            else:
                self._append_localized_log(
                    'info', 'msg_alignment_non_fasta_saved',
                    'The selected non-FASTA alignment was saved but cannot be previewed.')
        else:
            self._append_localized_log(
                'error', 'log_alignment_failed', 'Alignment failed: {error}',
                error=result.error_message)
            QMessageBox.critical(
                self, lang_manager.get('title_alignment_failed', 'Alignment Failed'),
                lang_manager.get('msg_alignment_failed',
                                 'Alignment failed:\n{err}').format(err=result.error_message))

    # ==================== Haplotype Calculation ====================

    def _calculate_haplotype(self):
        """Show MSA dialog, run alignment + haplotype calculation, display in Haplotype tab."""
        selected = self._selected_taxons_for_analysis()
        if selected is None:
            return

        config = SequenceAlignmentDialog.get_alignment_config(self)
        if config is None:
            return

        output_target = self._analysis_output_target()
        if output_target is None:
            return
        output_path, prefix = output_target

        tool_label = "MAFFT" if config.tool == "mafft" else "MUSCLE"
        self._append_localized_log(
            'info', 'log_starting_haplotype',
            'Starting haplotype calculation with {tool} for {count} sequences…',
            tool=tool_label, count=len(selected))
        self.set_status_key('status_haplotype', 'Calculating haplotypes...')

        self._stop_worker(self.haplotype_worker)
        worker = HaplotypeWorker(
            self.analysis_service, selected, output_path, prefix, config)
        worker.input_generation = self._input_generation
        self.haplotype_worker = worker
        worker.progress.connect(self.set_progress)
        worker.log.connect(self.log_tab.append_info)
        worker.finished.connect(
            lambda result, source=worker:
            self._on_haplotype_calculation_finished(source, result))
        self._start_active_worker(worker)

    def _on_haplotype_calculation_finished(self, worker: HaplotypeWorker,
                                           result: AnalysisResult):
        """Handle haplotype calculation completion.

        The Alignment and Haplotype tabs are populated by independent
        background loaders; the UI thread is not blocked while the files are
        parsed. The Haplotype tab takes focus (once loaded) because it is the
        primary output of this flow.
        """
        if worker is not self.haplotype_worker:
            return
        self._clear_active_worker(worker)
        self.set_progress(0)
        self.set_status_key('status_ready', 'Ready')

        if result.cancelled:
            self._append_localized_log(
                'warning', 'log_haplotype_cancelled',
                'Haplotype calculation cancelled.')
        elif result.success:
            self._append_localized_log(
                'success', 'log_haplotype_completed',
                'Haplotype calculation completed.')
        else:
            self._append_localized_log(
                'error', 'log_haplotype_failed',
                'Haplotype calculation failed: {error}', error=result.error_message)
            QMessageBox.critical(
                self, lang_manager.get('title_error', 'Error'),
                lang_manager.get('msg_hap_calc_failed',
                                 'Haplotype calculation failed:\n{err}').format(err=result.error_message))

        if result.aligned_fasta:
            if (
                worker.input_generation == self._input_generation
                and os.path.isfile(result.aligned_fasta)
            ):
                self._aligned_result_generation = worker.input_generation
            self._load_alignment_tab_async(result.aligned_fasta)

        if result.haplotype_ready:
            self._load_haplotype_tab_async(
                result.output_path, result.prefix, focus=True)

    # ==================== Async Tab Loaders ====================

    def _load_alignment_tab_async(self, fasta_path: str, focus: bool = False) -> None:
        """Parse the aligned FASTA off the UI thread, then populate the tab.

        ``focus`` controls whether the Alignment tab takes focus once loaded.
        When called from _on_analysis_finished the Network tab stays in front;
        the standalone alignment flow passes focus=True to surface the result.
        """
        if not fasta_path:
            return

        # Create the tab shell immediately so the user can see progress / the
        # empty table while parsing runs in the background.
        if self.alignment_tab is None:
            self.alignment_tab = AlignmentTabWidget()
            self.tab_widget.addTab(self.alignment_tab, self.TAB_NAMES['alignment'])

        self._append_localized_log(
            'info', 'log_loading_alignment_view',
            'Loading alignment view in background…')

        self._stop_worker(self.alignment_tab_loader)
        worker = AlignmentTabLoadWorker(fasta_path)
        self.alignment_tab_loader = worker
        worker.finished.connect(
            lambda data, source=worker, f=focus:
            self._on_alignment_tab_loaded(source, data, f)
        )
        worker.start()

    def _on_alignment_tab_loaded(self, worker: AlignmentTabLoadWorker,
                                 data: dict, focus: bool) -> None:
        """Apply pre-parsed alignment data to the Alignment tab (main thread)."""
        if worker is not self.alignment_tab_loader or self.alignment_tab is None:
            return
        self.alignment_tab.apply_data(data)
        if data.get("error"):
            self._append_localized_log(
                'warning', 'log_alignment_view_issue',
                'Alignment view loaded with issue: {error}', error=data.get('error'))
        else:
            self._append_localized_log(
                'info', 'log_alignment_view_ready', 'Alignment view ready.')
        if focus:
            self.switch_to_tab('alignment')

    def _load_haplotype_tab_async(self, output_path: str, prefix: str,
                                  focus: bool = False) -> None:
        """Parse haplotype result files off the UI thread, then populate the tab."""
        if not output_path or not prefix:
            return

        if self.haplotype_tab is None:
            self.haplotype_tab = HaplotypeTabWidget()
            self.tab_widget.addTab(self.haplotype_tab, self.TAB_NAMES['haplotype'])

        self._append_localized_log(
            'info', 'log_loading_haplotype_view',
            'Loading haplotype view in background…')

        self._stop_worker(self.haplotype_tab_loader)
        worker = HaplotypeTabLoadWorker(output_path, prefix)
        self.haplotype_tab_loader = worker
        worker.finished.connect(
            lambda data, source=worker, f=focus:
            self._on_haplotype_tab_loaded(source, data, f)
        )
        worker.start()

    def _on_haplotype_tab_loaded(self, worker: HaplotypeTabLoadWorker,
                                 data: dict, focus: bool) -> None:
        """Apply pre-parsed haplotype data to the Haplotype tab (main thread)."""
        if worker is not self.haplotype_tab_loader or self.haplotype_tab is None:
            return
        self.haplotype_tab.apply_data(data)
        errors = data.get('errors') or []
        if errors:
            self._append_localized_log(
                'warning', 'log_haplotype_view_issue',
                'Haplotype result is incomplete: {error}', error='; '.join(errors))
        else:
            self._append_localized_log(
                'info', 'log_haplotype_view_ready', 'Haplotype view ready.')
        if focus:
            self.switch_to_tab('haplotype')

    # ==================== Tools Functions ====================

    def _set_language(self, lang: str):
        """Set interface language."""
        lang_manager.set_language(lang)

        # Rebuild menu bar
        if self.menu_builder:
            self.menu_builder.rebuild()
            if self._active_worker is not None:
                self._set_analysis_actions_enabled(False)

        # Update window title
        self.setWindowTitle(lang_manager.get('window_title'))

        # Update tab names using widget references so indices don't need to be hard-coded.
        # Haplotype and Alignment tabs are included conditionally — they only exist
        # after the first successful analysis / alignment run.
        tab_keys = [
            (self.index_tab, 'tab_index'),
            (self.web_view_main, 'tab_network'),
            (self.data_tab, 'tab_data'),
            (self.haplotype_tab, 'tab_haplotype'),
            (self.alignment_tab, 'tab_alignment'),
            (self.interpretation_tab, 'tab_interpretation'),
        ]
        for widget, lang_key in tab_keys:
            if widget is None:
                continue
            idx = self.tab_widget.indexOf(widget)
            if idx >= 0:
                self.tab_widget.setTabText(idx, lang_manager.get(lang_key))

        # Update component texts
        self.update_chrome_language()
        self.table_model.update_language(
            [
                lang_manager.get('column_select'),
                lang_manager.get('column_id'),
                lang_manager.get('column_name'),
                lang_manager.get('column_sequence'),
                lang_manager.get('column_discrete_traits'),
                lang_manager.get('column_continuous_traits'),
            ],
            lang_manager.get('tooltip_sequence'),
        )
        if self.data_tab:
            self.data_tab.update_language()
        if self.output_panel:
            self.output_panel.update_language()
        if self.alignment_tab is not None:
            self.alignment_tab.update_language()
        if self.haplotype_tab is not None:
            self.haplotype_tab.update_language()
        if self.interpretation_tab is not None and self._last_interpretation_result is not None:
            self.interpretation_tab.set_report(self._build_interpretation_report(
                self._last_interpretation_kind, self._last_interpretation_result))
        if self.status_bar_widget:
            self.status_bar_widget.update_language()

        if self._active_worker is self.analysis_worker:
            self.show_waiting_page()

        self.output_panel.append_info(lang_manager.get('msg_language_changed'))


    # ==================== Help Functions ====================

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            lang_manager.get('title_about', 'About'),
            lang_manager.get(
                'msg_about_text',
                'Haplotype Network Analysis Tool\n\n'
                'Version: 2.0.0\n\n'
                'Python version rebuilt with PyQt6\n\n'
                'For haplotype network construction and analysis'
            )
        )

    def _show_tcsbu_help(self):
        """Open TCS-BU help PDF with the system default PDF viewer."""
        self._open_help_pdf('tcsbu.pdf', 'title_tcsbu_help', 'TCS-BU Help', 'TCS-BU')

    def _show_netst_help(self):
        """Open NetST help PDF with the system default PDF viewer."""
        self._open_help_pdf('netst.pdf', 'title_netst_help', 'NetST Help', 'NetST')

    def _open_help_pdf(self, filename: str, title_key: str,
                       default_title: str, document_name: str) -> None:
        """Open one bundled help document with consistent error handling."""
        pdf_path = os.path.join(self.current_directory, 'static', 'docs', filename)
        if not os.path.isfile(pdf_path):
            QMessageBox.warning(
                self, lang_manager.get(title_key, default_title),
                lang_manager.get(
                    'msg_pdf_not_found', '{name} help PDF not found:\n{path}'
                ).format(name=document_name, path=pdf_path))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))

    # ==================== Helper Methods ====================

    def _append_localized_log(self, level: str, key: str, default: str,
                              **values) -> None:
        message = lang_manager.get(key, default).format(**values)
        writer = getattr(self.log_tab, f'append_{level}', self.log_tab.append_info)
        writer(message)

    @staticmethod
    def _format_validation_issue(issue: ValidationIssue) -> str:
        details = issue.details
        if issue.code == 'empty_name':
            return lang_manager.get(
                'msg_validation_empty_name', 'Sequence name is empty (ID: {id}).'
            ).format(**details)
        if issue.code == 'empty_sequence':
            return lang_manager.get(
                'msg_validation_empty_sequence',
                'Sequence is empty (ID: {id}, name: {name}).'
            ).format(**details)
        if issue.code == 'invalid_name_whitespace':
            return lang_manager.get(
                'msg_validation_name_whitespace',
                'Sequence name contains whitespace (ID: {id}, name: {name}).'
            ).format(**details)
        if issue.code == 'invalid_continuous':
            return lang_manager.get(
                'msg_validation_invalid_continuous',
                "Continuous trait '{value}' is not numeric (ID: {id}, name: {name})."
            ).format(**details)
        if issue.code == 'duplicate_names':
            names = "\n".join(f"  • {name}" for name in details.get('names', []))
            return lang_manager.get(
                'msg_validation_duplicate_names',
                'Selected sequences contain duplicate names:\n{names}'
            ).format(names=names)
        if issue.code == 'invalid_project_name':
            return lang_manager.get(
                'msg_invalid_project_name',
                'Project name cannot contain path separators or be . or ...'
            )
        return lang_manager.get(
            'msg_enter_project_name', 'Please enter a project name!'
        )

    def _check_trait_completeness(self, taxons: list) -> None:
        """Check loaded taxons for missing discrete / continuous traits and warn the user."""
        has_discrete = any(t.discrete_traits.strip() for t in taxons)
        has_continuous = any(
            has_meaningful_continuous_trait(t.continuous_traits)
            for t in taxons
        )
        if not has_discrete:
            self._append_localized_log(
                'warning', 'log_no_discrete_traits',
                'Data has no discrete traits; group coloring is unavailable.')
        if not has_continuous:
            self._append_localized_log(
                'info', 'log_no_continuous_traits',
                'Data has no valid continuous traits; continuous-trait visualization is unavailable.')

    def closeEvent(self, event):
        """Ensure background workers are stopped before the window is destroyed."""
        for worker in (self.analysis_worker, self.alignment_worker,
                       self.haplotype_worker, self.interpretation_worker,
                       self.alignment_tab_loader,
                       self.haplotype_tab_loader):
            self._stop_worker(worker)
        super().closeEvent(event)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainForm()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
