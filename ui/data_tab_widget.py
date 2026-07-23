"""
Data Table Tab Widget Module

Provides the data table tab widget for displaying and editing sequence data.
"""

from typing import Optional, Callable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QPushButton, QLabel, QHeaderView, QAbstractItemView, QFrame
)


class DataTabWidget(QWidget):
    """
    Data Table Tab Widget Class
    
    Provides a complete data table display interface including:
    - Toolbar with select all/deselect buttons and selected count display
    - Data table view
    """

    selection_changed = pyqtSignal()
    DEFAULT_COLUMN_WIDTHS = [50, 50, 120, 400, 120, 120, 60, 120]

    def __init__(self, parent: QWidget = None):
        """Initialize the data table tab widget"""
        super().__init__(parent)

        self.table_view: Optional[QTableView] = None
        self.btn_select_all: Optional[QPushButton] = None
        self.btn_deselect_all: Optional[QPushButton] = None
        self.selected_count_label: Optional[QLabel] = None
        self.total_count_label: Optional[QLabel] = None
        self._count_caption_label: Optional[QLabel] = None

        self._select_all_callback: Optional[Callable] = None
        self._deselect_all_callback: Optional[Callable] = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        self.table_view = self._create_table_view()
        layout.addWidget(self.table_view)

    def _create_toolbar(self) -> QFrame:
        """Create toolbar"""
        toolbar_frame = QFrame()
        toolbar_frame.setFrameShape(QFrame.Shape.StyledPanel)
        toolbar_frame.setFrameShadow(QFrame.Shadow.Raised)

        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(5, 3, 5, 3)

        from .language_manager import lang_manager

        # Select All button
        self.btn_select_all = QPushButton(lang_manager.get('btn_select_all', 'Select All'))
        self.btn_select_all.clicked.connect(self._on_select_all)
        toolbar_layout.addWidget(self.btn_select_all)

        # Deselect All button
        self.btn_deselect_all = QPushButton(lang_manager.get('btn_deselect_all', 'Deselect All'))
        self.btn_deselect_all.clicked.connect(self._on_deselect_all)
        toolbar_layout.addWidget(self.btn_deselect_all)

        toolbar_layout.addStretch()

        # Selected count display
        self._count_caption_label = QLabel(lang_manager.get('label_selected', 'Selected:'))
        toolbar_layout.addWidget(self._count_caption_label)

        self.selected_count_label = QLabel("0")
        self.selected_count_label.setMinimumWidth(30)
        self.selected_count_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.selected_count_label.setStyleSheet("color: #2196F3;")
        toolbar_layout.addWidget(self.selected_count_label)

        separator_label = QLabel("/")
        toolbar_layout.addWidget(separator_label)

        self.total_count_label = QLabel("0")
        self.total_count_label.setMinimumWidth(30)
        toolbar_layout.addWidget(self.total_count_label)

        return toolbar_frame

    def _create_table_view(self) -> QTableView:
        """Create data table view"""
        table_view = QTableView()

        table_view.setAlternatingRowColors(True)
        table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table_view.setSortingEnabled(False)
        table_view.setShowGrid(True)

        header = table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)

        table_view.verticalHeader().setDefaultSectionSize(25)
        table_view.verticalHeader().setVisible(False)

        return table_view

    def set_model(self, model):
        """Set data model"""
        self.table_view.setModel(model)
        model.dataChanged.connect(self._on_data_changed)
        model.layoutChanged.connect(self._on_layout_changed)
        self._apply_column_widths()

    def _apply_column_widths(self):
        """Apply default column width settings"""
        model = self.table_view.model()
        if model:
            for i, width in enumerate(self.DEFAULT_COLUMN_WIDTHS):
                if i < model.columnCount():
                    self.table_view.setColumnWidth(i, width)

    def set_select_all_callback(self, callback: Callable):
        """Set select all callback function"""
        self._select_all_callback = callback

    def set_deselect_all_callback(self, callback: Callable):
        """Set deselect all callback function"""
        self._deselect_all_callback = callback

    def _on_select_all(self):
        """Select all button click handler"""
        if self._select_all_callback:
            self._select_all_callback()

    def _on_deselect_all(self):
        """Deselect all button click handler"""
        if self._deselect_all_callback:
            self._deselect_all_callback()

    def _on_data_changed(self, *args):
        """Data changed handler"""
        self.selection_changed.emit()

    def _on_layout_changed(self):
        """Layout changed handler"""
        self.update_counts()

    def update_counts(self, selected: int = None, total: int = None):
        """Update count display"""
        model = self.table_view.model()

        if selected is not None:
            self.selected_count_label.setText(str(selected))

        if total is not None:
            self.total_count_label.setText(str(total))
        elif model:
            self.total_count_label.setText(str(model.rowCount()))

    def update_language(self):
        """Update interface language"""
        from .language_manager import lang_manager
        self.btn_select_all.setText(lang_manager.get('btn_select_all'))
        self.btn_deselect_all.setText(lang_manager.get('btn_deselect_all'))
        if self._count_caption_label:
            self._count_caption_label.setText(lang_manager.get('label_selected'))
