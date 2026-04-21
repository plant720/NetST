"""
Alignment Tab Widget — Displays multiple sequence alignment results.

Layout:
  Top:    Summary label (file name, sequence count, positions)
          Info label (full file path)
          Load-more button (only visible when additional positions are hidden)
  Main:   Horizontal splitter:
            Left:  QTableWidget — Sequence Name column
            Right: Nucleotide sequence viewer — one column per position,
                   color-coded by base (A/T/C/G); rows stay in sync with left table

For long alignments (> 500 positions) only variable (informative) sites are
selected for display; when the selection still exceeds 1000 columns the view
initially shows only the first 1000 and the remainder is loaded lazily when
the user clicks "Load more".

File parsing is split from UI rendering (parse_alignment_data is a pure
threadsafe function; apply_data populates Qt widgets on the main thread) so
the tab can be populated asynchronously from a background worker.
"""

import os
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QLabel, QPushButton, QSplitter,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

# ── Nucleotide colour scheme  (background, foreground) ──────────────────────
_BASE_STYLE = {
    'A': ('#C8E6C9', '#1B5E20'),  # green
    'T': ('#FFCDD2', '#B71C1C'),  # red
    'C': ('#BBDEFB', '#0D47A1'),  # blue
    'G': ('#E1BEE7', '#4A148C'),  # purple
    '-': ('#F5F5F5', '#9E9E9E'),  # gap – grey
    'N': ('#FFF9C4', '#E65100'),  # ambiguous – amber
}
_DEFAULT_STYLE: Tuple[str, str] = ('#FAFAFA', '#333333')

# Show all positions up to this length; beyond it only variable sites are shown.
_MAX_FULL_POSITIONS = 500
# Initial positions rendered when the display list exceeds this size; the rest
# is loaded on demand via the "Load more" button.
_LAZY_LOAD_CHUNK = 1000


