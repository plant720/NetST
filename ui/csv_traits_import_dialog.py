"""
CSV Traits Import Dialog Module

Dialog for selecting which CSV columns map to sequence name,
discrete traits, and continuous traits when importing trait data.
"""

from typing import List, Optional, Dict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy
)

from .language_manager import lang_manager

_NONE_OPTION = "-- None --"


class CsvTraitsImportDialog(QDialog):
    """
    Dialog that lets the user map CSV columns to sequence name,
    discrete traits, and continuous traits fields.
    """

    def __init__(
            self,
            headers: List[str],
            preview_rows: List[List[str]],
            parent=None,
    ):
        super().__init__(parent)
        self._headers = headers
        self._preview_rows = preview_rows
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        self.setWindowTitle(lang_manager.get('dlg_csv_title', 'Import Traits from CSV'))
        self.setMinimumSize(620, 460)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(14, 14, 14, 14)

        # ---- Column mapping group ----
        mapping_group = QGroupBox(lang_manager.get('dlg_csv_mapping', 'Column Mapping'))
        grid = QGridLayout(mapping_group)
        grid.setSpacing(8)

        # Sequence Name (required)
        grid.addWidget(QLabel(lang_manager.get('dlg_csv_seq_name', 'Sequence Name Column:')), 0, 0)
        self.combo_name = QComboBox()
        self.combo_name.addItems(self._headers)
        grid.addWidget(self.combo_name, 0, 1)

        # Discrete Traits (optional)
        grid.addWidget(QLabel(lang_manager.get('dlg_csv_discrete', 'Discrete Traits Column:')), 1, 0)
        self.combo_discrete = QComboBox()
        self.combo_discrete.addItem(_NONE_OPTION)
        self.combo_discrete.addItems(self._headers)
        grid.addWidget(self.combo_discrete, 1, 1)

        # Continuous Traits (optional)
        grid.addWidget(QLabel(lang_manager.get('dlg_csv_continuous', 'Continuous Traits Column:')), 2, 0)
        self.combo_continuous = QComboBox()
        self.combo_continuous.addItem(_NONE_OPTION)
        self.combo_continuous.addItems(self._headers)
        grid.addWidget(self.combo_continuous, 2, 1)

        main_layout.addWidget(mapping_group)

        # ---- Preview table ----
        preview_group = QGroupBox(lang_manager.get('dlg_csv_preview', 'Data Preview (first rows)'))
        preview_layout = QVBoxLayout(preview_group)

        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.preview_table.setColumnCount(len(self._headers))
        self.preview_table.setHorizontalHeaderLabels(self._headers)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.preview_table.setRowCount(len(self._preview_rows))
        for row_idx, row in enumerate(self._preview_rows):
            for col_idx, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.preview_table.setItem(row_idx, col_idx, item)

        preview_layout.addWidget(self.preview_table)
        main_layout.addWidget(preview_group)

        # ---- Buttons ----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_ok = QPushButton(lang_manager.get('btn_ok', 'OK'))
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self.accept)

        self.btn_cancel = QPushButton(lang_manager.get('btn_cancel', 'Cancel'))
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def get_mapping(self) -> Dict[str, Optional[int]]:
        """
        Return the column-index mapping chosen by the user.

        Keys:
          'name_col'       – index of the sequence-name column (always set)
          'discrete_col'   – index of discrete traits column, or None
          'continuous_col' – index of continuous traits column, or None
        """

        def _index(combo: QComboBox, has_none: bool) -> Optional[int]:
            text = combo.currentText()
            if has_none and text == _NONE_OPTION:
                return None
            try:
                return self._headers.index(text)
            except ValueError:
                return None

        return {
            'name_col': _index(self.combo_name, has_none=False),
            'discrete_col': _index(self.combo_discrete, has_none=True),
            'continuous_col': _index(self.combo_continuous, has_none=True),
        }

    # ------------------------------------------------------------------
    # Static factory
    # ------------------------------------------------------------------

    @staticmethod
    def get_column_mapping(
            headers: List[str],
            preview_rows: List[List[str]],
            parent=None,
    ) -> Optional[Dict[str, Optional[int]]]:
        """
        Show the dialog and return the column mapping, or None if cancelled.
        """
        dlg = CsvTraitsImportDialog(headers, preview_rows, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.get_mapping()
        return None
