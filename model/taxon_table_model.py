"""
Table model for displaying taxon/sequence data in a QTableView.

Base columns (Select, ID, Name, Sequence) are followed by one dynamic column
per trait in the project's :class:`~model.trait_schema.TraitSchema`. Trait cell
values live in ``TaxonData.traits``; editing the group or primary-continuous
trait also updates the ``discrete_traits`` / ``continuous_traits`` mirrors that
the classic pipeline reads.
"""
from typing import Any, Optional, List

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QColor

from model.taxon_data import TaxonData
from model.trait_schema import CONTINUOUS, DISCRETE, TraitSchema
from service.validation_service import has_meaningful_continuous_trait


class TaxonTableModel(QAbstractTableModel):
    """Table model for displaying and editing taxon data."""

    # Fixed leading columns; trait columns are appended after these.
    BASE_COLUMNS = [
        ("Select", "selected"),
        ("ID", "id"),
        ("Name", "name"),
        ("Sequence", "display_sequence"),
    ]
    NAME_COLUMN = 2
    SEQUENCE_COLUMN = 3
    FIRST_TRAIT_COLUMN = len(BASE_COLUMNS)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[TaxonData] = []
        self._schema: TraitSchema = TraitSchema()
        self._trait_columns: List[str] = []
        self._base_headers = [label for label, _ in self.BASE_COLUMNS]
        self._sequence_tooltip = "Length: {length} bp\nSequence is read-only"

    # ── schema-driven columns ────────────────────────────────────────────────

    def set_schema(self, schema: TraitSchema) -> None:
        """Point the model at a new trait schema and rebuild the columns."""
        self.beginResetModel()
        self._schema = schema
        self._trait_columns = [d.name for d in schema.ordered()]
        self.endResetModel()

    def schema(self) -> TraitSchema:
        return self._schema

    def _trait_at(self, column: int) -> Optional[str]:
        index = column - self.FIRST_TRAIT_COLUMN
        if 0 <= index < len(self._trait_columns):
            return self._trait_columns[index]
        return None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.BASE_COLUMNS) + len(self._trait_columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        taxon = self._data[index.row()]
        col = index.column()
        trait_name = self._trait_at(col)

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:  # Select column - handled by CheckStateRole
                return None
            if trait_name is not None:
                return taxon.trait_value(trait_name)
            attr_name = self.BASE_COLUMNS[col][1]
            return getattr(taxon, attr_name, "")

        elif role == Qt.ItemDataRole.CheckStateRole:
            if col == 0:  # Select column
                return Qt.CheckState.Checked if taxon.selected else Qt.CheckState.Unchecked

        elif role == Qt.ItemDataRole.EditRole:
            if trait_name is not None:
                return taxon.trait_value(trait_name)
            attr_name = self.BASE_COLUMNS[col][1]
            if attr_name == "display_sequence":
                return taxon.sequence
            return getattr(taxon, attr_name, "")

        elif role == Qt.ItemDataRole.BackgroundRole:
            # Highlight an invalid continuous-trait value.
            if trait_name is not None:
                definition = self._schema.get(trait_name)
                if (definition is not None and definition.kind == CONTINUOUS
                        and not has_meaningful_continuous_trait(taxon.trait_value(trait_name))
                        and taxon.trait_value(trait_name).strip() not in ("", "0")):
                    return QColor(255, 200, 200)  # Light red

        elif role == Qt.ItemDataRole.ToolTipRole:
            if col == self.SEQUENCE_COLUMN:
                return self._sequence_tooltip.format(length=taxon.sequence_length)

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return False

        taxon = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            if isinstance(value, Qt.CheckState):
                taxon.selected = (value == Qt.CheckState.Checked)
            else:
                taxon.selected = (value == Qt.CheckState.Checked.value)
            self.dataChanged.emit(index, index, [role])
            return True

        if role != Qt.ItemDataRole.EditRole:
            return False

        trait_name = self._trait_at(col)
        if trait_name is not None:
            taxon.traits[trait_name] = str(value)
            self._sync_primary_traits(taxon)
            self.dataChanged.emit(index, index, [role])
            return True

        if col == self.NAME_COLUMN:
            taxon.name = str(value)
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
        elif col in (1, self.SEQUENCE_COLUMN):  # ID and sequence are read-only
            pass
        else:  # Name and every trait column are editable
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                trait_name = self._trait_at(section)
                if trait_name is not None:
                    definition = self._schema.get(trait_name)
                    suffix = ""
                    if definition is not None:
                        marks = []
                        if definition.is_group:
                            marks.append("group")
                        marks.append(
                            "Cat" if definition.kind == DISCRETE else "Num")
                        suffix = " (" + ", ".join(marks) + ")"
                    return f"{trait_name}{suffix}"
                if 0 <= section < len(self._base_headers):
                    return self._base_headers[section]
                return ""
            return section + 1
        return None

    def update_language(self, headers: List[str], sequence_tooltip: str) -> None:
        """Update localized base headers and tooltips without rebuilding the model."""
        if len(headers) >= len(self.BASE_COLUMNS):
            self._base_headers = list(headers[:len(self.BASE_COLUMNS)])
        self._sequence_tooltip = sequence_tooltip
        self.headerDataChanged.emit(
            Qt.Orientation.Horizontal, 0, self.columnCount() - 1
        )

    # ── trait synchronization ────────────────────────────────────────────────

    def _sync_primary_traits(self, taxon: TaxonData) -> None:
        """Mirror the group / primary-continuous trait values onto the taxon.

        The classic pipeline (haplotype processing, meta.csv, diversity) reads
        ``discrete_traits`` and ``continuous_traits``; keep them in step with the
        designated group and first visualized continuous trait.
        """
        group = self._schema.group()
        if group is not None:
            taxon.discrete_traits = taxon.trait_value(group.name)
        else:
            taxon.discrete_traits = ""
        primary = self._schema.primary_continuous()
        if primary is not None:
            value = taxon.trait_value(primary.name)
            taxon.continuous_traits = value if value.strip() else "0"
        else:
            taxon.continuous_traits = "0"

    def sync_all_primary_traits(self) -> None:
        """Re-sync every taxon after the schema's group/primary changes."""
        for taxon in self._data:
            self._sync_primary_traits(taxon)
        if self.columnCount() > self.FIRST_TRAIT_COLUMN:
            self.headerDataChanged.emit(
                Qt.Orientation.Horizontal,
                self.FIRST_TRAIT_COLUMN,
                self.columnCount() - 1,
            )
        if self._data:
            first_trait = self.FIRST_TRAIT_COLUMN
            last_trait = self.columnCount() - 1
            if last_trait < first_trait:
                return
            self.dataChanged.emit(
                self.index(0, first_trait),
                self.index(len(self._data) - 1, last_trait),
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
