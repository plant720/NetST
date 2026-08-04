"""
Metadata tab: configure how each project trait is visualized.

One row per trait in the project's :class:`~model.trait_schema.TraitSchema`,
letting the user set its display type (categorical/numeric), pick the group,
toggle whether it is drawn as a ring, and edit colours by picker or hexadecimal
value. One built-in default palette/gradient is used; no Pattern or Theme
selector is exposed. The Apply button refreshes visualization configuration
without rebuilding network topology.
"""

from typing import Callable, List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QRadioButton, QButtonGroup, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QGridLayout, QColorDialog, QScrollArea, QSizePolicy,
    QMessageBox, QLineEdit,
)

from model.trait_schema import (
    CONTINUOUS, DISCRETE, TraitSchema, normalize_hex_color,
)
from .language_manager import lang_manager


class _DiscreteColorDialog(QDialog):
    """Per-category colour picker for one discrete trait."""

    def __init__(self, trait_name, categories, resolved, overrides, parent=None):
        super().__init__(parent)
        self.setWindowTitle(lang_manager.get('dlg_colors_title', 'Category Colours'))
        self.setMinimumWidth(320)
        self._overrides = dict(overrides)
        self._resolved = dict(resolved)
        self._buttons = {}
        self._edits = {}

        root = QVBoxLayout(self)
        root.addWidget(QLabel(f"{trait_name}"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        grid = QGridLayout(inner)
        for row, category in enumerate(categories):
            grid.addWidget(QLabel(str(category) or "(blank)"), row, 0)
            swatch = QPushButton()
            swatch.setFixedWidth(80)
            color = self._overrides.get(category, resolved.get(category, "#FFFFFF"))
            self._set_swatch(swatch, color)
            swatch.clicked.connect(lambda _c, cat=category, b=swatch: self._pick(cat, b))
            grid.addWidget(swatch, row, 1)
            hex_edit = QLineEdit(color)
            hex_edit.setPlaceholderText("#RRGGBB")
            hex_edit.setMaximumWidth(100)
            hex_edit.editingFinished.connect(
                lambda cat=category, edit=hex_edit, b=swatch:
                self._sync_hex(cat, edit, b))
            grid.addWidget(hex_edit, row, 2)
            self._buttons[category] = swatch
            self._edits[category] = hex_edit
        scroll.setWidget(inner)
        root.addWidget(scroll)

        buttons = QHBoxLayout()
        buttons.addStretch()
        reset = QPushButton(lang_manager.get('btn_reset', 'Reset'))
        reset.clicked.connect(self._reset)
        ok = QPushButton(lang_manager.get('btn_ok', 'OK'))
        ok.clicked.connect(self._accept_if_valid)
        cancel = QPushButton(lang_manager.get('btn_cancel', 'Cancel'))
        cancel.clicked.connect(self.reject)
        buttons.addWidget(reset)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    @staticmethod
    def _set_swatch(button, color):
        button.setText(color)
        button.setStyleSheet(
            f"background-color: {color}; color: {_contrast(color)};")

    def _pick(self, category, button):
        current_text = self._edits[category].text()
        current = QColor(normalize_hex_color(current_text) or "#FFFFFF")
        chosen = QColorDialog.getColor(current, self, lang_manager.get('dlg_colors_pick', 'Pick a colour'))
        if chosen.isValid():
            hexcolor = chosen.name().upper()
            self._overrides[category] = hexcolor
            self._edits[category].setText(hexcolor)
            self._set_swatch(button, hexcolor)

    def _sync_hex(self, category, edit, button):
        color = normalize_hex_color(edit.text())
        if color:
            edit.setText(color)
            edit.setStyleSheet("")
            self._overrides[category] = color
            self._set_swatch(button, color)
        else:
            edit.setStyleSheet("border: 1px solid #D32F2F;")

    def _accept_if_valid(self):
        overrides = {}
        for category, edit in self._edits.items():
            color = normalize_hex_color(edit.text())
            if color is None:
                QMessageBox.warning(
                    self, lang_manager.get('title_warning', 'Warning'),
                    lang_manager.get(
                        'msg_invalid_hex_color',
                        'Enter a valid hexadecimal colour such as #3B82F6.'))
                edit.setFocus()
                return
            if (
                category in self._overrides
                or color != normalize_hex_color(self._resolved.get(category))
            ):
                overrides[category] = color
        self._overrides = overrides
        self.accept()

    def _reset(self):
        self._overrides = {}
        self.accept()

    def overrides(self):
        return self._overrides


class _ContinuousColorDialog(QDialog):
    """Low/high endpoint picker for one continuous-trait gradient."""

    def __init__(self, trait_name, low, high, parent=None):
        super().__init__(parent)
        self.setWindowTitle(lang_manager.get(
            'dlg_gradient_title', 'Numeric Trait Gradient'))
        self.setMinimumWidth(360)
        self._colors = [low, high]
        self._reset_requested = False

        root = QVBoxLayout(self)
        root.addWidget(QLabel(str(trait_name)))
        grid = QGridLayout()
        self._buttons = []
        self._edits = []
        labels = [
            lang_manager.get('metadata_gradient_low', 'Low value'),
            lang_manager.get('metadata_gradient_high', 'High value'),
        ]
        for row, label in enumerate(labels):
            grid.addWidget(QLabel(label), row, 0)
            button = QPushButton()
            button.setMinimumWidth(120)
            self._set_swatch(button, self._colors[row])
            button.clicked.connect(
                lambda _checked=False, index=row: self._pick(index))
            grid.addWidget(button, row, 1)
            edit = QLineEdit(self._colors[row])
            edit.setPlaceholderText("#RRGGBB")
            edit.setMaximumWidth(100)
            edit.textChanged.connect(
                lambda _text, index=row: self._sync_hex(index))
            grid.addWidget(edit, row, 2)
            self._buttons.append(button)
            self._edits.append(edit)
        root.addLayout(grid)

        self.gradient_preview = QLabel()
        self.gradient_preview.setFixedHeight(30)
        root.addWidget(self.gradient_preview)
        self._update_gradient_preview()

        actions = QHBoxLayout()
        actions.addStretch()
        reset = QPushButton(lang_manager.get('btn_reset', 'Reset'))
        reset.clicked.connect(self._reset)
        ok = QPushButton(lang_manager.get('btn_ok', 'OK'))
        ok.clicked.connect(self._accept_if_valid)
        cancel = QPushButton(lang_manager.get('btn_cancel', 'Cancel'))
        cancel.clicked.connect(self.reject)
        actions.addWidget(reset)
        actions.addWidget(ok)
        actions.addWidget(cancel)
        root.addLayout(actions)

    @staticmethod
    def _set_swatch(button, color):
        button.setText(color)
        button.setStyleSheet(
            f"background-color: {color}; color: {_contrast(color)};")

    def _pick(self, index):
        chosen = QColorDialog.getColor(
            QColor(normalize_hex_color(self._edits[index].text())
                   or self._colors[index]), self,
            lang_manager.get('dlg_colors_pick', 'Pick a colour'))
        if chosen.isValid():
            self._colors[index] = chosen.name().upper()
            self._edits[index].setText(self._colors[index])
            self._set_swatch(self._buttons[index], self._colors[index])
            self._update_gradient_preview()

    def _sync_hex(self, index):
        color = normalize_hex_color(self._edits[index].text())
        if color:
            self._colors[index] = color
            self._edits[index].setStyleSheet("")
            self._set_swatch(self._buttons[index], color)
            self._update_gradient_preview()
        else:
            self._edits[index].setStyleSheet("border: 1px solid #D32F2F;")

    def _update_gradient_preview(self):
        low, high = self._colors
        self.gradient_preview.setStyleSheet(
            "border: 1px solid #888; border-radius: 3px;"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f" stop:0 {low}, stop:1 {high});")

    def _accept_if_valid(self):
        colors = [normalize_hex_color(edit.text()) for edit in self._edits]
        if any(color is None for color in colors):
            QMessageBox.warning(
                self, lang_manager.get('title_warning', 'Warning'),
                lang_manager.get(
                    'msg_invalid_hex_color',
                    'Enter a valid hexadecimal colour such as #3B82F6.'))
            return
        self._colors = colors
        self.accept()

    def _reset(self):
        self._reset_requested = True
        self.accept()

    def colors(self):
        return None if self._reset_requested else tuple(self._colors)


def _contrast(hexcolor: str) -> str:
    try:
        c = QColor(hexcolor)
        luminance = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
        return "#000000" if luminance > 140 else "#FFFFFF"
    except Exception:
        return "#000000"


class MetadataTabWidget(QWidget):
    """Trait-visualization configuration table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._schema = TraitSchema()
        self._category_provider: Optional[Callable[[str], List[str]]] = None
        self._apply_callback: Optional[Callable[[], None]] = None
        self._group_button_group = QButtonGroup(self)
        self._group_button_group.setExclusive(True)
        self._building = False
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        header = QHBoxLayout()
        self.title_label = QLabel(lang_manager.get(
            'metadata_tab_hint',
            'Sample-name, sequence, or topology changes require rebuilding the '
            'network. Trait type, group, visibility, and colour changes only '
            'refresh the visualization configuration.'))
        self.title_label.setWordWrap(True)
        header.addWidget(self.title_label, 1)
        self.apply_button = QPushButton(lang_manager.get(
            'btn_apply_metadata', 'Apply Visualization Config'))
        self.apply_button.clicked.connect(self._on_apply)
        header.addWidget(self.apply_button, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self._set_headers()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self.table)

    def _set_headers(self):
        self.table.setHorizontalHeaderLabels([
            lang_manager.get('metadata_col_trait', 'Trait'),
            lang_manager.get('metadata_col_type', 'Type'),
            lang_manager.get('metadata_col_group', 'Group'),
            lang_manager.get('metadata_col_visualize', 'Visualize'),
            lang_manager.get('metadata_col_colors', 'Colours'),
        ])

    # ── wiring ────────────────────────────────────────────────────────────────

    def set_apply_callback(self, callback: Callable[[], None]) -> None:
        self._apply_callback = callback

    def set_category_provider(self, provider: Callable[[str], List[str]]) -> None:
        self._category_provider = provider

    def set_schema(self, schema: TraitSchema) -> None:
        self._schema = schema
        self._rebuild()

    def schema(self) -> TraitSchema:
        return self._schema

    def update_language(self) -> None:
        self.title_label.setText(lang_manager.get('metadata_tab_hint', self.title_label.text()))
        self.apply_button.setText(lang_manager.get(
            'btn_apply_metadata', 'Apply Visualization Config'))
        self._set_headers()
        self._rebuild()

    # ── table build ─────────────────────────────────────────────────────────

    def _rebuild(self) -> None:
        self._building = True
        for button in list(self._group_button_group.buttons()):
            self._group_button_group.removeButton(button)
        definitions = self._schema.ordered()
        self.table.setRowCount(len(definitions))
        for row, definition in enumerate(definitions):
            # Trait name
            item = QTableWidgetItem(definition.name)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 0, item)

            # Type
            type_combo = QComboBox()
            type_combo.addItem(lang_manager.get('role_discrete', 'Categorical'), DISCRETE)
            type_combo.addItem(lang_manager.get('role_continuous', 'Numeric'), CONTINUOUS)
            type_combo.setCurrentIndex(0 if definition.kind == DISCRETE else 1)
            type_combo.currentIndexChanged.connect(
                lambda _i, name=definition.name, combo=type_combo: self._on_type_changed(name, combo))
            self.table.setCellWidget(row, 1, type_combo)

            # Group radio (discrete only)
            group_radio = QRadioButton()
            group_radio.setEnabled(definition.kind == DISCRETE)
            group_radio.setChecked(definition.is_group)
            group_radio.toggled.connect(
                lambda checked, name=definition.name: self._on_group_toggled(name, checked))
            self._group_button_group.addButton(group_radio)
            self.table.setCellWidget(row, 2, self._center(group_radio))

            # Visualize checkbox
            vis = QCheckBox()
            if definition.is_group:
                definition.visualize = True
            vis.setChecked(definition.visualize)
            vis.setEnabled(not definition.is_group)
            vis.toggled.connect(
                lambda checked, name=definition.name: self._on_visualize_toggled(name, checked))
            self.table.setCellWidget(row, 3, self._center(vis))

            # Colours button: category editor for discrete traits, low/high
            # endpoint picker for continuous traits.
            colors_button = QPushButton(lang_manager.get('metadata_edit_colors', 'Edit…'))
            if definition.kind == CONTINUOUS:
                low, high = definition.gradient_endpoints()
                colors_button.setText(f"{low}  →  {high}")
                colors_button.setStyleSheet(
                    "color: #111; font-weight: 600;"
                    "background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
                    f" stop:0 {low}, stop:1 {high});")
            colors_button.clicked.connect(
                lambda _c, name=definition.name: self._edit_colors(name))
            self.table.setCellWidget(row, 4, colors_button)
        self._building = False

    @staticmethod
    def _center(widget: QWidget) -> QWidget:
        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        layout.addWidget(widget)
        layout.addStretch()
        return holder

    # ── edits ─────────────────────────────────────────────────────────────────

    def _on_type_changed(self, name, combo):
        if self._building:
            return
        definition = self._schema.get(name)
        if definition is None:
            return
        new_kind = combo.currentData()
        if (
            definition.kind == DISCRETE
            and new_kind == CONTINUOUS
            and len(self._schema.discrete()) <= 1
        ):
            QMessageBox.warning(
                self,
                lang_manager.get('title_warning', 'Warning'),
                lang_manager.get(
                    'msg_metadata_keep_discrete',
                    'At least one categorical trait is required as the group.'),
            )
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
            return
        definition.kind = new_kind
        if definition.kind == CONTINUOUS:
            definition.is_group = False
        self._schema._normalize_group()
        # Defer the rebuild: it deletes the combo that is emitting this signal.
        QTimer.singleShot(0, self._rebuild)

    def _on_group_toggled(self, name, checked):
        if self._building or not checked:
            return
        try:
            self._schema.set_group(name)
        except ValueError:
            return
        QTimer.singleShot(0, self._rebuild)

    def _on_visualize_toggled(self, name, checked):
        if self._building:
            return
        definition = self._schema.get(name)
        if definition is not None:
            definition.visualize = bool(checked)

    def _edit_colors(self, name):
        definition = self._schema.get(name)
        if definition is None:
            return
        if definition.kind == DISCRETE:
            categories = self._category_provider(name) if self._category_provider else []
            if not categories:
                return
            resolved = definition.resolve_category_colors(categories)
            dialog = _DiscreteColorDialog(
                name, categories, resolved, definition.category_colors, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                definition.category_colors = dialog.overrides()
        else:
            low, high = definition.gradient_endpoints()
            dialog = _ContinuousColorDialog(name, low, high, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                colors = dialog.colors()
                if colors is None:
                    definition.clear_custom_gradient()
                else:
                    definition.gradient_low, definition.gradient_high = colors
                self._rebuild()

    def _on_apply(self):
        if self._apply_callback:
            self._apply_callback()
