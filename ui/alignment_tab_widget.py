"""
Alignment Tab Widget — Displays multiple sequence alignment results.

Layout:
  Top:    Summary label (file name, sequence count, positions)
          Info label (full file path; also directs the user to the source
                      FASTA file when the alignment is truncated in the UI)
  Main:   Horizontal splitter:
            Left:  QTableWidget — Sequence Name column
            Right: Nucleotide sequence viewer — one column per position,
                   color-coded by base (A/T/C/G); rows stay in sync with left table

Only the first _MAX_DISPLAY_POSITIONS columns of the alignment are rendered.
For longer alignments the user is directed to the aligned FASTA file on disk
instead of loading additional positions into the UI — this keeps parsing and
rendering cheap regardless of input size.

File parsing is split from UI rendering (parse_alignment_data is a pure
threadsafe function; apply_data populates Qt widgets on the main thread) so
the tab can be populated asynchronously from a background worker.
"""

import os
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QLabel, QSplitter,
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

# Only the first N positions are ever rendered. For longer alignments the user
# is directed to the source FASTA file rather than loading more into the UI.
_MAX_DISPLAY_POSITIONS = 500


class AlignmentTabWidget(QWidget):
    """Alignment results tab: color-coded view of an aligned FASTA file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sequences: List[Tuple[str, str]] = []  # (name, sequence)
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
        self._info_label.setWordWrap(True)
        self._info_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
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

    @staticmethod
    def parse_alignment_data(fasta_path: str) -> Dict[str, Any]:
        """Parse an aligned FASTA file into plain Python data.

        Threadsafe: touches no Qt objects, so it is safe to call from a
        QThread. The returned dict is consumed by apply_data() on the main
        thread. Only the first _MAX_DISPLAY_POSITIONS columns are kept for
        display; the parser does not scan the full alignment for variable
        sites, which keeps parsing O(N_seqs * 500) regardless of length.
        """
        result: Dict[str, Any] = {
            "fasta_path": fasta_path or "",
            "sequences": [],            # List[Tuple[str, str]]
            "display_positions": [],    # List[int]
            "summary": "No alignment loaded.",
            "info": fasta_path or "",
            "seq_len": 0,
            "n_seqs": 0,
            "truncated": False,
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

        display_len = min(seq_len, _MAX_DISPLAY_POSITIONS)
        display_positions = list(range(display_len))
        truncated = seq_len > _MAX_DISPLAY_POSITIONS

        if truncated:
            pos_note = (
                f"{seq_len} positions (showing first {display_len})"
            )
            info_text = (
                f"Source: {fasta_path}\n"
                f"Only the first {display_len} positions are shown here to keep the view "
                f"responsive. Open the file above for the complete alignment."
            )
        else:
            pos_note = f"{seq_len} positions"
            info_text = f"Source: {fasta_path}"

        result["sequences"] = sequences
        result["display_positions"] = display_positions
        result["seq_len"] = seq_len
        result["n_seqs"] = n_seqs
        result["truncated"] = truncated
        result["summary"] = (
            f"Alignment: {os.path.basename(fasta_path)}    |    "
            f"Sequences: {n_seqs}    |    {pos_note}"
        )
        result["info"] = info_text
        return result

    def apply_data(self, data: Dict[str, Any]) -> None:
        """Populate the widget from a parse_alignment_data() result."""
        self._sequences = list(data.get("sequences", []))
        self._display_positions = list(data.get("display_positions", []))

        self._summary_label.setText(data.get("summary", ""))
        self._info_label.setText(data.get("info", ""))

        self._name_table.setRowCount(0)
        self._seq_viewer.setRowCount(0)
        self._seq_viewer.setColumnCount(0)

        if not self._sequences or not self._display_positions:
            return

        self._render()

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
        self._name_table.setRowCount(0)
        self._seq_viewer.setRowCount(0)
        self._seq_viewer.setColumnCount(0)
        self._summary_label.setText("No alignment loaded.")
        self._info_label.setText("")

    # ── Private rendering ────────────────────────────────────────────────────

    def _render(self) -> None:
        """Render the name column and the (capped) sequence viewer."""
        n_rows = len(self._sequences)
        n_cols = len(self._display_positions)

        # Left: sequence name column — all rows
        self._name_table.setRowCount(n_rows)
        for r, (name, _) in enumerate(self._sequences):
            item = QTableWidgetItem(name)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setToolTip(name)
            self._name_table.setItem(r, 0, item)

        # Right: nucleotide grid, capped at _MAX_DISPLAY_POSITIONS columns.
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
