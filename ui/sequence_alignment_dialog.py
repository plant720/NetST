"""
Multiple Sequence Alignment Parameter Dialog

Presents a tabbed dialog for configuring either MAFFT or MUSCLE alignment,
based on the CLI options supported by each tool.
"""

from dataclasses import dataclass
from typing import Optional, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QPushButton, QLabel, QFrame, QTabWidget, QWidget, QSizePolicy,
)
from PyQt6.QtCore import Qt

from .language_manager import lang_manager


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------

@dataclass
class SequenceAlignmentConfig:
    """Parameters chosen by the user for a standalone alignment run."""

    tool: str = "mafft"          # "mafft" or "muscle"

    # ── MAFFT options ──────────────────────────────────────────────────────
    mafft_algorithm: str = "auto"   # auto | retree1 | retree2 | linsi | ginsi | einsi
    mafft_op: float = 1.53          # --op  gap opening penalty
    mafft_ep: float = 0.0           # --ep  offset (gap extension-like)
    mafft_maxiterate: int = 0       # --maxiterate  (0 = disabled / use algorithm default)
    mafft_thread: int = -1          # --thread  (-1 = auto)
    mafft_clustalout: bool = False   # --clustalout
    mafft_reorder: bool = False      # --reorder  (default: input order)
    mafft_quiet: bool = False        # --quiet
    mafft_dash: bool = False         # --dash

    # ── MUSCLE options ─────────────────────────────────────────────────────
    muscle_maxiters: int = 16        # -maxiters
    muscle_maxhours: float = 0.0     # -maxhours  (0.0 = no limit)
    muscle_diags: bool = False        # -diags
    muscle_output_format: str = "fasta"  # fasta | html | msf | clw | clwstrict
    muscle_quiet: bool = False        # -quiet

    # ── MAFFT arg builders ─────────────────────────────────────────────────

    def to_mafft_method_args(self) -> List[str]:
        """Return the algorithm/method portion of the MAFFT args list.

        Note: '--inputorder' is handled separately by AnalysisService
        (it is added by default unless mafft_reorder is True).
        """
        _alg_map = {
            "auto":    ["--auto"],
            "retree1": ["--retree", "1"],
            "retree2": ["--retree", "2"],
            "linsi":   ["--localpair",  "--maxiterate", "1000"],
            "ginsi":   ["--globalpair", "--maxiterate", "1000"],
            "einsi":   ["--genafpair",  "--maxiterate", "1000"],
        }
        args: List[str] = list(_alg_map.get(self.mafft_algorithm, ["--auto"]))

        # Per-run options
        if self.mafft_op != 1.53:
            args += ["--op", str(round(self.mafft_op, 6))]
        if self.mafft_ep != 0.0:
            args += ["--ep", str(round(self.mafft_ep, 6))]

        # Only apply --maxiterate for non-preset algorithms
        preset_algorithms = {"linsi", "ginsi", "einsi"}
        if self.mafft_algorithm not in preset_algorithms and self.mafft_maxiterate > 0:
            args += ["--maxiterate", str(self.mafft_maxiterate)]

        args += ["--thread", str(self.mafft_thread)]

        if self.mafft_clustalout:
            args.append("--clustalout")
        if self.mafft_reorder:
            args.append("--reorder")
        if self.mafft_quiet:
            args.append("--quiet")
        if self.mafft_dash:
            args.append("--dash")

        return args

    # ── MUSCLE arg builder ─────────────────────────────────────────────────

    def to_muscle_extra_args(self) -> List[str]:
        """Return MUSCLE option args (excluding -in / -out file paths)."""
        args: List[str] = []
        if self.muscle_diags:
            args.append("-diags")
        if self.muscle_maxiters != 16:
            args += ["-maxiters", str(self.muscle_maxiters)]
        if self.muscle_maxhours > 0.0:
            args += ["-maxhours", str(round(self.muscle_maxhours, 4))]
        _fmt_map = {
            "html":      "-html",
            "msf":       "-msf",
            "clw":       "-clw",
            "clwstrict": "-clwstrict",
        }
        if self.muscle_output_format in _fmt_map:
            args.append(_fmt_map[self.muscle_output_format])
        if self.muscle_quiet:
            args.append("-quiet")
        return args


