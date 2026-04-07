"""
Standardization Dialog Module

Dialog for configuring sequence name standardization options.
"""

from dataclasses import dataclass
from typing import List, Optional, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QCheckBox, QLineEdit, QSpinBox, QLabel,
    QTextEdit, QPushButton, QFrame, QSplitter
)


@dataclass
class StandardizationConfig:
    """Configuration for standardization options."""
    remove_ambiguous: bool = False
    replace_enabled: bool = False
    replace_from: str = ""
    replace_to: str = ""

    split_name_enabled: bool = False
    split_name_delimiter: str = "|"
    split_name_index: int = 0

    split_discrete_enabled: bool = False
    split_discrete_delimiter: str = "|"
    split_discrete_index: int = 1

    split_continuous_enabled: bool = False
    split_continuous_delimiter: str = "|"
    split_continuous_index: int = 2

    use_numbering: bool = False


class SplitOptionWidget(QFrame):
    """Widget for a single split option (checkbox + delimiter + index)."""

    def __init__(self, label_text: str, default_index: int = 0, option_id: str = "", parent=None):
        super().__init__(parent)
        self.option_id = option_id
        self._setup_ui(label_text, default_index)

    def _setup_ui(self, label_text: str, default_index: int):
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(5)

        # Row 1: Checkbox + delimiter
        self.checkbox = QCheckBox("Split names using:")
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)
        layout.addWidget(self.checkbox, 0, 0)

        self.delimiter_edit = QLineEdit("|")
        self.delimiter_edit.setMaximumWidth(50)
        self.delimiter_edit.setEnabled(False)
        layout.addWidget(self.delimiter_edit, 0, 1)

        # Row 2: Label + index
        self.label = QLabel(label_text)
        self.label.setContentsMargins(20, 0, 0, 0)
        layout.addWidget(self.label, 1, 0)

        self.index_spin = QSpinBox()
        self.index_spin.setMinimum(0)
        self.index_spin.setMaximum(99)
        self.index_spin.setValue(default_index)
        self.index_spin.setMaximumWidth(50)
        self.index_spin.setEnabled(False)
        layout.addWidget(self.index_spin, 1, 1)

    def _on_checkbox_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.delimiter_edit.setEnabled(enabled)
        self.index_spin.setEnabled(enabled)

    def is_enabled(self) -> bool:
        return self.checkbox.isChecked()

    def get_delimiter(self) -> str:
        return self.delimiter_edit.text()

    def get_index(self) -> int:
        return self.index_spin.value()

    def set_preview_callback(self, callback: Callable):
        # Pass self as the source when checkbox state changes
        self.checkbox.stateChanged.connect(lambda state: callback(self, state))
        self.delimiter_edit.textChanged.connect(lambda: callback(self, None))
        self.index_spin.valueChanged.connect(lambda: callback(self, None))


