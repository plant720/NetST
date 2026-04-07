"""
Alignment Tab Widget — Displays multiple sequence alignment results.

Layout:
  Top:    Summary label (file name, sequence count, positions)
          Info label (full file path)
  Main:   Horizontal splitter:
            Left:  QTableWidget — Sequence Name column
            Right: Nucleotide sequence viewer — one column per position,
                   color-coded by base (A/T/C/G); rows stay in sync with left table

For long alignments (> 500 positions) only variable (informative) sites are
shown, with the total and variable counts reported in the summary.
"""

import os
from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QLabel, QSplitter,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

# ── Nucleotide colour scheme  (background, foreground) ──────────────────────
_BASE_STYLE = {
    'A': ('#C8E6C9', '#1B5E20'),   # green
    'T': ('#FFCDD2', '#B71C1C'),   # red
    'C': ('#BBDEFB', '#0D47A1'),   # blue
    'G': ('#E1BEE7', '#4A148C'),   # purple
    '-': ('#F5F5F5', '#9E9E9E'),   # gap – grey
    'N': ('#FFF9C4', '#E65100'),   # ambiguous – amber
}
_DEFAULT_STYLE: Tuple[str, str] = ('#FAFAFA', '#333333')

# Show all positions up to this length; beyond it only variable sites are shown.
_MAX_FULL_POSITIONS = 500


class AlignmentTabWidget(QWidget):
    """Alignment results tab: color-coded view of an aligned FASTA file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sequences: List[Tuple[str, str]] = []   # (name, sequence)
        self._display_positions: List[int] = []
        self._setup_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        self._summary_label = QLabel("No alignment loaded.")
        self._summary_label.setFont(QFont("Arial", 10))
        self._summary_label.setStyleSheet("color:#555;padding:4px;")
        layout.addWidget(self._summary_label)

        self._info_label = QLabel("")
        self._info_label.setFont(QFont("Arial", 9))
        self._info_label.setStyleSheet("color:#888;padding:2px 4px;")
        layout.addWidget(self._info_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        self._name_table = self._make_name_table()
        splitter.addWidget(self._name_table)

        self._seq_viewer = self._make_seq_viewer()
        splitter.addWidget(self._seq_viewer)

        splitter.setSizes([220, 900])

        # Synchronise vertical scrolling between the two tables
        self._name_table.verticalScrollBar().valueChanged.connect(
            self._seq_viewer.verticalScrollBar().setValue
        )
        self._seq_viewer.verticalScrollBar().valueChanged.connect(
            self._name_table.verticalScrollBar().setValue
        )

    @staticmethod
    def _make_name_table() -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(1)
        t.setHorizontalHeaderLabels(["Sequence Name"])
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setAlternatingRowColors(True)
        t.setShowGrid(True)
        t.setSortingEnabled(False)
        t.verticalHeader().setDefaultSectionSize(24)
        t.verticalHeader().setVisible(False)
        h = t.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        h.setSectionsClickable(False)
        t.setFont(QFont("Arial", 9))
        return t

    @staticmethod
    def _make_seq_viewer() -> QTableWidget:
        t = QTableWidget()
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setShowGrid(True)
        t.setSortingEnabled(False)
        t.verticalHeader().setDefaultSectionSize(24)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setDefaultSectionSize(20)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        t.setFont(QFont("Courier New", 9))
        return t

    # ── Public API ───────────────────────────────────────────────────────────

    def load_alignment(self, fasta_path: str) -> None:
        """Load and display an aligned FASTA file.

        Safe to call multiple times — each call fully replaces the previous data.
        """
        self._sequences.clear()
        self._display_positions.clear()
        self._name_table.setRowCount(0)
        self._seq_viewer.setRowCount(0)
        self._seq_viewer.setColumnCount(0)

        if not fasta_path or not os.path.isfile(fasta_path):
            self._summary_label.setText("Alignment file not found.")
            self._info_label.setText(fasta_path or "")
            return

        # Parse aligned FASTA
        try:
            current: Optional[str] = None
            buf: List[str] = []
            with open(fasta_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('>'):
                        if current is not None and buf:
                            self._sequences.append((current, ''.join(buf).upper()))
                        current = line[1:].strip()
                        buf = []
                    else:
                        buf.append(line)
                if current is not None and buf:
                    self._sequences.append((current, ''.join(buf).upper()))
        except Exception:
            self._summary_label.setText("Failed to read alignment file.")
            self._info_label.setText(fasta_path)
            return

        if not self._sequences:
            self._summary_label.setText("No sequences found in alignment file.")
            self._info_label.setText(fasta_path)
            return

        seq_len = max(len(s) for _, s in self._sequences)
        n_seqs = len(self._sequences)

        if n_seqs == 1 or seq_len <= _MAX_FULL_POSITIONS:
            self._display_positions = list(range(seq_len))
            pos_note = f"{seq_len} positions"
        else:
            seqs_only = [s for _, s in self._sequences]
            self._display_positions = [
                i for i in range(seq_len)
                if len({s[i] if i < len(s) else '?' for s in seqs_only}) > 1
            ]
            if not self._display_positions:
                self._display_positions = list(range(seq_len))
            pos_note = f"{seq_len} positions ({len(self._display_positions)} variable shown)"

        self._summary_label.setText(
            f"Alignment: {os.path.basename(fasta_path)}    |    "
            f"Sequences: {n_seqs}    |    "
            f"{pos_note}"
        )
        self._info_label.setText(f"Source: {fasta_path}")

        self._render()

    def clear(self) -> None:
        """Reset the widget (e.g. when opening a new project)."""
        self._sequences.clear()
        self._display_positions.clear()
        self._name_table.setRowCount(0)
        self._seq_viewer.setRowCount(0)
        self._seq_viewer.setColumnCount(0)
        self._summary_label.setText("No alignment loaded.")
        self._info_label.setText("")

    # ── Private rendering ────────────────────────────────────────────────────

    def _render(self) -> None:
        if not self._sequences or not self._display_positions:
            return

        n_rows = len(self._sequences)
        n_cols = len(self._display_positions)

        # Left: sequence name column
        self._name_table.setRowCount(n_rows)
        for r, (name, _) in enumerate(self._sequences):
            item = QTableWidgetItem(name)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setToolTip(name)
            self._name_table.setItem(r, 0, item)

        # Right: nucleotide grid
        self._seq_viewer.setUpdatesEnabled(False)
        self._seq_viewer.setRowCount(n_rows)
        self._seq_viewer.setColumnCount(n_cols)
        self._seq_viewer.setHorizontalHeaderLabels(
            [str(p + 1) for p in self._display_positions]
        )

        for r, (_, seq) in enumerate(self._sequences):
            for c, pos in enumerate(self._display_positions):
                base = seq[pos] if pos < len(seq) else '?'
                bg, fg = _BASE_STYLE.get(base, _DEFAULT_STYLE)

                item = QTableWidgetItem(base)
                item.setForeground(QBrush(QColor(fg)))
                item.setBackground(QBrush(QColor(bg)))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setToolTip(f"Position {pos + 1}: {base}")
                self._seq_viewer.setItem(r, c, item)

        self._seq_viewer.setUpdatesEnabled(True)
