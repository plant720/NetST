"""
Haplotype Network Parameter Dialog

Allows the user to select a network algorithm (original_tcs, modified_tcs, msn, mjn)
and configure the corresponding fastHaN parameters before running the analysis.
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
    """Parameters chosen by the user for a fastHaN run."""
    algorithm: str = "modified_tcs"  # one of: original_tcs / modified_tcs / msn / mjn
    threads: int = 8  # -t  (original_tcs, modified_tcs, mjn)
    ambiguous: int = 0  # -a  (original_tcs only) 0/1
    merge: int = 0  # -m  (original_tcs only) 0/1
    epsilon: int = 0  # -e  (msn, mjn)

    def to_extra_args(self) -> List[str]:
        """Build the extra CLI arguments list for fastHaN (excluding -i / -o)."""
        args: List[str] = []
        alg = self.algorithm

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

# Algorithm display labels → fastHaN identifiers
_ALGORITHMS = [
    ("original_tcs", "Original TCS"),
    ("modified_tcs", "Modified TCS"),
    ("msn", "MSN (Minimum Spanning Network)"),
    ("mjn", "MJN (Median-Joining Network)"),
]


class HaplotypeNetworkDialog(QDialog):
    """
    Modal dialog for configuring a fastHaN haplotype network run.

    Shows a combo-box to pick the algorithm and a dynamic parameter
    group that updates to match the selected algorithm's options.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
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
        for _, label in _ALGORITHMS:
            self._alg_combo.addItem(label)
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

        # Add all rows; visibility controlled in _on_algorithm_changed
        self._param_layout.addRow(self._threads_label, self._threads_spin)
        self._param_layout.addRow(self._ambiguous_label, self._ambiguous_check)
        self._param_layout.addRow(self._merge_label, self._merge_check)
        self._param_layout.addRow(self._epsilon_label, self._epsilon_spin)

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

        has_threads = alg in ("original_tcs", "modified_tcs", "mjn")
        has_ambiguous = alg == "original_tcs"
        has_merge = alg == "original_tcs"
        has_epsilon = alg in ("msn", "mjn")

        self._threads_label.setVisible(has_threads)
        self._threads_spin.setVisible(has_threads)
        self._ambiguous_label.setVisible(has_ambiguous)
        self._ambiguous_check.setVisible(has_ambiguous)
        self._merge_label.setVisible(has_merge)
        self._merge_check.setVisible(has_merge)
        self._epsilon_label.setVisible(has_epsilon)
        self._epsilon_spin.setVisible(has_epsilon)

        # Hide the parameter group entirely when there are no options
        any_params = has_threads or has_ambiguous or has_merge or has_epsilon
        self._param_group.setVisible(any_params)

        self.adjustSize()

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
        )
        self.accept()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_config(self) -> HaplotypeNetworkConfig:
        """Return the configuration chosen by the user."""
        return self._config

    @staticmethod
    def get_network_config(parent=None) -> Optional[HaplotypeNetworkConfig]:
        """
        Convenience factory: show modal dialog, return config or None on cancel.

        Usage::
            cfg = HaplotypeNetworkDialog.get_network_config(self)
            if cfg is not None:
                self._run_network_analysis(cfg.algorithm, cfg.to_extra_args())
        """
        dialog = HaplotypeNetworkDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