class StandardizationDialog(QDialog):
    """
    Standardization Dialog
    
    Allows configuring how sequence names are parsed and standardized.
    """

    def __init__(self, sequence_names: List[str], parent=None):
        super().__init__(parent)
        self.sequence_names = sequence_names[:100]  # Limit preview to 100
        self.config = StandardizationConfig()
        self._accepted = False
        self._active_split = None  # Track which split option is currently active

        self._setup_ui()
        self._update_preview()

    def _setup_ui(self):
        self.setWindowTitle("Standardization")
        self.setMinimumSize(650, 450)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left side: Options
        options_widget = self._create_options_widget()
        splitter.addWidget(options_widget)

        # Right side: Preview
        preview_widget = self._create_preview_widget()
        splitter.addWidget(preview_widget)

        splitter.setSizes([280, 370])

        # Bottom: Buttons and numbering option
        bottom_layout = QHBoxLayout()

        self.numbering_check = QCheckBox("Use numbering as seq names")
        bottom_layout.addWidget(self.numbering_check)

        bottom_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.setMinimumWidth(75)
        self.ok_btn.clicked.connect(self._on_ok)
        bottom_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumWidth(75)
        self.cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(self.cancel_btn)

        layout.addLayout(bottom_layout)

    def _create_options_widget(self) -> QGroupBox:
        group = QGroupBox("Standardization")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Remove ambiguous bases
        self.remove_ambiguous_check = QCheckBox("Remove seq with ambiguous bases")
        layout.addWidget(self.remove_ambiguous_check)

        # Replace option
        replace_layout = QHBoxLayout()
        self.replace_check = QCheckBox("Replace")
        self.replace_check.stateChanged.connect(self._on_replace_changed)
        replace_layout.addWidget(self.replace_check)

        self.replace_from_edit = QLineEdit()
        self.replace_from_edit.setMaximumWidth(60)
        self.replace_from_edit.setEnabled(False)
        replace_layout.addWidget(self.replace_from_edit)

        replace_layout.addWidget(QLabel("->"))

        self.replace_to_edit = QLineEdit()
        self.replace_to_edit.setMaximumWidth(60)
        self.replace_to_edit.setEnabled(False)
        replace_layout.addWidget(self.replace_to_edit)

        replace_layout.addStretch()
        layout.addLayout(replace_layout)

        # Split options
        self.split_name = SplitOptionWidget("Use as the new name", 0)
        self.split_name.set_preview_callback(self._update_preview)
        layout.addWidget(self.split_name)

        self.split_discrete = SplitOptionWidget("Use as discrete trait", 1)
        self.split_discrete.set_preview_callback(self._update_preview)
        layout.addWidget(self.split_discrete)

        self.split_continuous = SplitOptionWidget("Use as continuous trait", 2)
        self.split_continuous.set_preview_callback(self._update_preview)
        layout.addWidget(self.split_continuous)

        layout.addStretch()

        return group

    def _create_preview_widget(self) -> QFrame:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        # Preview Names
        names_layout = QVBoxLayout()
        names_label = QLabel("Preview Names:")
        names_layout.addWidget(names_label)

        self.preview_names = QTextEdit()
        self.preview_names.setReadOnly(True)
        self.preview_names.setFont(QFont("Courier New", 9))
        self.preview_names.setStyleSheet("background-color: #FFFFCC;")
        names_layout.addWidget(self.preview_names)

        layout.addLayout(names_layout, 2)

        # Split Results
        results_layout = QVBoxLayout()
        results_label = QLabel("Split Results:")
        results_layout.addWidget(results_label)

        self.split_results = QTextEdit()
        self.split_results.setReadOnly(True)
        self.split_results.setFont(QFont("Courier New", 9))
        self.split_results.setStyleSheet("background-color: #FFFFCC;")
        results_layout.addWidget(self.split_results)

        layout.addLayout(results_layout, 1)

        return frame

    def _on_replace_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.replace_from_edit.setEnabled(enabled)
        self.replace_to_edit.setEnabled(enabled)

    def _update_preview(self, source=None, state=None):
        # Update preview names
        preview_text = "\n".join(self.sequence_names)
        self.preview_names.setText(preview_text)

        # If source is provided and it's enabled, make it the active split
        if source is not None and isinstance(source, SplitOptionWidget):
            if source.is_enabled():
                self._active_split = source
            elif self._active_split == source:
                # If this source was active but is now disabled, find another
                self._active_split = None

        # If no active split, find the first enabled one
        if self._active_split is None or not self._active_split.is_enabled():
            for split_widget in [self.split_name, self.split_discrete,
                                 self.split_continuous]:
                if split_widget.is_enabled():
                    self._active_split = split_widget
                    break
            else:
                self._active_split = None

        # Update split results based on active split
        if self._active_split and self._active_split.is_enabled() and self._active_split.get_delimiter():
            results = []
            delimiter = self._active_split.get_delimiter()
            index = self._active_split.get_index()

            for name in self.sequence_names:
                try:
                    parts = name.split(delimiter)
                    if index < len(parts):
                        results.append(parts[index])
                    else:
                        results.append(f"Error: {name}")
                except Exception:
                    results.append(f"Error: {name}")

            self.split_results.setText("\n".join(results))
        else:
            self.split_results.clear()

    def _on_ok(self):
        # Build configuration
        self.config.remove_ambiguous = self.remove_ambiguous_check.isChecked()
        self.config.replace_enabled = self.replace_check.isChecked()
        self.config.replace_from = self.replace_from_edit.text()
        self.config.replace_to = self.replace_to_edit.text()

        self.config.split_name_enabled = self.split_name.is_enabled()
        self.config.split_name_delimiter = self.split_name.get_delimiter()
        self.config.split_name_index = self.split_name.get_index()

        self.config.split_discrete_enabled = self.split_discrete.is_enabled()
        self.config.split_discrete_delimiter = self.split_discrete.get_delimiter()
        self.config.split_discrete_index = self.split_discrete.get_index()

        self.config.split_continuous_enabled = self.split_continuous.is_enabled()
        self.config.split_continuous_delimiter = self.split_continuous.get_delimiter()
        self.config.split_continuous_index = self.split_continuous.get_index()

        self.config.use_numbering = self.numbering_check.isChecked()

        self._accepted = True
        self.accept()

    def get_config(self) -> Optional[StandardizationConfig]:
        if self._accepted:
            return self.config
        return None

    @staticmethod
    def get_standardization_config(sequence_names: List[str], parent=None) -> Optional[StandardizationConfig]:
        """
        Static method to show dialog and get configuration.
        
        Returns StandardizationConfig if OK was clicked, None if cancelled.
        """
        dialog = StandardizationDialog(sequence_names, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
