"""
Haplotype Network Parameter Dialog

Allows the user to select a network algorithm (Original/Modified TCS, MSN, MJN,
McAN, or RMST) and configure the corresponding engine parameters.
"""

from dataclasses import dataclass
from typing import Optional, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QComboBox, QSpinBox, QCheckBox,
    QPushButton, QLabel, QFrame, QSizePolicy,
)

from .language_manager import lang_manager


# ---------------------------------------------------------------------------
# Data class returned by the dialog
# ---------------------------------------------------------------------------

@dataclass
class HaplotypeNetworkConfig:
    """Parameters chosen by the user for a network-engine run."""
    algorithm: str = "modified_tcs"
    threads: int = 8  # -t  (original_tcs, modified_tcs, mjn)
    ambiguous: int = 0  # -a  (original_tcs only) 0/1
    merge: int = 0  # -m  (original_tcs only) 0/1
    epsilon: int = 0  # -e  (msn, mjn)
    mcan_reference: str = ""
    mcan_exclude_ambiguous: bool = False
    rmst_method: str = "exact"
    rmst_iterations: int = 100
    rmst_seed: int = 42
    rmst_exclude_ambiguous: bool = True

    def to_extra_args(self) -> List[str]:
        """Build allow-listed engine arguments (excluding common input/output paths)."""
        args: List[str] = []
        alg = self.algorithm

        if alg == "mcan":
            args += ["--nthread", str(self.threads)]
            if self.mcan_reference:
                args += ["--netst-reference", self.mcan_reference]
            if self.mcan_exclude_ambiguous:
                args.append("--netst-exclude-ambiguous")
            return args

        if alg == "rmst":
            args += ["--method", self.rmst_method]
            if self.rmst_method == "randomized":
                args += ["--iterations", str(self.rmst_iterations)]
                args += ["--seed", str(self.rmst_seed)]
            if not self.rmst_exclude_ambiguous:
                args.append("--netst-include-ambiguous")
            return args

        if alg in ("original_tcs", "modified_tcs", "mjn"):
            args += ["-t", str(self.threads)]

        if alg == "original_tcs":
            args += ["-a", str(self.ambiguous)]
            args += ["-m", str(self.merge)]

        if alg in ("msn", "mjn"):
            args += ["-e", str(self.epsilon)]

        return args


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

# Algorithm display labels → NetST engine identifiers
_ALGORITHMS = [
    ("original_tcs", "alg_original_tcs", "Original TCS"),
    ("modified_tcs", "alg_modified_tcs", "Modified TCS"),
    ("msn", "alg_msn", "MSN (Minimum Spanning Network)"),
    ("mjn", "alg_mjn", "MJN (Median-Joining Network)"),
    ("rmst", "alg_rmst", "RMST (Randomized Minimum Spanning Tree)"),
    ("mcan", "alg_mcan", "McAN Minimum-cost Arborescence Network"),
]