# ---------------------------------------------------------------------------
# Algorithm display lists
# ---------------------------------------------------------------------------

_MAFFT_ALGORITHMS = [
    ("auto",    "Auto (automatic selection)"),
    ("retree1", "FFT-NS-1 (very fast)"),
    ("retree2", "FFT-NS-2 (fast, default)"),
    ("linsi",   "L-INS-i (local pair, most accurate, slow)"),
    ("ginsi",   "G-INS-i (global pair, slow)"),
    ("einsi",   "E-INS-i (long indel regions, slow)"),
]

_MUSCLE_OUTPUT_FORMATS = [
    ("fasta",     "FASTA (default)"),
    ("html",      "HTML (-html)"),
    ("msf",       "GCG MSF (-msf)"),
    ("clw",       "CLUSTALW (-clw)"),
    ("clwstrict", "CLUSTALW strict header (-clwstrict)"),
]

# Preset algorithms that fix --maxiterate internally
_PRESET_ALGORITHMS = {"linsi", "ginsi", "einsi"}


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class SequenceAlignmentDialog(QDialog):
    """
    Modal dialog for configuring a Multiple Sequence Alignment run.

    Presents a tab per tool (MAFFT / MUSCLE).  The user selects the tool
    tab they want, configures parameters, then confirms.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = SequenceAlignmentConfig()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.setWindowTitle(lang_manager.get(
            'dlg_msa_title', 'Multiple Sequence Alignment'))
        self.setMinimumWidth(460)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        # ── Tool tabs ───────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_mafft_tab(),  "MAFFT")
        self._tabs.addTab(self._build_muscle_tab(), "MUSCLE")
        root.addWidget(self._tabs)

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

    # ── MAFFT tab ───────────────────────────────────────────────────────

    def _build_mafft_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Algorithm group
        alg_group = QGroupBox(lang_manager.get('dlg_msa_mafft_algorithm', 'Algorithm'))
        alg_form = QFormLayout(alg_group)
        alg_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self._mafft_alg_combo = QComboBox()
        for key, label in _MAFFT_ALGORITHMS:
            self._mafft_alg_combo.addItem(label, key)
        self._mafft_alg_combo.currentIndexChanged.connect(self._on_mafft_alg_changed)
        alg_form.addRow(lang_manager.get('dlg_msa_select', 'Algorithm:'),
                        self._mafft_alg_combo)
        layout.addWidget(alg_group)

        # Parameters group
        param_group = QGroupBox(lang_manager.get('dlg_msa_parameters', 'Parameters'))
        param_form = QFormLayout(param_group)
        param_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        # --op
        self._mafft_op_spin = QDoubleSpinBox()
        self._mafft_op_spin.setRange(0.0, 100.0)
        self._mafft_op_spin.setSingleStep(0.01)
        self._mafft_op_spin.setDecimals(4)
        self._mafft_op_spin.setValue(1.53)
        self._mafft_op_spin.setToolTip(
            lang_manager.get('dlg_msa_mafft_op_tip',
                             'Gap opening penalty (default: 1.53)'))
        param_form.addRow(
            lang_manager.get('dlg_msa_mafft_op', 'Gap Open Penalty (--op):'),
            self._mafft_op_spin)

        # --ep
        self._mafft_ep_spin = QDoubleSpinBox()
        self._mafft_ep_spin.setRange(0.0, 100.0)
        self._mafft_ep_spin.setSingleStep(0.01)
        self._mafft_ep_spin.setDecimals(4)
        self._mafft_ep_spin.setValue(0.0)
        self._mafft_ep_spin.setToolTip(
            lang_manager.get('dlg_msa_mafft_ep_tip',
                             'Offset (works like gap extension penalty, default: 0.0)'))
        param_form.addRow(
            lang_manager.get('dlg_msa_mafft_ep', 'Offset (--ep):'),
            self._mafft_ep_spin)

        # --maxiterate
        self._mafft_maxiter_label = QLabel(
            lang_manager.get('dlg_msa_mafft_maxiterate', 'Max Iterations (--maxiterate):'))
        self._mafft_maxiter_spin = QSpinBox()
        self._mafft_maxiter_spin.setRange(0, 9999)
        self._mafft_maxiter_spin.setValue(0)
        self._mafft_maxiter_spin.setToolTip(
            lang_manager.get('dlg_msa_mafft_maxiterate_tip',
                             'Maximum iterative refinement cycles (0 = algorithm default). '
                             'Disabled for L/G/E-INS-i presets.'))
        param_form.addRow(self._mafft_maxiter_label, self._mafft_maxiter_spin)

        # --thread
        self._mafft_thread_spin = QSpinBox()
        self._mafft_thread_spin.setRange(-1, 256)
        self._mafft_thread_spin.setValue(-1)
        self._mafft_thread_spin.setToolTip(
            lang_manager.get('dlg_msa_mafft_thread_tip',
                             'Number of threads (-1 = auto-detect, default: -1)'))
        param_form.addRow(
            lang_manager.get('dlg_msa_mafft_thread', 'Threads (--thread):'),
            self._mafft_thread_spin)

        layout.addWidget(param_group)

        # Options group (checkboxes)
        opt_group = QGroupBox(lang_manager.get('dlg_msa_options', 'Options'))
        opt_layout = QVBoxLayout(opt_group)

        self._mafft_clustalout_chk = QCheckBox(
            lang_manager.get('dlg_msa_mafft_clustalout', 'Clustal output format (--clustalout)'))
        self._mafft_clustalout_chk.setToolTip(
            lang_manager.get('dlg_msa_mafft_clustalout_tip',
                             'Output in Clustal format instead of FASTA'))

        self._mafft_reorder_chk = QCheckBox(
            lang_manager.get('dlg_msa_mafft_reorder', 'Reorder output by alignment (--reorder)'))
        self._mafft_reorder_chk.setToolTip(
            lang_manager.get('dlg_msa_mafft_reorder_tip',
                             'Output sequences in alignment order (default: input order)'))

        self._mafft_quiet_chk = QCheckBox(
            lang_manager.get('dlg_msa_mafft_quiet', 'Quiet mode (--quiet)'))
        self._mafft_quiet_chk.setToolTip(
            lang_manager.get('dlg_msa_mafft_quiet_tip', 'Do not report progress'))

        self._mafft_dash_chk = QCheckBox(
            lang_manager.get('dlg_msa_mafft_dash', 'Add structural information (--dash)'))
        self._mafft_dash_chk.setToolTip(
            lang_manager.get('dlg_msa_mafft_dash_tip',
                             'Add structural information (Rozewicki et al.)'))

        for chk in (self._mafft_clustalout_chk, self._mafft_reorder_chk,
                    self._mafft_quiet_chk, self._mafft_dash_chk):
            opt_layout.addWidget(chk)

        layout.addWidget(opt_group)
        layout.addStretch()

        # Trigger initial visibility
        self._on_mafft_alg_changed(0)

        return page

    # ── MUSCLE tab ──────────────────────────────────────────────────────

    def _build_muscle_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Parameters group
        param_group = QGroupBox(lang_manager.get('dlg_msa_parameters', 'Parameters'))
        param_form = QFormLayout(param_group)
        param_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        # -maxiters
        self._muscle_maxiters_spin = QSpinBox()
        self._muscle_maxiters_spin.setRange(1, 9999)
        self._muscle_maxiters_spin.setValue(16)
        self._muscle_maxiters_spin.setToolTip(
            lang_manager.get('dlg_msa_muscle_maxiters_tip',
                             'Maximum number of iterations (default: 16). '
                             'Use 2 for very fast (no refinement), 1 for fastest possible.'))
        param_form.addRow(
            lang_manager.get('dlg_msa_muscle_maxiters', 'Max Iterations (-maxiters):'),
            self._muscle_maxiters_spin)

        # -maxhours
        self._muscle_maxhours_spin = QDoubleSpinBox()
        self._muscle_maxhours_spin.setRange(0.0, 9999.0)
        self._muscle_maxhours_spin.setSingleStep(0.5)
        self._muscle_maxhours_spin.setDecimals(2)
        self._muscle_maxhours_spin.setValue(0.0)
        self._muscle_maxhours_spin.setToolTip(
            lang_manager.get('dlg_msa_muscle_maxhours_tip',
                             'Maximum time to iterate in hours (0.0 = no limit, default: no limit)'))
        param_form.addRow(
            lang_manager.get('dlg_msa_muscle_maxhours', 'Max Hours (-maxhours):'),
            self._muscle_maxhours_spin)

        # Output format
        self._muscle_fmt_combo = QComboBox()
        for key, label in _MUSCLE_OUTPUT_FORMATS:
            self._muscle_fmt_combo.addItem(label, key)
        self._muscle_fmt_combo.setToolTip(
            lang_manager.get('dlg_msa_muscle_format_tip',
                             'Output alignment format (default: FASTA)'))
        param_form.addRow(
            lang_manager.get('dlg_msa_muscle_format', 'Output Format:'),
            self._muscle_fmt_combo)

        layout.addWidget(param_group)

        # Options group
        opt_group = QGroupBox(lang_manager.get('dlg_msa_options', 'Options'))
        opt_layout = QVBoxLayout(opt_group)

        self._muscle_diags_chk = QCheckBox(
            lang_manager.get('dlg_msa_muscle_diags', 'Find diagonals (-diags)'))
        self._muscle_diags_chk.setToolTip(
            lang_manager.get('dlg_msa_muscle_diags_tip',
                             'Enable diagonal finding (faster for similar sequences)'))

        self._muscle_quiet_chk = QCheckBox(
            lang_manager.get('dlg_msa_muscle_quiet', 'Quiet mode (-quiet)'))
        self._muscle_quiet_chk.setToolTip(
            lang_manager.get('dlg_msa_muscle_quiet_tip',
                             'Do not write progress messages to stderr'))

        for chk in (self._muscle_diags_chk, self._muscle_quiet_chk):
            opt_layout.addWidget(chk)

        layout.addWidget(opt_group)
        layout.addStretch()

        return page

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_mafft_alg_changed(self, index: int):
        """Disable --maxiterate spinner for preset algorithms that fix it."""
        key = self._mafft_alg_combo.itemData(index) or "auto"
        is_preset = key in _PRESET_ALGORITHMS
        self._mafft_maxiter_label.setEnabled(not is_preset)
        self._mafft_maxiter_spin.setEnabled(not is_preset)
        if is_preset:
            self._mafft_maxiter_spin.setToolTip(
                lang_manager.get('dlg_msa_mafft_maxiterate_preset_tip',
                                 'Fixed at 1000 for this algorithm preset'))

    def _on_ok(self):
        """Read widget values and accept the dialog."""
        tool = "mafft" if self._tabs.currentIndex() == 0 else "muscle"

        # MAFFT
        mafft_alg = self._mafft_alg_combo.currentData() or "auto"

        # MUSCLE output format
        muscle_fmt = self._muscle_fmt_combo.currentData() or "fasta"

        self._config = SequenceAlignmentConfig(
            tool=tool,
            # MAFFT
            mafft_algorithm=mafft_alg,
            mafft_op=self._mafft_op_spin.value(),
            mafft_ep=self._mafft_ep_spin.value(),
            mafft_maxiterate=self._mafft_maxiter_spin.value(),
            mafft_thread=self._mafft_thread_spin.value(),
            mafft_clustalout=self._mafft_clustalout_chk.isChecked(),
            mafft_reorder=self._mafft_reorder_chk.isChecked(),
            mafft_quiet=self._mafft_quiet_chk.isChecked(),
            mafft_dash=self._mafft_dash_chk.isChecked(),
            # MUSCLE
            muscle_maxiters=self._muscle_maxiters_spin.value(),
            muscle_maxhours=self._muscle_maxhours_spin.value(),
            muscle_diags=self._muscle_diags_chk.isChecked(),
            muscle_output_format=muscle_fmt,
            muscle_quiet=self._muscle_quiet_chk.isChecked(),
        )
        self.accept()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_config(self) -> SequenceAlignmentConfig:
        """Return the configuration chosen by the user."""
        return self._config

    @staticmethod
    def get_alignment_config(parent=None) -> Optional[SequenceAlignmentConfig]:
        """
        Convenience factory: show the modal dialog and return config or None on cancel.

        Usage::
            cfg = SequenceAlignmentDialog.get_alignment_config(self)
            if cfg is not None:
                self._run_sequence_alignment(cfg)
        """
        dialog = SequenceAlignmentDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
