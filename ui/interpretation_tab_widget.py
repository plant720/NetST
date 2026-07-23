"""Structured result view for auxiliary haplotype-network analyses."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .language_manager import lang_manager


class InterpretationTabWidget(QWidget):
    """Display one structured interpretation report without recomputing it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        self.title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color:#49606c;")
        layout.addWidget(self.description_label)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

    def set_report(self, report: Dict[str, Any]) -> None:
        """Render a report containing summary rows, warnings, notes and tables."""
        self.title_label.setText(str(report.get("title", "Analysis")))
        self.description_label.setText(str(report.get("description", "")))
        self.tabs.clear()

        overview = QWidget()
        overview_layout = QVBoxLayout(overview)
        overview_layout.setContentsMargins(8, 8, 8, 8)
        summary_rows = list(report.get("summary", []))
        summary = self._make_table(
            report.get("summary_columns", ["Metric", "Value"]), summary_rows
        )
        overview_layout.addWidget(summary)

        messages: List[str] = []
        warnings = list(report.get("warnings", []))
        notes = list(report.get("notes", []))
        if warnings:
            warning_title = self._escape(report.get("warnings_title", "Warnings"))
            messages.append(f"<h3 style='color:#9a6700'>{warning_title}</h3><ul>" + "".join(
                f"<li>{self._escape(value)}</li>" for value in warnings
            ) + "</ul>")
        if notes:
            notes_title = self._escape(
                report.get("notes_title", "Interpretation notes"))
            messages.append(f"<h3>{notes_title}</h3><ul>" + "".join(
                f"<li>{self._escape(value)}</li>" for value in notes
            ) + "</ul>")
        if messages:
            message_view = QTextBrowser()
            message_view.setOpenExternalLinks(False)
            message_view.setHtml("".join(messages))
            message_view.setMaximumHeight(190)
            overview_layout.addWidget(message_view)

        self.tabs.addTab(overview, str(report.get("overview_title", "Overview")))

        for table in report.get("tables", []):
            widget = self._make_table(table.get("columns", []), table.get("rows", []))
            self.tabs.addTab(widget, str(table.get("title", "Table")))

    @staticmethod
    def _make_table(columns: Iterable[Any], rows: Iterable[Iterable[Any]]) -> QTableWidget:
        columns = [str(value) for value in columns]
        rows = [list(row) for row in rows]
        table = QTableWidget(len(rows), len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        for row_index, row in enumerate(rows):
            for column_index in range(len(columns)):
                value = row[column_index] if column_index < len(row) else ""
                item = QTableWidgetItem(InterpretationTabWidget._display(value))
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                table.setItem(row_index, column_index, item)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if columns:
            header.setStretchLastSection(True)
        table.setSortingEnabled(bool(rows))
        return table

    @staticmethod
    def _display(value: Any) -> str:
        if value is None:
            return "—"
        if isinstance(value, float):
            if value != value:
                return "—"
            return f"{value:.6g}"
        if isinstance(value, bool):
            if lang_manager.get_language() == "cn":
                return "是" if value else "否"
            return "Yes" if value else "No"
        if isinstance(value, (list, tuple, set)):
            return "; ".join(str(item) for item in value)
        return str(value)

    @staticmethod
    def _escape(value: Any) -> str:
        return (str(value).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))
