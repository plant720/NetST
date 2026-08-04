"""
Metadata Import Dialog Module

Maps each column of a CSV/TSV metadata file to a role — sample name, a discrete
trait, a continuous trait, or ignored — so a project can carry several traits per
sample. At least one discrete trait is required and is designated the *group*.
"""

from typing import List, Optional, Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QComboBox, QLineEdit, QPushButton, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QWidget,
    QSizePolicy, QMessageBox,
)

from model.trait_schema import CONTINUOUS, DISCRETE
from service.continuous_transform_service import (
    DATE_DAYS,
    DATE_MONTHS,
    DATE_YEARS,
    MODE_DATE,
    MODE_MEASUREMENT,
    MODE_NUMBER,
    QUANTITY_LENGTH,
    QUANTITY_MASS,
    QUANTITY_TEMPERATURE,
    UNIT_DEFINITIONS,
    ContinuousTransform,
    ContinuousTransformError,
    parse_date_value,
    transform_continuous_values,
)
from service.metadata_service import MetadataMapping, TraitColumn
from .language_manager import lang_manager


# Column roles offered per source column.
ROLE_IGNORE = "ignore"
ROLE_NAME = "name"
ROLE_DISCRETE = "discrete"
ROLE_CONTINUOUS = "continuous"

_NAME_HINTS = {
    "sample", "sampleid", "sample_id", "name", "sequence", "sequence_name",
    "samplename", "sample_name", "accession", "strain", "id", "taxon",
}
_CONTINUOUS_HINTS = {
    "value", "continuous", "time", "date", "age", "altitude", "elevation",
    "latitude", "longitude", "temperature", "depth", "size", "height", "weight",
    "mass", "count", "numeric", "日期", "时间", "株高", "高度", "体重", "重量", "温度",
}

_DATE_HINTS = ("date", "time", "日期", "时间", "采集日", "采样日")
_LENGTH_HINTS = (
    "height", "length", "altitude", "elevation", "depth", "size",
    "株高", "高度", "长度", "海拔", "深度",
)
_MASS_HINTS = ("weight", "mass", "biomass", "体重", "重量", "质量", "生物量")
_TEMPERATURE_HINTS = ("temperature", "temp", "温度")


def _normalize(text: str) -> str:
    return "".join(ch for ch in str(text).strip().lower() if ch.isalnum() or ch == "_")


def _guess_role(header: str, is_first: bool, name_taken: bool) -> str:
    key = _normalize(header)
    if not name_taken and (is_first or key in _NAME_HINTS):
        return ROLE_NAME
    typed_hints = _DATE_HINTS + _LENGTH_HINTS + _MASS_HINTS + _TEMPERATURE_HINTS
    if key in _CONTINUOUS_HINTS or any(hint in key for hint in typed_hints):
        return ROLE_CONTINUOUS
    return ROLE_DISCRETE


def _guess_transform(header: str, values: Sequence[str]) -> ContinuousTransform:
    """Conservatively suggest a conversion without silently changing units."""
    key = _normalize(header)
    non_blank = [str(value).strip() for value in values if str(value).strip()][:50]
    if non_blank and any(hint in key for hint in _DATE_HINTS):
        try:
            for value in non_blank:
                parse_date_value(value)
        except ContinuousTransformError:
            pass
        else:
            return ContinuousTransform(mode=MODE_DATE, date_unit=DATE_YEARS)

    suggestions = (
        (_LENGTH_HINTS, QUANTITY_LENGTH, "m"),
        (_MASS_HINTS, QUANTITY_MASS, "g"),
        (_TEMPERATURE_HINTS, QUANTITY_TEMPERATURE, "c"),
    )
    # Unit-bearing values are safe to infer. Bare numbers alone are left as
    # ordinary numbers because their source unit cannot be known reliably.
    def has_non_numeric_text(value: str) -> bool:
        try:
            float(value)
        except ValueError:
            return True
        return False

    has_suffix = any(has_non_numeric_text(value) for value in non_blank)
    if non_blank and has_suffix:
        for hints, quantity, unit in suggestions:
            if not any(hint in key for hint in hints):
                continue
            candidate = ContinuousTransform(
                mode=MODE_MEASUREMENT,
                quantity=quantity,
                target_unit=unit,
                bare_unit=unit,
            )
            try:
                transform_continuous_values(non_blank, candidate)
            except ContinuousTransformError:
                continue
            return candidate
    return ContinuousTransform()