class HaplotypeNetworkDialog(QDialog):
    """
    Modal dialog for configuring a haplotype-network engine run.

    Shows a combo-box to pick the algorithm and a dynamic parameter
    group that updates to match the selected algorithm's options.
    """

    def __init__(self, parent=None, sample_names=None,
                 native_mcan_vcf: bool = False):
        super().__init__(parent)
        self._sample_names = list(sample_names or [])
        self._native_mcan_vcf = native_mcan_vcf
        self._config = HaplotypeNetworkConfig()
        self._build_ui()
        self._on_algorithm_changed(0)  # initialise parameter visibility

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.setWindowTitle(lang_manager.get('dlg_haplonet_title', 'Build Haplotype Network'))
        self.setMinimumWidth(420)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        # ── Algorithm selector ──────────────────────────────────────────
        alg_group = QGroupBox(lang_manager.get('dlg_haplonet_algorithm', 'Algorithm'))
        alg_form = QFormLayout(alg_group)
        alg_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self._alg_combo = QComboBox()
        for _, text_key, fallback in _ALGORITHMS:
            self._alg_combo.addItem(lang_manager.get(text_key, fallback))
        self._alg_combo.currentIndexChanged.connect(self._on_algorithm_changed)
        alg_form.addRow(lang_manager.get('dlg_haplonet_select', 'Select:'), self._alg_combo)
        root.addWidget(alg_group)

        # ── Parameter group ─────────────────────────────────────────────
        self._param_group = QGroupBox(lang_manager.get('dlg_haplonet_params', 'Parameters'))
        self._param_layout = QFormLayout(self._param_group)
        self._param_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        root.addWidget(self._param_group)

        # Threads
        self._threads_label = QLabel(lang_manager.get('dlg_haplonet_threads', 'Threads (-t):'))
        self._threads_spin = QSpinBox()
        self._threads_spin.setRange(1, 256)
        self._threads_spin.setValue(8)
        self._threads_spin.setToolTip(lang_manager.get(
            'dlg_haplonet_threads_tip', 'Number of parallel threads (default: 8)'))

        # Ambiguous
        self._ambiguous_label = QLabel(lang_manager.get(
            'dlg_haplonet_ambiguous', 'Mask ambiguous bases (-a):'))
        self._ambiguous_check = QCheckBox()
        self._ambiguous_check.setChecked(False)
        self._ambiguous_check.setToolTip(lang_manager.get(
            'dlg_haplonet_ambiguous_tip',
            'Mark sites containing ambiguous bases: checked = mask (1), unchecked = ignore (0)'))

        # Merge
        self._merge_label = QLabel(lang_manager.get(
            'dlg_haplonet_merge', 'Merge intermediate vertices (-m):'))
        self._merge_check = QCheckBox()
        self._merge_check.setChecked(False)
        self._merge_check.setToolTip(lang_manager.get(
            'dlg_haplonet_merge_tip',
            'Merge intermediate vertices: checked = merge (1), unchecked = keep (0)'))

        # Epsilon
        self._epsilon_label = QLabel(lang_manager.get('dlg_haplonet_epsilon', 'Epsilon (-e):'))
        self._epsilon_spin = QSpinBox()
        self._epsilon_spin.setRange(0, 9999)
        self._epsilon_spin.setValue(0)
        self._epsilon_spin.setToolTip(lang_manager.get(
            'dlg_haplonet_epsilon_tip', 'Epsilon value for network construction (default: 0)'))

        # McAN reference sequence and ambiguity handling
        self._mcan_reference_label = QLabel(lang_manager.get(
            'dlg_haplonet_mcan_reference', 'Reference sequence:'))
        self._mcan_reference_combo = QComboBox()
        self._mcan_reference_combo.addItems(self._sample_names)
        self._mcan_reference_combo.setToolTip(lang_manager.get(
            'dlg_haplonet_mcan_reference_tip',
            'McAN describes mutations relative to this aligned sequence.'))

        self._mcan_ambiguous_label = QLabel(lang_manager.get(
            'dlg_haplonet_mcan_ambiguous', 'Exclude ambiguous sites:'))
        self._mcan_ambiguous_check = QCheckBox()
        self._mcan_ambiguous_check.setChecked(False)
        self._mcan_ambiguous_check.setToolTip(lang_manager.get(
            'dlg_haplonet_mcan_ambiguous_tip',
            'Exclude alignment columns containing bases other than A/C/G/T/U or gaps.'))

        # RMST mode, randomized sampling controls, and site filtering
        self._rmst_method_label = QLabel(lang_manager.get(
            'dlg_haplonet_rmst_method', 'RMST mode:'))
        self._rmst_method_combo = QComboBox()
        self._rmst_method_combo.addItem(lang_manager.get(
            'dlg_haplonet_rmst_exact', 'Exact MST-compatible edge union'), 'exact')
        self._rmst_method_combo.addItem(lang_manager.get(
            'dlg_haplonet_rmst_randomized', 'Randomized repeated MST'), 'randomized')
        self._rmst_method_combo.setToolTip(lang_manager.get(
            'dlg_haplonet_rmst_method_tip',
            'Exact mode is deterministic and recommended; randomized mode samples tie handling.'))
        self._rmst_method_combo.currentIndexChanged.connect(
            self._update_rmst_parameter_visibility)

        self._rmst_iterations_label = QLabel(lang_manager.get(
            'dlg_haplonet_rmst_iterations', 'Iterations:'))
        self._rmst_iterations_spin = QSpinBox()
        self._rmst_iterations_spin.setRange(1, 1000)
        self._rmst_iterations_spin.setValue(100)
        self._rmst_iterations_spin.setToolTip(lang_manager.get(
            'dlg_haplonet_rmst_iterations_tip',
            'Number of randomized minimum spanning trees to sample.'))

        self._rmst_seed_label = QLabel(lang_manager.get(
            'dlg_haplonet_rmst_seed', 'Random seed:'))
        self._rmst_seed_spin = QSpinBox()
        self._rmst_seed_spin.setRange(-2147483648, 2147483647)
        self._rmst_seed_spin.setValue(42)
        self._rmst_seed_spin.setToolTip(lang_manager.get(
            'dlg_haplonet_rmst_seed_tip',
            'Fixed seed for reproducible randomized results.'))

        self._rmst_ambiguous_label = QLabel(lang_manager.get(
            'dlg_haplonet_rmst_ambiguous', 'Exclude ambiguous sites:'))
        self._rmst_ambiguous_check = QCheckBox()
        self._rmst_ambiguous_check.setChecked(True)
        self._rmst_ambiguous_check.setToolTip(lang_manager.get(
            'dlg_haplonet_rmst_ambiguous_tip',
            'Exclude alignment columns containing symbols other than A/C/G/T/U or gaps.'))

        # Add all rows; visibility controlled in _on_algorithm_changed
        self._param_layout.addRow(self._threads_label, self._threads_spin)
        self._param_layout.addRow(self._ambiguous_label, self._ambiguous_check)
        self._param_layout.addRow(self._merge_label, self._merge_check)
        self._param_layout.addRow(self._epsilon_label, self._epsilon_spin)
        self._param_layout.addRow(
            self._mcan_reference_label, self._mcan_reference_combo)
        self._param_layout.addRow(
            self._mcan_ambiguous_label, self._mcan_ambiguous_check)
        self._param_layout.addRow(
            self._rmst_method_label, self._rmst_method_combo)
        self._param_layout.addRow(
            self._rmst_iterations_label, self._rmst_iterations_spin)
        self._param_layout.addRow(
            self._rmst_seed_label, self._rmst_seed_spin)
        self._param_layout.addRow(
            self._rmst_ambiguous_label, self._rmst_ambiguous_check)
        # ── Separator ───────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(sep)

        # ── Buttons ─────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._ok_btn = QPushButton(lang_manager.get('btn_ok', 'OK'))
        self._ok_btn.setDefault(True)
        self._ok_btn.setMinimumWidth(80)
        self._ok_btn.clicked.connect(self._on_ok)

        self._cancel_btn = QPushButton(lang_manager.get('btn_cancel', 'Cancel'))
        self._cancel_btn.setMinimumWidth(80)
        self._cancel_btn.clicked.connect(self.reject)

        btn_row.addWidget(self._ok_btn)
        btn_row.addWidget(self._cancel_btn)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_algorithm_changed(self, index: int):
        """Show/hide parameter rows based on selected algorithm."""
        alg = _ALGORITHMS[index][0]

        has_threads = alg in ("original_tcs", "modified_tcs", "mjn", "mcan")
        has_ambiguous = alg == "original_tcs"
        has_merge = alg == "original_tcs"
        has_epsilon = alg in ("msn", "mjn")
        is_mcan = alg == "mcan"
        is_rmst = alg == "rmst"

        self._threads_label.setVisible(has_threads)
        self._threads_spin.setVisible(has_threads)
        self._ambiguous_label.setVisible(has_ambiguous)
        self._ambiguous_check.setVisible(has_ambiguous)
        self._merge_label.setVisible(has_merge)
        self._merge_check.setVisible(has_merge)
        self._epsilon_label.setVisible(has_epsilon)
        self._epsilon_spin.setVisible(has_epsilon)
        show_mcan_alignment_options = is_mcan and not self._native_mcan_vcf
        self._mcan_reference_label.setVisible(show_mcan_alignment_options)
        self._mcan_reference_combo.setVisible(show_mcan_alignment_options)
        self._mcan_ambiguous_label.setVisible(show_mcan_alignment_options)
        self._mcan_ambiguous_check.setVisible(show_mcan_alignment_options)
        self._rmst_method_label.setVisible(is_rmst)
        self._rmst_method_combo.setVisible(is_rmst)
        self._rmst_ambiguous_label.setVisible(is_rmst)
        self._rmst_ambiguous_check.setVisible(is_rmst)
        self._update_rmst_parameter_visibility()

        # Hide the parameter group entirely when there are no options
        any_params = (has_threads or has_ambiguous or has_merge or has_epsilon
                      or is_mcan or is_rmst)
        self._param_group.setVisible(any_params)

        self.adjustSize()

    def _update_rmst_parameter_visibility(self, _index: int = -1):
        """Show sampling controls only for the randomized RMST mode."""
        is_rmst = _ALGORITHMS[self._alg_combo.currentIndex()][0] == "rmst"
        is_randomized = self._rmst_method_combo.currentData() == "randomized"
        visible = is_rmst and is_randomized
        self._rmst_iterations_label.setVisible(visible)
        self._rmst_iterations_spin.setVisible(visible)
        self._rmst_seed_label.setVisible(visible)
        self._rmst_seed_spin.setVisible(visible)

    def _on_ok(self):
        """Read widgets and accept the dialog."""
        index = self._alg_combo.currentIndex()
        alg = _ALGORITHMS[index][0]

        self._config = HaplotypeNetworkConfig(
            algorithm=alg,
            threads=self._threads_spin.value(),
            ambiguous=1 if self._ambiguous_check.isChecked() else 0,
            merge=1 if self._merge_check.isChecked() else 0,
            epsilon=self._epsilon_spin.value(),
            mcan_reference=("" if self._native_mcan_vcf
                            else self._mcan_reference_combo.currentText()),
            mcan_exclude_ambiguous=(False if self._native_mcan_vcf
                                    else self._mcan_ambiguous_check.isChecked()),
            rmst_method=self._rmst_method_combo.currentData(),
            rmst_iterations=self._rmst_iterations_spin.value(),
            rmst_seed=self._rmst_seed_spin.value(),
            rmst_exclude_ambiguous=self._rmst_ambiguous_check.isChecked(),
        )
        self.accept()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_config(self) -> HaplotypeNetworkConfig:
        """Return the configuration chosen by the user."""
        return self._config

    @staticmethod
    def get_network_config(parent=None, sample_names=None,
                           native_mcan_vcf: bool = False
                           ) -> Optional[HaplotypeNetworkConfig]:
        """
        Convenience factory: show modal dialog, return config or None on cancel.

        Usage::
            cfg = HaplotypeNetworkDialog.get_network_config(self)
            if cfg is not None:
                self._run_network_analysis(cfg.algorithm, cfg.to_extra_args())
        """
        dialog = HaplotypeNetworkDialog(
            parent, sample_names=sample_names,
            native_mcan_vcf=native_mcan_vcf)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
