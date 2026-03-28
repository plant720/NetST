"""
Haplotype Tab Widget — Displays haplotype analysis results.

Two tables are shown in a vertical splitter:
  Top:    Haplotype summary  (from <prefix>_hap_trait.csv)
            columns: Haplotype | Total Count | Discrete Traits | Samples
  Bottom: Sequence mapping   (from <prefix>_seq2hap.csv)
            columns: Sequence Name | Haplotype | Quantity | Continuous Traits | Discrete Traits

call load_result(output_path, prefix) after a successful analysis to refresh both tables.
"""

import csv
import os
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QLabel, QSplitter,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)


class HaplotypeTabWidget(QWidget):
    """Haplotype results tab: summary + sequence-to-haplotype mapping."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # One-line summary at the top (filled by load_result)
        self._summary_label = QLabel("No results loaded.")
        self._summary_label.setFont(QFont("Arial", 10))
        self._summary_label.setStyleSheet("color:#555;padding:4px;")
        layout.addWidget(self._summary_label)

        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)

        # ── Top pane: haplotype summary ──────────────────────────────────────
        top = QWidget()
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(2)
        top_layout.addWidget(self._section_header("Haplotype Summary"))
        self._hap_table = self._make_table(
            ["Haplotype", "Total Count", "Discrete Traits", "Samples"]
        )
        top_layout.addWidget(self._hap_table)
        splitter.addWidget(top)

        # ── Bottom pane: sequence → haplotype mapping ────────────────────────
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(2)
        bottom_layout.addWidget(self._section_header("Sequence → Haplotype Mapping"))
        self._seq_table = self._make_table(
            ["Sequence Name", "Haplotype", "Quantity", "Continuous Traits", "Discrete Traits"]
        )
        bottom_layout.addWidget(self._seq_table)
        splitter.addWidget(bottom)

        splitter.setSizes([280, 420])

    @staticmethod
    def _section_header(text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        label.setStyleSheet(
            "background:#E3F2FD;color:#1565C0;padding:4px 8px;border-radius:2px;"
        )
        return label

    @staticmethod
    def _make_table(headers: List[str]) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setShowGrid(True)
        h = table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        h.setStretchLastSection(True)
        table.verticalHeader().setDefaultSectionSize(24)
        table.verticalHeader().setVisible(False)
        return table

    # ── Public API ───────────────────────────────────────────────────────────

    def load_result(self, output_path: str, prefix: str) -> None:
        """Reload both tables from the latest analysis output files.

        Safe to call multiple times (e.g. after re-running the analysis).
        """
        hap_path = os.path.join(output_path, f"{prefix}_hap_trait.csv")
        seq_path = os.path.join(output_path, f"{prefix}_seq2hap.csv")

        hap_count = self._fill_hap_table(hap_path)
        seq_count = self._fill_seq_table(seq_path)

        self._summary_label.setText(
            f"Project: {prefix}    |    "
            f"Unique haplotypes: {hap_count}    |    "
            f"Total sequences: {seq_count}"
        )

    def clear(self) -> None:
        """Reset both tables (e.g. when a new project is opened)."""
        self._hap_table.setRowCount(0)
        self._seq_table.setRowCount(0)
        self._summary_label.setText("No results loaded.")

    # ── Private helpers ──────────────────────────────────────────────────────

    def _fill_hap_table(self, csv_path: str) -> int:
        """Populate the haplotype summary table; return the number of rows."""
        self._hap_table.setRowCount(0)
        if not os.path.isfile(csv_path):
            return 0

        rows: List[List[str]] = []
        try:
            with open(csv_path, encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    rows.append([
                        row.get("haplotype", ""),
                        row.get("total_quantity", ""),
                        row.get("discrete_traits", ""),
                        row.get("samples", ""),
                    ])
        except Exception:
            return 0

        self._hap_table.setRowCount(len(rows))
        for r, cols in enumerate(rows):
            for c, value in enumerate(cols):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._hap_table.setItem(r, c, item)
        self._hap_table.resizeColumnsToContents()
        return len(rows)

    def _fill_seq_table(self, csv_path: str) -> int:
        """Populate the sequence mapping table; return the number of rows."""
        self._seq_table.setRowCount(0)
        if not os.path.isfile(csv_path):
            return 0

        rows: List[List[str]] = []
        try:
            with open(csv_path, encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    rows.append([
                        row.get("sequence_name", ""),
                        row.get("haplotype", ""),
                        row.get("quantity", ""),
                        row.get("continuous_traits", ""),
                        row.get("discrete_traits", ""),
                    ])
        except Exception:
            return 0

        self._seq_table.setRowCount(len(rows))
        for r, cols in enumerate(rows):
            for c, value in enumerate(cols):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._seq_table.setItem(r, c, item)
        self._seq_table.resizeColumnsToContents()
        return len(rows)
