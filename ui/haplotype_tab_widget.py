"""
Haplotype Tab Widget — Displays haplotype analysis results.

Layout (vertical outer splitter):
  Top:    Haplotype Summary
          Info label (directs the user to the output files when the aligned
                      haplotype sequence is truncated in the UI)
            Horizontal inner splitter:
              Left:  QTableWidget — Haplotype | Total Count | Samples
              Right: Nucleotide sequence viewer — one column per position,
                     color-coded by base (A/T/C/G); rows stay in sync with left table
  Bottom: Sequence → Haplotype Mapping — Sequence Name | Haplotype

Only the first _MAX_DISPLAY_POSITIONS columns of each haplotype sequence are
rendered. For longer alignments the user is directed to the output files on
disk (e.g. ``{prefix}_hap.fasta``) instead of loading additional positions
into the UI — this keeps parsing and rendering cheap regardless of length.

File parsing is split from UI rendering (parse_result_data is a pure
threadsafe function; apply_data populates Qt widgets on the main thread) so
the tab can be populated asynchronously from a background worker.

Tooltips: every cell shows its full text on hover.
Sorting:  disabled — column headers are not clickable for sorting.
"""

import csv
import os
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QLabel, QSplitter,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

# ── Nucleotide colour scheme  (background, foreground) ──────────────────────
_BASE_STYLE: Dict[str, Tuple[str, str]] = {
    'A': ('#C8E6C9', '#1B5E20'),  # green
    'T': ('#FFCDD2', '#B71C1C'),  # red
    'C': ('#BBDEFB', '#0D47A1'),  # blue
    'G': ('#E1BEE7', '#4A148C'),  # purple
    '-': ('#F5F5F5', '#9E9E9E'),  # gap – grey
    'N': ('#FFF9C4', '#E65100'),  # ambiguous – amber
}
_DEFAULT_STYLE: Tuple[str, str] = ('#FAFAFA', '#333333')

# Only the first N positions are ever rendered. For longer alignments the user
# is directed to the output files on disk rather than loading more into the UI.
_MAX_DISPLAY_POSITIONS = 500


# ── Helpers ──────────────────────────────────────────────────────────────────

def _plain_item(value: str) -> QTableWidgetItem:
    """Read-only item whose tooltip shows the full text (handles long values)."""
    item = QTableWidgetItem(str(value))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    item.setToolTip(str(value))
    return item


# ── Main widget ───────────────────────────────────────────────────────────────

