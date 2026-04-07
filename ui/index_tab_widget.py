"""
Index Tab Widget — Application welcome / introduction page.

All display content is centralized in _INFO so it can be updated in one place.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser

# ── Centralised content ─────────────────────────────────────────────────────
# Edit this dict to update any text shown on the Index tab.

_INFO = {
    "name": "NetST — Haplotype Network Analysis Tool",
    "version": "2.0.0",
    "author": "Plant720 Lab",  # ← replace with real author / team
    "contact": "—",  # ← replace with real e-mail / URL
    "repo": "https://github.com/plant720/netst-py",
    "description": (
        "NetST is a comprehensive software platform for constructing and analyzing "
        "haplotype networks from DNA/RNA sequence data. "
        "It supports MSN, MJN, and TCS network algorithms and provides an interactive "
        "D3.js-based visualization interface."
    ),
    "modules": [
        ("Network View", "Interactive visualization of the haplotype network graph."),
        ("Data", "Load, preview, and select input sequences for analysis."),
        ("Haplotype", "Tabular summary of haplotypes and sequence assignments "
                      "(appears after the first successful analysis)."),
    ],
    "workflow": [
        "Load your FASTA sequence file via <b>File → Load Sequence</b>.",
        "Review the imported sequences in the <b>Data</b> tab; "
        "check / uncheck rows to control which sequences enter the analysis.",
        "Set an <b>Output Directory</b> and <b>Project Name</b> in the right panel.",
        "Run a network analysis from the <b>Analysis</b> menu "
        "(MSN / MJN / TCS Haplotype Network).",
        "Explore the interactive network in the <b>Network View</b> tab.",
        "Inspect haplotype assignments in the <b>Haplotype</b> tab.",
    ],
    "tips": [
        "Sequences do <i>not</i> need to be pre-aligned — "
        "MAFFT (or MUSCLE as fallback) will run automatically.",
        "Use the <i>Discrete Traits</i> column to colour network nodes "
        "by population, location, or any other categorical variable.",
        "GML network files produced by external tools can be imported via "
        "<b>File → Load GML</b>.",
        "Use <b>Tools → Date to Number</b> to convert collection dates "
        "(YYYY-MM-DD) into decimal numbers for continuous-trait analysis.",
    ],
}


def _build_html() -> str:
    """Assemble the HTML page from _INFO."""
    module_rows = "\n".join(
        f'<tr>'
        f'<td style="padding:4px 10px;font-weight:bold;white-space:nowrap;'
        f'width:140px;color:#1565C0;">{m[0]}</td>'
        f'<td style="padding:4px 10px;">{m[1]}</td>'
        f'</tr>'
        for m in _INFO["modules"]
    )
    workflow_items = "\n".join(
        f'<li style="margin:5px 0;">{step}</li>'
        for step in _INFO["workflow"]
    )
    tip_items = "\n".join(
        f'<li style="margin:5px 0;">{tip}</li>'
        for tip in _INFO["tips"]
    )

    return f"""
<html>
<body style="font-family:Arial,sans-serif;margin:24px 32px;color:#333;max-width:900px;">

<h1 style="color:#1976D2;margin-bottom:4px;">{_INFO['name']}</h1>
<p style="font-size:12px;color:#888;margin-top:0;">
  Version {_INFO['version']} &nbsp;·&nbsp;
  {_INFO['author']} &nbsp;·&nbsp;
  {_INFO['contact']}
</p>

<hr style="border:none;border-top:1px solid #ddd;margin:12px 0;"/>

<h3 style="color:#1976D2;">About</h3>
<p style="line-height:1.6;">{_INFO['description']}</p>

<h3 style="color:#1976D2;">Main Modules</h3>
<table style="border-collapse:collapse;width:100%;background:#f9f9f9;
              border:1px solid #e0e0e0;border-radius:4px;">
{module_rows}
</table>

<h3 style="color:#1976D2;">Workflow</h3>
<ol style="line-height:1.8;">
{workflow_items}
</ol>

<h3 style="color:#1976D2;">Tips</h3>
<ul style="line-height:1.8;">
{tip_items}
</ul>

<hr style="border:none;border-top:1px solid #ddd;margin:12px 0;"/>
<p style="font-size:11px;color:#aaa;">
  Project repository: <a href="{_INFO['repo']}">{_INFO['repo']}</a>
</p>

</body>
</html>
"""


class IndexTabWidget(QWidget):
    """Welcome / introduction tab displayed when the application starts."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._browser = QTextBrowser()
        self._browser.setReadOnly(True)
        self._browser.setOpenExternalLinks(True)
        self._browser.setHtml(_build_html())
        layout.addWidget(self._browser)