class ContinuousTransformDialog(QDialog):
    """Configure and preview conversion of one continuous metadata column."""

    def __init__(
        self,
        column_name: str,
        values: Sequence[str],
        transform: ContinuousTransform,
        row_numbers: Optional[Sequence[int]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._column_name = column_name
        self._values = list(values)
        self._row_numbers = (
            list(row_numbers) if row_numbers is not None
            else list(range(2, len(self._values) + 2))
        )
        self.setWindowTitle(lang_manager.get(
            'dlg_transform_title', 'Convert Continuous Trait: {name}').format(
                name=column_name))
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)
        note = QLabel(lang_manager.get(
            'transform_hint',
            'Choose how source text is converted to numbers. Blank cells remain blank; '
            'the source file is not modified.'))
        note.setWordWrap(True)
        layout.addWidget(note)

        options_group = QGroupBox(lang_manager.get(
            'transform_options', 'Conversion rule'))
        form = QFormLayout(options_group)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem(lang_manager.get(
            'transform_number', 'Plain number'), MODE_NUMBER)
        self.mode_combo.addItem(lang_manager.get(
            'transform_date', 'Date / time'), MODE_DATE)
        self.mode_combo.addItem(lang_manager.get(
            'transform_measurement', 'Measurement with unit'), MODE_MEASUREMENT)
        form.addRow(lang_manager.get('transform_mode', 'Input type:'), self.mode_combo)

        self.date_unit_label = QLabel(lang_manager.get(
            'transform_date_unit', 'Output time unit:'))
        self.date_unit_combo = QComboBox()
        self.date_unit_combo.addItem(lang_manager.get('transform_days', 'Days'), DATE_DAYS)
        self.date_unit_combo.addItem(lang_manager.get('transform_months', 'Months'), DATE_MONTHS)
        self.date_unit_combo.addItem(lang_manager.get('transform_years', 'Years'), DATE_YEARS)
        form.addRow(self.date_unit_label, self.date_unit_combo)

        self.date_origin_label = QLabel(lang_manager.get(
            'transform_start_date', 'Start date:'))
        self.date_origin_edit = QLineEdit()
        self.date_origin_edit.setPlaceholderText(lang_manager.get(
            'transform_start_auto', 'Blank = earliest valid date'))
        form.addRow(self.date_origin_label, self.date_origin_edit)

        self.quantity_label = QLabel(lang_manager.get(
            'transform_quantity', 'Measurement type:'))
        self.quantity_combo = QComboBox()
        self.quantity_combo.addItem(lang_manager.get(
            'transform_length', 'Length'), QUANTITY_LENGTH)
        self.quantity_combo.addItem(lang_manager.get(
            'transform_mass', 'Mass'), QUANTITY_MASS)
        self.quantity_combo.addItem(lang_manager.get(
            'transform_temperature', 'Temperature'), QUANTITY_TEMPERATURE)
        form.addRow(self.quantity_label, self.quantity_combo)

        self.target_unit_label = QLabel(lang_manager.get(
            'transform_target_unit', 'Output unit:'))
        self.target_unit_combo = QComboBox()
        form.addRow(self.target_unit_label, self.target_unit_combo)

        self.bare_unit_label = QLabel(lang_manager.get(
            'transform_bare_unit', 'Unit for values without a suffix:'))
        self.bare_unit_combo = QComboBox()
        form.addRow(self.bare_unit_label, self.bare_unit_combo)
        layout.addWidget(options_group)

        preview_group = QGroupBox(lang_manager.get(
            'transform_preview', 'Conversion Preview'))
        preview_layout = QVBoxLayout(preview_group)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        preview_layout.addWidget(self.status_label)
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(2)
        self.preview_table.setHorizontalHeaderLabels([
            lang_manager.get('transform_preview_input', 'Source value'),
            lang_manager.get('transform_preview_output', 'Converted number'),
        ])
        self.preview_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        preview_layout.addWidget(self.preview_table)
        layout.addWidget(preview_group, 1)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.ok_button = QPushButton(lang_manager.get('btn_ok', 'OK'))
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton(lang_manager.get('btn_cancel', 'Cancel'))
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self._load_transform(transform)
        self.mode_combo.currentIndexChanged.connect(self._update_preview)
        self.date_unit_combo.currentIndexChanged.connect(self._update_preview)
        self.date_origin_edit.textChanged.connect(self._update_preview)
        self.quantity_combo.currentIndexChanged.connect(self._on_quantity_changed)
        self.target_unit_combo.currentIndexChanged.connect(self._update_preview)
        self.bare_unit_combo.currentIndexChanged.connect(self._update_preview)
        self._refresh_option_visibility()
        self._update_preview()

    def _load_transform(self, transform: ContinuousTransform) -> None:
        mode_index = self.mode_combo.findData(transform.mode)
        self.mode_combo.setCurrentIndex(max(0, mode_index))
        date_unit_index = self.date_unit_combo.findData(transform.date_unit)
        self.date_unit_combo.setCurrentIndex(max(0, date_unit_index))
        self.date_origin_edit.setText(transform.date_origin)
        quantity_index = self.quantity_combo.findData(transform.quantity)
        self.quantity_combo.setCurrentIndex(max(0, quantity_index))
        self._populate_units(transform.target_unit, transform.bare_unit)

    def _populate_units(self, target_unit: str = "", bare_unit: str = "") -> None:
        quantity = self.quantity_combo.currentData() or QUANTITY_LENGTH
        units = list(UNIT_DEFINITIONS[quantity])
        self.target_unit_combo.blockSignals(True)
        self.bare_unit_combo.blockSignals(True)
        self.target_unit_combo.clear()
        self.bare_unit_combo.clear()
        for unit in units:
            label = self._unit_label(unit)
            self.target_unit_combo.addItem(label, unit)
            self.bare_unit_combo.addItem(label, unit)
        target_index = self.target_unit_combo.findData(target_unit)
        bare_index = self.bare_unit_combo.findData(bare_unit)
        self.target_unit_combo.setCurrentIndex(max(0, target_index))
        self.bare_unit_combo.setCurrentIndex(max(0, bare_index))
        self.target_unit_combo.blockSignals(False)
        self.bare_unit_combo.blockSignals(False)

    @staticmethod
    def _unit_label(unit: str) -> str:
        return {'c': '°C', 'f': '°F', 'k': 'K'}.get(unit, unit)

    def _on_quantity_changed(self, *_args) -> None:
        defaults = {
            QUANTITY_LENGTH: "m",
            QUANTITY_MASS: "g",
            QUANTITY_TEMPERATURE: "c",
        }
        unit = defaults[self.quantity_combo.currentData()]
        self._populate_units(unit, unit)
        self._update_preview()

    def _refresh_option_visibility(self) -> None:
        mode = self.mode_combo.currentData()
        is_date = mode == MODE_DATE
        is_measurement = mode == MODE_MEASUREMENT
        for widget in (
            self.date_unit_label, self.date_unit_combo,
            self.date_origin_label, self.date_origin_edit,
        ):
            widget.setVisible(is_date)
        for widget in (
            self.quantity_label, self.quantity_combo,
            self.target_unit_label, self.target_unit_combo,
            self.bare_unit_label, self.bare_unit_combo,
        ):
            widget.setVisible(is_measurement)

    def transform(self) -> ContinuousTransform:
        return ContinuousTransform(
            mode=self.mode_combo.currentData(),
            date_unit=self.date_unit_combo.currentData(),
            date_origin=self.date_origin_edit.text().strip(),
            quantity=self.quantity_combo.currentData(),
            target_unit=self.target_unit_combo.currentData(),
            bare_unit=self.bare_unit_combo.currentData(),
        )

    def _update_preview(self, *_args) -> None:
        self._refresh_option_visibility()
        preview_values = self._values[:10]
        self.preview_table.setRowCount(len(preview_values))
        for row, value in enumerate(preview_values):
            self.preview_table.setItem(row, 0, QTableWidgetItem(str(value)))
            self.preview_table.setItem(row, 1, QTableWidgetItem(""))
        try:
            converted = transform_continuous_values(
                self._values,
                self.transform(),
                row_numbers=self._row_numbers,
            )
        except ContinuousTransformError as exc:
            self.status_label.setText(lang_manager.get(
                'msg_transform_invalid', 'Cannot convert this column: {error}').format(
                    error=str(exc)))
            self.status_label.setStyleSheet("color: #B42318;")
            self.ok_button.setEnabled(False)
            return

        for row, value in enumerate(converted[:10]):
            self.preview_table.setItem(row, 1, QTableWidgetItem(value))
        valid_count = sum(1 for value in converted if value != "")
        self.status_label.setText(lang_manager.get(
            'msg_transform_valid', '{count} non-empty values can be converted.').format(
                count=valid_count))
        self.status_label.setStyleSheet("color: #067647;")
        self.ok_button.setEnabled(True)


class CsvTraitsImportDialog(QDialog):
    """Dialog mapping metadata columns to sample-name / discrete / continuous."""

    def __init__(self, headers: List[str], data_rows: List[List[str]], parent=None):
        super().__init__(parent)
        self._headers = headers
        self._data_rows = data_rows
        self._preview_rows = data_rows[:5]
        self._role_combos: List[QComboBox] = []
        self._name_edits: List[QLineEdit] = []
        self._transform_buttons: List[QPushButton] = []
        self._transforms = [
            _guess_transform(header, [
                row[index] if index < len(row) else "" for row in data_rows
            ])
            for index, header in enumerate(headers)
        ]
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        self.setWindowTitle(lang_manager.get('dlg_csv_title', 'Import Metadata from File'))
        self.setMinimumSize(840, 560)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(14, 14, 14, 14)

        # ---- Column mapping ----
        mapping_group = QGroupBox(lang_manager.get('dlg_csv_mapping', 'Column Mapping'))
        mapping_outer = QVBoxLayout(mapping_group)
        hint = QLabel(lang_manager.get(
            'dlg_csv_hint',
            'Tag each column. Exactly one Sample Name and at least one Categorical '
            'trait (the group) are required.'))
        hint.setWordWrap(True)
        mapping_outer.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setSpacing(6)
        grid.addWidget(QLabel(lang_manager.get('dlg_csv_col_header', 'Column')), 0, 0)
        grid.addWidget(QLabel(lang_manager.get('dlg_csv_col_role', 'Role')), 0, 1)
        grid.addWidget(QLabel(lang_manager.get('dlg_csv_col_trait', 'Trait name')), 0, 2)
        grid.addWidget(QLabel(lang_manager.get(
            'dlg_csv_col_conversion', 'Continuous conversion')), 0, 3)

        role_items = [
            (lang_manager.get('role_ignore', 'Ignore'), ROLE_IGNORE),
            (lang_manager.get('role_name', 'Sample Name'), ROLE_NAME),
            (lang_manager.get('role_discrete', 'Categorical'), ROLE_DISCRETE),
            (lang_manager.get('role_continuous', 'Numeric'), ROLE_CONTINUOUS),
        ]
        name_taken = False
        for index, header in enumerate(self._headers):
            grid.addWidget(QLabel(str(header)), index + 1, 0)
            role_combo = QComboBox()
            for label, value in role_items:
                role_combo.addItem(label, value)
            guess = _guess_role(header, index == 0, name_taken)
            if guess == ROLE_NAME:
                name_taken = True
            role_combo.setCurrentIndex(
                next(i for i, (_, v) in enumerate(role_items) if v == guess))
            role_combo.currentIndexChanged.connect(
                lambda _value, column=index: self._on_role_changed(column))
            grid.addWidget(role_combo, index + 1, 1)
            self._role_combos.append(role_combo)

            name_edit = QLineEdit(str(header))
            name_edit.textChanged.connect(lambda _t: self._refresh_group_combo())
            grid.addWidget(name_edit, index + 1, 2)
            self._name_edits.append(name_edit)

            transform_button = QPushButton()
            transform_button.clicked.connect(
                lambda _checked=False, column=index: self._configure_transform(column))
            grid.addWidget(transform_button, index + 1, 3)
            self._transform_buttons.append(transform_button)

        scroll.setWidget(inner)
        mapping_outer.addWidget(scroll)

        # Group trait selector
        group_row = QHBoxLayout()
        group_row.addWidget(QLabel(lang_manager.get('dlg_csv_group', 'Group (inner ring) trait:')))
        self.group_combo = QComboBox()
        group_row.addWidget(self.group_combo, 1)
        mapping_outer.addLayout(group_row)

        main_layout.addWidget(mapping_group)

        # ---- Preview ----
        preview_group = QGroupBox(lang_manager.get('dlg_csv_preview', 'Data Preview (first rows)'))
        preview_layout = QVBoxLayout(preview_group)
        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.preview_table.setColumnCount(len(self._headers))
        self.preview_table.setHorizontalHeaderLabels([str(h) for h in self._headers])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.preview_table.setRowCount(len(self._preview_rows))
        for row_idx, row in enumerate(self._preview_rows):
            for col_idx in range(len(self._headers)):
                value = row[col_idx] if col_idx < len(row) else ""
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.preview_table.setItem(row_idx, col_idx, item)
        preview_layout.addWidget(self.preview_table)
        main_layout.addWidget(preview_group)

        # ---- Buttons ----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_ok = QPushButton(lang_manager.get('btn_ok', 'OK'))
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self._accept_if_valid)
        self.btn_cancel = QPushButton(lang_manager.get('btn_cancel', 'Cancel'))
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

        self._refresh_group_combo()
        for index in range(len(self._headers)):
            self._refresh_transform_button(index)

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def _discrete_trait_names(self) -> List[str]:
        names = []
        for combo, edit in zip(self._role_combos, self._name_edits):
            if combo.currentData() == ROLE_DISCRETE:
                name = edit.text().strip()
                if name:
                    names.append(name)
        return names

    def _refresh_group_combo(self):
        previous = self.group_combo.currentText()
        names = self._discrete_trait_names()
        self.group_combo.blockSignals(True)
        self.group_combo.clear()
        self.group_combo.addItems(names)
        if previous in names:
            self.group_combo.setCurrentText(previous)
        self.group_combo.blockSignals(False)

    def _on_role_changed(self, column: int) -> None:
        self._refresh_group_combo()
        self._refresh_transform_button(column)

    def _transform_summary(self, transform: ContinuousTransform) -> str:
        if transform.mode == MODE_DATE:
            unit = {
                DATE_DAYS: lang_manager.get('transform_days', 'Days'),
                DATE_MONTHS: lang_manager.get('transform_months', 'Months'),
                DATE_YEARS: lang_manager.get('transform_years', 'Years'),
            }[transform.date_unit]
            origin = transform.date_origin or lang_manager.get(
                'transform_earliest', 'earliest date')
            return lang_manager.get(
                'transform_summary_date', 'Date → {unit} ({origin})').format(
                    unit=unit, origin=origin)
        if transform.mode == MODE_MEASUREMENT:
            quantity = {
                QUANTITY_LENGTH: lang_manager.get('transform_length', 'Length'),
                QUANTITY_MASS: lang_manager.get('transform_mass', 'Mass'),
                QUANTITY_TEMPERATURE: lang_manager.get('transform_temperature', 'Temperature'),
            }[transform.quantity]
            return lang_manager.get(
                'transform_summary_measurement', '{quantity} → {unit}').format(
                    quantity=quantity,
                    unit=ContinuousTransformDialog._unit_label(transform.target_unit),
                )
        return lang_manager.get('transform_summary_number', 'Plain number')

    def _refresh_transform_button(self, column: int) -> None:
        enabled = self._role_combos[column].currentData() == ROLE_CONTINUOUS
        button = self._transform_buttons[column]
        button.setEnabled(enabled)
        button.setText(self._transform_summary(self._transforms[column]))

    def _usable_source_column(self, column: int):
        name_columns = [
            index for index, combo in enumerate(self._role_combos)
            if combo.currentData() == ROLE_NAME
        ]
        values = []
        row_numbers = []
        for row_number, row in enumerate(self._data_rows, start=2):
            if len(name_columns) == 1:
                name_index = name_columns[0]
                if name_index >= len(row) or not row[name_index].strip():
                    continue
            values.append(row[column] if column < len(row) else "")
            row_numbers.append(row_number)
        return values, row_numbers

    def _configure_transform(self, column: int) -> None:
        values, row_numbers = self._usable_source_column(column)
        dialog = ContinuousTransformDialog(
            self._name_edits[column].text().strip() or self._headers[column],
            values,
            self._transforms[column],
            row_numbers,
            self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._transforms[column] = dialog.transform()
            self._refresh_transform_button(column)

    def _accept_if_valid(self):
        name_cols = [i for i, c in enumerate(self._role_combos)
                     if c.currentData() == ROLE_NAME]
        if len(name_cols) != 1:
            self._warn(lang_manager.get(
                'msg_csv_need_one_name', 'Select exactly one Sample Name column.'))
            return

        trait_columns: List[TraitColumn] = []
        seen_names = set()
        for index, (combo, edit) in enumerate(zip(self._role_combos, self._name_edits)):
            role = combo.currentData()
            if role not in (ROLE_DISCRETE, ROLE_CONTINUOUS):
                continue
            name = edit.text().strip()
            if not name:
                self._warn(lang_manager.get(
                    'msg_csv_trait_name_empty', 'Every trait column needs a name.'))
                return
            if name in seen_names:
                self._warn(lang_manager.get(
                    'msg_csv_trait_name_dup', 'Trait names must be unique: {name}'
                ).format(name=name))
                return
            seen_names.add(name)
            kind = DISCRETE if role == ROLE_DISCRETE else CONTINUOUS
            transform = self._transforms[index] if kind == CONTINUOUS else None
            if transform is not None:
                values, row_numbers = self._usable_source_column(index)
                try:
                    transform_continuous_values(
                        values, transform, row_numbers=row_numbers)
                except ContinuousTransformError as exc:
                    self._warn(lang_manager.get(
                        'msg_csv_transform_invalid',
                        'Trait {name!r} cannot be converted: {error}').format(
                            name=name, error=str(exc)))
                    return
            trait_columns.append(TraitColumn(
                index=index, name=name, kind=kind, transform=transform))

        if not any(c.kind == DISCRETE for c in trait_columns):
            self._warn(lang_manager.get(
                'msg_csv_need_discrete',
                'At least one categorical trait is required to serve as the group.'))
            return

        self._mapping = MetadataMapping(
            name_col=name_cols[0],
            trait_columns=tuple(trait_columns),
            group_trait=self.group_combo.currentText() or None,
        )
        self.accept()

    def _warn(self, message: str):
        QMessageBox.warning(self, lang_manager.get('title_warning', 'Warning'), message)

    def get_mapping(self) -> Optional[MetadataMapping]:
        return getattr(self, "_mapping", None)

    # ------------------------------------------------------------------
    # Static factory
    # ------------------------------------------------------------------

    @staticmethod
    def get_column_mapping(headers, data_rows, parent=None) -> Optional[MetadataMapping]:
        dlg = CsvTraitsImportDialog(headers, data_rows, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.get_mapping()
        return None