class HaplotypeTabWidget(QWidget):
    """Haplotype results tab: summary + nucleotide viewer + sequence mapping."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # hap_name → full upper-cased aligned sequence (from _hap.fasta)
        self._hap_sequences: Dict[str, str] = {}
        # 0-based column indices actually shown in the seq viewer
        self._display_positions: List[int] = []
        self._setup_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self._summary_label = QLabel("No results loaded.")
        self._summary_label.setFont(QFont("Arial", 10))
        self._summary_label.setStyleSheet("color:#555;padding:4px;")
        layout.addWidget(self._summary_label)

        outer = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(outer)

        # ── top pane: haplotype summary ──────────────────────────────────────
        top = QWidget()
        tl = QVBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(2)
        tl.addWidget(_section_header("Haplotype Summary"))

        self._info_label = QLabel("")
        self._info_label.setFont(QFont("Arial", 9))
        self._info_label.setStyleSheet("color:#888;padding:2px 4px;")
        self._info_label.setWordWrap(True)
        self._info_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._info_label.setVisible(False)
        tl.addWidget(self._info_label)

        inner = QSplitter(Qt.Orientation.Horizontal)
        # stretch=1 ensures inner fills all remaining height in the top pane,
        # preventing a blank gap above the table when the pane is taller than
        # the inner splitter's preferred size.
        tl.addWidget(inner, 1)

        # Left: stat table (Haplotype | Total Count | Samples)
        self._hap_table = _make_table(["Haplotype", "Total Count", "Samples"])
        inner.addWidget(self._hap_table)

        # Right: nucleotide sequence viewer
        self._seq_viewer = self._make_seq_viewer()
        inner.addWidget(self._seq_viewer)

        inner.setSizes([280, 700])

        # Synchronise vertical scrolling between the two top-pane tables
        self._hap_table.verticalScrollBar().valueChanged.connect(
            self._seq_viewer.verticalScrollBar().setValue
        )
        self._seq_viewer.verticalScrollBar().valueChanged.connect(
            self._hap_table.verticalScrollBar().setValue
        )

        outer.addWidget(top)

        # ── bottom pane: sequence → haplotype mapping ────────────────────────
        bottom = QWidget()
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(2)
        bl.addWidget(_section_header("Sequence → Haplotype Mapping"))
        self._seq_table = _make_table(["Sequence Name", "Haplotype"])
        bl.addWidget(self._seq_table, 1)  # stretch=1 mirrors the top pane fix
        outer.addWidget(bottom)

        # Give roughly equal initial space to both panes
        outer.setSizes([300, 300])

    @staticmethod
    def _make_seq_viewer() -> QTableWidget:
        """Compact, fixed-column-width table for nucleotide display."""
        t = QTableWidget()
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setShowGrid(True)
        t.setSortingEnabled(False)
        t.verticalHeader().setDefaultSectionSize(24)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setDefaultSectionSize(20)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        t.setFont(QFont("Courier New", 9))  # monospace for aligned bases
        return t

    # ── Public API ───────────────────────────────────────────────────────────

    @staticmethod
    def parse_result_data(output_path: str, prefix: str) -> Dict[str, Any]:
        """Parse all result files (CSV + FASTA) into plain Python data.

        Threadsafe: touches no Qt objects, so it is safe to call from a
        QThread. The returned dict is consumed by apply_data() on the main
        thread. Only the first _MAX_DISPLAY_POSITIONS columns are kept for
        display; the parser does not scan the full alignment for variable
        sites, which keeps parsing O(N_haps * 500) regardless of length.
        """
        hap_path = os.path.join(output_path, f"{prefix}_hap_trait.csv")
        seq_path = os.path.join(output_path, f"{prefix}_seq.meta.csv")
        fasta_path = os.path.join(output_path, f"{prefix}_hap.fasta")

        hap_rows: List[Tuple[str, str, str]] = []
        if os.path.isfile(hap_path):
            try:
                with open(hap_path, encoding="utf-8") as fh:
                    for row in csv.DictReader(fh):
                        hap_rows.append((
                            row.get("haplotype", ""),
                            row.get("total_quantity", ""),
                            row.get("samples", ""),
                        ))
            except Exception:
                hap_rows = []

        seq_rows: List[Tuple[str, str]] = []
        if os.path.isfile(seq_path):
            try:
                with open(seq_path, encoding="utf-8") as fh:
                    for row in csv.DictReader(fh):
                        seq_rows.append((
                            row.get("sequence_name", ""),
                            row.get("haplotype", ""),
                        ))
            except Exception:
                seq_rows = []

        hap_sequences: Dict[str, str] = {}
        if os.path.isfile(fasta_path):
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
                                hap_sequences[current] = ''.join(buf).upper()
                            current = line[1:].strip()
                            buf = []
                        else:
                            buf.append(line)
                    if current is not None and buf:
                        hap_sequences[current] = ''.join(buf).upper()
            except Exception:
                hap_sequences = {}

        display_positions: List[int] = []
        seq_len = 0
        truncated = False
        if hap_sequences:
            seq_len = max(len(s) for s in hap_sequences.values())
            display_len = min(seq_len, _MAX_DISPLAY_POSITIONS)
            display_positions = list(range(display_len))
            truncated = seq_len > _MAX_DISPLAY_POSITIONS

        summary = (
            f"Project: {prefix}    |    "
            f"Unique haplotypes: {len(hap_rows)}    |    "
            f"Total sequences: {len(seq_rows)}"
        )
        if seq_len:
            if truncated:
                summary += (
                    f"    |    {seq_len} positions "
                    f"(showing first {len(display_positions)})"
                )
            else:
                summary += f"    |    {seq_len} positions"

        info = ""
        if truncated:
            info = (
                f"Only the first {len(display_positions)} positions are shown here to keep "
                f"the view responsive. For the full aligned haplotypes open "
                f"{fasta_path}."
            )

        return {
            "prefix": prefix,
            "output_path": output_path,
            "hap_rows": hap_rows,
            "seq_rows": seq_rows,
            "hap_sequences": hap_sequences,
            "display_positions": display_positions,
            "seq_len": seq_len,
            "truncated": truncated,
            "summary": summary,
            "info": info,
        }

    def apply_data(self, data: Dict[str, Any]) -> None:
        """Populate all three panes from a parse_result_data() result."""
        self._hap_sequences = dict(data.get("hap_sequences", {}))
        self._display_positions = list(data.get("display_positions", []))

        self._fill_hap_table(data.get("hap_rows", []))
        self._fill_seq_table(data.get("seq_rows", []))
        self._render_seq_viewer()

        self._summary_label.setText(data.get("summary", ""))
        info = data.get("info", "")
        self._info_label.setText(info)
        self._info_label.setVisible(bool(info))

    def load_result(self, output_path: str, prefix: str) -> None:
        """Reload all three panes from the latest analysis output files (sync).

        Kept for callers that want to parse + render in the current thread.
        Background/async callers should use parse_result_data() followed by
        apply_data() on the main thread.
        """
        self.apply_data(self.parse_result_data(output_path, prefix))

    def clear(self) -> None:
        """Reset all panes (e.g. when opening a new project)."""
        self._hap_table.setRowCount(0)
        self._seq_viewer.setRowCount(0)
        self._seq_viewer.setColumnCount(0)
        self._seq_table.setRowCount(0)
        self._hap_sequences.clear()
        self._display_positions.clear()
        self._summary_label.setText("No results loaded.")
        self._info_label.clear()
        self._info_label.setVisible(False)

    # ── Private: fill tables ─────────────────────────────────────────────────

    def _fill_hap_table(self, rows: List[Tuple[str, str, str]]) -> None:
        """Fill the haplotype summary table from pre-parsed rows."""
        self._hap_table.setRowCount(len(rows))
        for r, (hap, count, samples) in enumerate(rows):
            self._hap_table.setItem(r, 0, _plain_item(hap))
            cnt = _plain_item(count)
            cnt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._hap_table.setItem(r, 1, cnt)
            self._hap_table.setItem(r, 2, _plain_item(samples))

        self._hap_table.resizeColumnToContents(0)
        self._hap_table.resizeColumnToContents(1)

    def _fill_seq_table(self, rows: List[Tuple[str, str]]) -> None:
        """Fill the sequence mapping table from pre-parsed rows."""
        self._seq_table.setRowCount(len(rows))
        for r, (name, hap) in enumerate(rows):
            self._seq_table.setItem(r, 0, _plain_item(name))
            self._seq_table.setItem(r, 1, _plain_item(hap))

        self._seq_table.resizeColumnToContents(0)
        self._seq_table.resizeColumnToContents(1)

    def _render_seq_viewer(self) -> None:
        """Render the (capped) nucleotide grid for all haplotypes."""
        self._seq_viewer.setRowCount(0)
        self._seq_viewer.setColumnCount(0)

        if not self._hap_sequences or not self._display_positions:
            return

        hap_order = list(self._hap_sequences.keys())
        n_cols = len(self._display_positions)

        self._seq_viewer.setUpdatesEnabled(False)
        self._seq_viewer.setRowCount(len(hap_order))
        self._seq_viewer.setColumnCount(n_cols)
        self._seq_viewer.setHorizontalHeaderLabels(
            [str(p + 1) for p in self._display_positions]
        )

        for r, hap_name in enumerate(hap_order):
            seq = self._hap_sequences.get(hap_name, "")
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

    # ── Utility ───────────────────────────────────────────────────────────────

    def _current_hap_order(self) -> List[str]:
        """Return haplotype names in the current visual row order of _hap_table."""
        order = [
            self._hap_table.item(r, 0).text()
            for r in range(self._hap_table.rowCount())
            if self._hap_table.item(r, 0)
        ]
        return order if order else list(self._hap_sequences.keys())


# ── Module-level UI helpers ──────────────────────────────────────────────────

def _section_header(text: str) -> QLabel:
    label = QLabel(text)
    label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    label.setStyleSheet(
        "background:#E3F2FD;color:#1565C0;padding:4px 8px;border-radius:2px;"
    )
    return label


def _make_table(headers: List[str]) -> QTableWidget:
    """Standard read-only table with tooltips and no column-header sorting."""
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setShowGrid(True)
    table.setSortingEnabled(False)  # column-header click must not sort
    h = table.horizontalHeader()
    h.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    h.setStretchLastSection(True)
    h.setSectionsClickable(False)  # visually disable the clickable header
    table.verticalHeader().setDefaultSectionSize(24)
    table.verticalHeader().setVisible(False)
    return table
