"""Options for missing-aware auxiliary sequence analyses."""

from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from .language_manager import lang_manager


class InterpretationOptionsDialog(QDialog):
    def __init__(self, mode: str, alignment_length: int, parent=None,
                 group_traits=None, default_group=None):
        super().__init__(parent)
        self.mode = mode
        self.setWindowTitle(lang_manager.get(
            'dlg_interpretation_options', 'Interpretation Analysis Options'))
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.missing_policy = None
        self.minimum_sites = None
        self.minimum_coverage = None
        self.group_trait = None
        self.permutation_count = None

        if mode == 'diversity':
            # Choose which discrete trait groups samples (Hd, pi, private haplotypes).
            group_traits = list(group_traits or [])
            if group_traits:
                self.group_trait = QComboBox()
                for name in group_traits:
                    self.group_trait.addItem(name, name)
                if default_group and default_group in group_traits:
                    self.group_trait.setCurrentText(default_group)
                form.addRow(lang_manager.get(
                    'label_group_trait', 'Group samples by:'), self.group_trait)

            self.missing_policy = QComboBox()
            self.missing_policy.addItem(
                lang_manager.get('option_complete_deletion', 'Complete deletion'),
                'complete_deletion')
            self.missing_policy.addItem(
                lang_manager.get('option_pairwise_deletion', 'Pairwise deletion'),
                'pairwise_deletion')
            form.addRow(lang_manager.get(
                'label_missing_policy', 'Missing-data policy:'), self.missing_policy)
            self.permutation_count = QSpinBox()
            self.permutation_count.setRange(0, 100000)
            self.permutation_count.setSingleStep(100)
            self.permutation_count.setValue(999)
            self.permutation_count.setToolTip(lang_manager.get(
                'permutation_count_tip',
                'Permutations for global FST and AMOVA; 0 disables P values.'))
            form.addRow(lang_manager.get(
                'label_permutation_count', 'Permutations:'), self.permutation_count)
        elif mode == 'distance':
            self.minimum_sites = QSpinBox()
            self.minimum_sites.setRange(1, max(1, alignment_length))
            self.minimum_sites.setValue(1)
            self.minimum_coverage = QDoubleSpinBox()
            self.minimum_coverage.setRange(0.0, 100.0)
            self.minimum_coverage.setDecimals(1)
            self.minimum_coverage.setSuffix('%')
            self.minimum_coverage.setValue(50.0)
            form.addRow(lang_manager.get(
                'label_minimum_comparable_sites', 'Minimum comparable sites:'),
                self.minimum_sites)
            form.addRow(lang_manager.get(
                'label_minimum_coverage', 'Minimum comparable coverage:'),
                self.minimum_coverage)
        else:
            raise ValueError(f'Unsupported interpretation option mode: {mode}')

        layout.addLayout(form)
        note = QLabel(lang_manager.get(
            'interpretation_options_note',
            'Gap, N, ?, and IUPAC ambiguity codes are treated as non-callable.'))
        note.setWordWrap(True)
        note.setStyleSheet('color:#596b75;')
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def config(self) -> Dict[str, object]:
        if self.mode == 'diversity':
            result = {
                'missing_policy': self.missing_policy.currentData(),
                'permutation_count': self.permutation_count.value(),
            }
            if self.group_trait is not None:
                result['group_trait'] = self.group_trait.currentData()
            return result
        return {
            'minimum_comparable_sites': self.minimum_sites.value(),
            'minimum_coverage': self.minimum_coverage.value() / 100.0,
        }

    @classmethod
    def get_config(
        cls, mode: str, alignment_length: int, parent=None,
        group_traits=None, default_group=None,
    ) -> Optional[Dict[str, object]]:
        dialog = cls(mode, alignment_length, parent,
                     group_traits=group_traits, default_group=default_group)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.config()
        return None
