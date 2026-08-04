"""Structured result view for auxiliary haplotype-network analyses."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from service import interpretation_charts
from .language_manager import lang_manager

try:  # QtSvg ships with PyQt6 but guard so the tab still works without it.
    from PyQt6.QtSvgWidgets import QSvgWidget
except ImportError:  # pragma: no cover - depends on the runtime PyQt build
    QSvgWidget = None  # type: ignore[assignment]

try:  # WebEngine gives interactive (hover) charts; fall back to static SVG.
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover - depends on the runtime PyQt build
    QWebEngineView = None  # type: ignore[assignment]


class SvgFigureWidget(QSvgWidget if QSvgWidget else QWidget):  # type: ignore[misc]
    """Render one SVG figure, scaling its height to the available width."""

    def __init__(self, svg: str, parent=None, max_height: Optional[int] = None):
        super().__init__(parent)
        self._aspect = 0.4
        self._max_height = max_height
        if QSvgWidget is not None and svg:
            self.load(QByteArray(svg.encode("utf-8")))
            size = self.renderer().defaultSize()
            if size.width() > 0:
                self._aspect = size.height() / size.width()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._apply_height(max(self.width(), 1))

    def _apply_height(self, width: int) -> None:
        height = max(1, int(round(width * self._aspect)))
        if self._max_height is not None:
            height = min(height, self._max_height)
        if height != self.height():
            self.setFixedHeight(height)

    def resizeEvent(self, event):  # noqa: N802 - Qt override
        self._apply_height(event.size().width())
        super().resizeEvent(event)


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
        """Render a report: KPI cards, charts, summary, warnings and tables."""
        self.title_label.setText(str(report.get("title", "Analysis")))
        self.description_label.setText(str(report.get("description", "")))
        self._clear_tabs()

        self.tabs.addTab(
            self._build_overview(report),
            str(report.get("overview_title", "Overview")),
        )

        figures = list(report.get("figures", []))
        if figures:
            self.tabs.addTab(
                self._build_charts(figures),
                lang_manager.get("report_charts", "Visualizations"),
            )

        for table in report.get("tables", []):
            widget = self._make_table(table.get("columns", []), table.get("rows", []))
            self.tabs.addTab(widget, str(table.get("title", "Table")))

    def _clear_tabs(self) -> None:
        """Drop previous pages, deleting heavy children (e.g. web views)."""
        while self.tabs.count():
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            if widget is not None:
                widget.deleteLater()

    def _build_overview(self, report: Dict[str, Any]) -> QWidget:
        overview = QWidget()
        overview_layout = QVBoxLayout(overview)
        overview_layout.setContentsMargins(8, 8, 8, 8)
        overview_layout.setSpacing(10)

        cards = list(report.get("cards", []))
        if cards and QSvgWidget is not None:
            cards_svg = interpretation_charts.cards_svg(cards)
            if cards_svg:
                overview_layout.addWidget(
                    SvgFigureWidget(cards_svg, max_height=230))

        summary_rows = list(report.get("summary", []))
        summary = self._make_table(
            report.get("summary_columns", ["Metric", "Value"]), summary_rows
        )
        overview_layout.addWidget(summary, 1)

        messages = self._messages_html(report)
        if messages:
            message_view = QTextBrowser()
            message_view.setOpenExternalLinks(False)
            message_view.setHtml(messages)
            message_view.setMaximumHeight(190)
            overview_layout.addWidget(message_view)

        return overview

    def _messages_html(self, report: Dict[str, Any]) -> str:
        messages: List[str] = []
        warnings = list(report.get("warnings", []))
        notes = list(report.get("notes", []))
        if warnings:
            warning_title = self._escape(report.get("warnings_title", "Warnings"))
            messages.append(
                f"<h3 style='color:#9a6700'>{warning_title}</h3><ul>"
                + "".join(f"<li>{self._escape(value)}</li>" for value in warnings)
                + "</ul>"
            )
        if notes:
            notes_title = self._escape(
                report.get("notes_title", "Interpretation notes"))
            messages.append(
                f"<h3>{notes_title}</h3><ul>"
                + "".join(f"<li>{self._escape(value)}</li>" for value in notes)
                + "</ul>"
            )
        return "".join(messages)

    def _build_charts(self, figures: List[Dict[str, Any]]) -> QWidget:
        if QWebEngineView is not None:
            view = QWebEngineView()
            view.setHtml(interpretation_charts.figures_html(figures))
            return view
        return self._svg_charts_fallback(figures)

    def _svg_charts_fallback(self, figures: List[Dict[str, Any]]) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(6, 6, 6, 6)
        container_layout.setSpacing(14)
        for figure in figures:
            svg = figure.get("svg")
            if not svg or QSvgWidget is None:
                continue
            container_layout.addWidget(SvgFigureWidget(svg))
            desc = figure.get("desc")
            if desc:
                caption = QLabel(str(desc))
                caption.setWordWrap(True)
                caption.setStyleSheet("color:#6b7a82;font-size:12px;")
                container_layout.addWidget(caption)
        container_layout.addStretch(1)
        scroll.setWidget(container)
        return scroll

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
