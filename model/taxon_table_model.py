"""
Table model for displaying taxon/sequence data in a QTableView.
Corresponds to the DataGridView binding in VB.NET.
"""
from typing import Any, Optional, List

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QColor

from model.taxon_data import TaxonData


class TaxonTableModel(QAbstractTableModel):
    """Table model for displaying and editing taxon data."""

    COLUMNS = [
        ("Select", "selected"),
        ("ID", "id"),
        ("Name", "name"),
        ("Sequence", "display_sequence"),
        ("Discrete Traits", "discrete_traits"),
        ("Continuous Traits", "continuous_traits"),
    ]

    # Columns that can be edited (all except ID which is column 1)
    EDITABLE_COLUMNS = {0, 2, 3, 4, 5}  # Select, Name, Sequence, Discrete Traits, Continuous Traits

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[TaxonData] = []
        self._headers = [label for label, _ in self.COLUMNS]
        self._sequence_tooltip = "Length: {length} bp\nClick the cell to view or edit the full sequence"

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        taxon = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:  # Select column - handled by CheckStateRole
                return None
            attr_name = self.COLUMNS[col][1]
            return getattr(taxon, attr_name, "")

        elif role == Qt.ItemDataRole.CheckStateRole:
            if col == 0:  # Select column
                return Qt.CheckState.Checked if taxon.selected else Qt.CheckState.Unchecked

        elif role == Qt.ItemDataRole.EditRole:
            attr_name = self.COLUMNS[col][1]
            if attr_name == "display_sequence":
                return taxon.sequence  # Return full sequence for editing
            return getattr(taxon, attr_name, "")

        elif role == Qt.ItemDataRole.BackgroundRole:
            # Highlight invalid data
            if col == 5 and not taxon.is_valid_continuous_traits():
                return QColor(255, 200, 200)  # Light red

        elif role == Qt.ItemDataRole.ToolTipRole:
            if col == 3:  # Sequence column
                return self._sequence_tooltip.format(length=taxon.sequence_length)

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return False

        taxon = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            # Fix: Handle both Qt.CheckState enum and integer values
            if isinstance(value, Qt.CheckState):
                taxon.selected = (value == Qt.CheckState.Checked)
            else:
                taxon.selected = (value == Qt.CheckState.Checked.value)
            self.dataChanged.emit(index, index, [role])
            return True

        if role == Qt.ItemDataRole.EditRole and col in self.EDITABLE_COLUMNS:
            attr_name = self.COLUMNS[col][1]

            # Handle special cases
            if col == 3:  # Sequence column - update the actual sequence
                taxon.sequence = str(value)
                self.dataChanged.emit(index, index, [role])
                return True

            setattr(taxon, attr_name, value)
            self.dataChanged.emit(index, index, [role])
            return True

        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

        col = index.column()
        if col == 0:  # Select column
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        elif col in self.EDITABLE_COLUMNS:
            flags |= Qt.ItemFlag.ItemIsEditable

        return flags

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self._headers[section]
            else:
                return section + 1
        return None

    def update_language(self, headers: List[str], sequence_tooltip: str) -> None:
        """Update localized headers and tooltips without rebuilding the model."""
        if len(headers) == len(self.COLUMNS):
            self._headers = list(headers)
        self._sequence_tooltip = sequence_tooltip
        self.headerDataChanged.emit(
            Qt.Orientation.Horizontal, 0, len(self.COLUMNS) - 1
        )

    # Data manipulation methods

    def add_taxons(self, taxons: List[TaxonData]) -> None:
        """Add multiple taxons."""
        if not taxons:
            return
        start_row = len(self._data)
        end_row = start_row + len(taxons) - 1
        self.beginInsertRows(QModelIndex(), start_row, end_row)
        self._data.extend(taxons)
        self.endInsertRows()

    def clear(self) -> None:
        """Clear all data."""
        if self._data:
            self.beginRemoveRows(QModelIndex(), 0, len(self._data) - 1)
            self._data.clear()
            self.endRemoveRows()

    def get_taxon(self, row: int) -> Optional[TaxonData]:
        """Get taxon at row index."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def get_all_taxons(self) -> List[TaxonData]:
        """Get all taxons."""
        return list(self._data)

    def get_selected_taxons(self) -> List[TaxonData]:
        """Get all selected taxons."""
        return [t for t in self._data if t.selected]

    def get_selected_count(self) -> int:
        """Get count of selected taxons."""
        return sum(1 for t in self._data if t.selected)

    def select_all(self) -> None:
        """Select all taxons."""
        for taxon in self._data:
            taxon.selected = True
        if self._data:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._data) - 1, 0),
                [Qt.ItemDataRole.CheckStateRole]
            )

    def deselect_all(self) -> None:
        """Deselect all taxons."""
        for taxon in self._data:
            taxon.selected = False
        if self._data:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._data) - 1, 0),
                [Qt.ItemDataRole.CheckStateRole]
            )