class AlignmentTabWidget(QWidget):
    """Alignment results tab: color-coded view of an aligned FASTA file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sequences: List[Tuple[str, str]] = []  # (name, sequence)
        self._display_positions: List[int] = []
        self._rendered_count: int = 0  # how many columns are currently in the viewer
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

        self._load_more_btn = QPushButton("Load more positions")
        self._load_more_btn.setStyleSheet(
            "QPushButton {"
            "  background:#E3F2FD;color:#1565C0;border:1px solid #90CAF9;"
            "  padding:4px 10px;border-radius:3px;"
            "}"
            "QPushButton:hover { background:#BBDEFB; }"
        )
        self._load_more_btn.clicked.connect(self._load_more)
        self._load_more_btn.setVisible(False)
        layout.addWidget(self._load_more_btn)

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

    @staticmethod
    def parse_alignment_data(fasta_path: str) -> Dict[str, Any]:
        """Parse an aligned FASTA file into plain Python data.

        Threadsafe: touches no Qt objects, so it is safe to call from a
        QThread. The returned dict is consumed by apply_data() on the main
        thread.
        """
        result: Dict[str, Any] = {
            "fasta_path": fasta_path or "",
            "sequences": [],            # List[Tuple[str, str]]
            "display_positions": [],    # List[int]
            "summary": "No alignment loaded.",
            "info": fasta_path or "",
            "seq_len": 0,
            "n_seqs": 0,
            "error": None,              # Optional[str]
        }

        if not fasta_path or not os.path.isfile(fasta_path):
            result["summary"] = "Alignment file not found."
            result["error"] = "not_found"
            return result

        sequences: List[Tuple[str, str]] = []
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
                            sequences.append((current, ''.join(buf).upper()))
                        current = line[1:].strip()
                        buf = []
                    else:
                        buf.append(line)
                if current is not None and buf:
                    sequences.append((current, ''.join(buf).upper()))
        except Exception as e:
            result["summary"] = "Failed to read alignment file."
            result["info"] = fasta_path
            result["error"] = f"read_error: {e}"
            return result

        if not sequences:
            result["summary"] = "No sequences found in alignment file."
            result["info"] = fasta_path
            result["error"] = "empty"
            return result

        seq_len = max(len(s) for _, s in sequences)
        n_seqs = len(sequences)

        if n_seqs == 1 or seq_len <= _MAX_FULL_POSITIONS:
            display_positions = list(range(seq_len))
            pos_note = f"{seq_len} positions"
        else:
            seqs_only = [s for _, s in sequences]
            display_positions = [
                i for i in range(seq_len)
                if len({s[i] if i < len(s) else '?' for s in seqs_only}) > 1
            ]
            if not display_positions:
                display_positions = list(range(seq_len))
            pos_note = f"{seq_len} positions ({len(display_positions)} variable shown)"

        result["sequences"] = sequences
        result["display_positions"] = display_positions
        result["seq_len"] = seq_len
        result["n_seqs"] = n_seqs
        result["summary"] = (
            f"Alignment: {os.path.basename(fasta_path)}    |    "
            f"Sequences: {n_seqs}    |    {pos_note}"
        )
        result["info"] = f"Source: {fasta_path}"
        return result

    def apply_data(self, data: Dict[str, Any]) -> None:
        """Populate the widget from a parse_alignment_data() result."""
        self._sequences = list(data.get("sequences", []))
        self._display_positions = list(data.get("display_positions", []))
        self._rendered_count = 0

        self._summary_label.setText(data.get("summary", ""))
        self._info_label.setText(data.get("info", ""))

        self._name_table.setRowCount(0)
        self._seq_viewer.setRowCount(0)
        self._seq_viewer.setColumnCount(0)
        self._load_more_btn.setVisible(False)

        if not self._sequences or not self._display_positions:
            return

        self._render_initial()

    def load_alignment(self, fasta_path: str) -> None:
        """Load and display an aligned FASTA file (synchronous).

        Kept for callers that want to parse + render in the current thread.
        Background/async callers should use parse_alignment_data() followed by
        apply_data() on the main thread.
        """
        self.apply_data(self.parse_alignment_data(fasta_path))

    def clear(self) -> None:
        """Reset the widget (e.g. when opening a new project)."""
        self._sequences.clear()
        self._display_positions.clear()
        self._rendered_count = 0
        self._name_table.setRowCount(0)
        self._seq_viewer.setRowCount(0)
        self._seq_viewer.setColumnCount(0)
        self._load_more_btn.setVisible(False)
        self._summary_label.setText("No alignment loaded.")
        self._info_label.setText("")

    # ── Private rendering ────────────────────────────────────────────────────

    def _render_initial(self) -> None:
        """Render name column and the first chunk of the sequence viewer."""
        n_rows = len(self._sequences)
        n_cols_total = len(self._display_positions)

        # Left: sequence name column — rendered once, all rows
        self._name_table.setRowCount(n_rows)
        for r, (name, _) in enumerate(self._sequences):
            item = QTableWidgetItem(name)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setToolTip(name)
            self._name_table.setItem(r, 0, item)

        # Right: size the grid once to the final column count, then fill the
        # first chunk. This avoids re-sizing on every "Load more" click.
        self._seq_viewer.setUpdatesEnabled(False)
        self._seq_viewer.setRowCount(n_rows)
        self._seq_viewer.setColumnCount(n_cols_total)
        self._seq_viewer.setHorizontalHeaderLabels(
            [str(p + 1) for p in self._display_positions]
        )
        self._seq_viewer.setUpdatesEnabled(True)

        first_chunk = min(_LAZY_LOAD_CHUNK, n_cols_total)
        self._render_range(0, first_chunk)
        self._rendered_count = first_chunk

        self._update_load_more_button()

    def _render_range(self, start: int, stop: int) -> None:
        """Populate viewer cells for display_positions[start:stop]."""
        if start >= stop:
            return

        self._seq_viewer.setUpdatesEnabled(False)
        for r, (_, seq) in enumerate(self._sequences):
            for c in range(start, stop):
                pos = self._display_positions[c]
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

    def _load_more(self) -> None:
        """User-triggered render of the next chunk of hidden positions."""
        n_total = len(self._display_positions)
        if self._rendered_count >= n_total:
            self._load_more_btn.setVisible(False)
            return
        stop = min(self._rendered_count + _LAZY_LOAD_CHUNK, n_total)
        self._render_range(self._rendered_count, stop)
        self._rendered_count = stop
        self._update_load_more_button()

    def _update_load_more_button(self) -> None:
        remaining = len(self._display_positions) - self._rendered_count
        if remaining <= 0:
            self._load_more_btn.setVisible(False)
            return
        next_chunk = min(_LAZY_LOAD_CHUNK, remaining)
        self._load_more_btn.setText(
            f"Load more positions  ({self._rendered_count}/"
            f"{len(self._display_positions)} shown, +{next_chunk})"
        )
        self._load_more_btn.setVisible(True)
