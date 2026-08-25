"""Bilingual academic landing-page content for the NetST Home tab."""

from html import escape

REPOSITORY = "https://github.com/plant720/NetST"

# Restrained colors from the NPG/SCI plotting palette.  The darker blue is the
# interface anchor; the remaining colors are used only as navigational accents.
SCI_COLORS = ("#3C5488", "#00A087", "#E64B35", "#4DBBD5")


CONTENT = {
    "cn": {
        "kicker": "开源科研软件",
        "title": "NetST",
        "subtitle": "单倍型网络分析与可视化",
        "tagline": "面向群体遗传学、分子生态学与系统地理学",
        "summary": "在一个清晰、可复现的桌面工作流中完成序列比对、单倍型识别、网络构建与性状可视化。",
        "start_label": "开始分析",
        "start_text": "文件  →  导入 FASTA / NEXUS / PHYLIP / VCF",
        "workflow_title": "分析流程",
        "workflow_note": "从原始序列到可解释的单倍型网络",
        "workflow": [
            ("01", "导入", "序列与元数据"),
            ("02", "检查", "样本、性状与质量"),
            ("03", "分析", "比对、单倍型与网络"),
            ("04", "解读", "多样性、距离与拓扑"),
        ],
        "cap_title": "核心能力",
        "cap_note": "围绕常用群体遗传分析任务设计",
        "capabilities": [
            ("多格式数据", "导入 FASTA、NEXUS、PHYLIP、VCF，并从样本 ID 或 CSV/TSV 解析元数据。"),
            ("序列与单倍型", "集成 MAFFT / MUSCLE 比对，识别唯一单倍型并保留样本归属。"),
            ("网络构建", "支持 TCS、MSN、MJN、RMST 与 McAN 等互补网络算法。"),
            ("交互式解读", "联动查看性状、多样性指数、距离 / PCoA 与网络拓扑指标。"),
        ],
        "ref_title": "方法与格式",
        "reference": [
            ("算法", "Original TCS · Modified TCS · MSN · MJN · RMST · McAN"),
            ("输入", "FASTA · NEXUS · PHYLIP · VCF · CSV / TSV metadata"),
            ("输出", "FASTA · NEXUS · PHYLIP · VCF · GML · 交互式 HTML"),
        ],
        "repo_text": "GitHub 仓库",
        "docs_text": "使用文档",
        "docs_path": "docs/NetST-使用手册.md",
        "footer": "Plant720 Lab · 双语桌面应用",
    },
    "en": {
        "kicker": "OPEN-SOURCE SCIENTIFIC SOFTWARE",
        "title": "NetST",
        "subtitle": "Haplotype Network Analysis & Visualization",
        "tagline": "For population genetics, molecular ecology, and phylogeography",
        "summary": (
            "Align sequences, identify haplotypes, reconstruct networks, and visualize traits "
            "in one clear, reproducible desktop workflow."
        ),
        "start_label": "START AN ANALYSIS",
        "start_text": "File  →  Import FASTA / NEXUS / PHYLIP / VCF",
        "workflow_title": "WORKFLOW",
        "workflow_note": "From raw sequences to interpretable haplotype networks",
        "workflow": [
            ("01", "Import", "Sequences & metadata"),
            ("02", "Review", "Samples, traits & quality"),
            ("03", "Analyze", "Alignment, haplotypes & network"),
            ("04", "Explore", "Diversity, distance & topology"),
        ],
        "cap_title": "CORE CAPABILITIES",
        "cap_note": "Built around common population-genetic analysis tasks",
        "capabilities": [
            ("Multi-format data", "Import FASTA, NEXUS, PHYLIP, or VCF and parse metadata from sample IDs or CSV/TSV."),
            ("Sequences & haplotypes", "Run MAFFT / MUSCLE alignments and identify unique haplotypes with sample assignments."),
            ("Network construction", "Choose complementary TCS, MSN, MJN, RMST, and McAN network algorithms."),
            ("Interactive interpretation", "Explore traits, diversity indices, distance / PCoA, and network topology metrics."),
        ],
        "ref_title": "METHODS & FORMATS",
        "reference": [
            ("Algorithms", "Original TCS · Modified TCS · MSN · MJN · RMST · McAN"),
            ("Inputs", "FASTA · NEXUS · PHYLIP · VCF · CSV / TSV metadata"),
            ("Outputs", "FASTA · NEXUS · PHYLIP · VCF · GML · interactive HTML"),
        ],
        "repo_text": "GitHub repository",
        "docs_text": "User guide",
        "docs_path": "docs/NetST-User-Manual.md",
        "footer": "Plant720 Lab · Bilingual desktop application",
    },
}


def _section_heading(title: str, note: str = "") -> str:
    """Return a compact section heading with an optional right-aligned note."""
    note_cell = f'<td class="section-note" align="right">{escape(note)}</td>' if note else ""
    return (
        '<table class="section-heading" width="100%" cellspacing="0" cellpadding="0"><tr>'
        f'<td class="section-title">{escape(title)}</td>{note_cell}</tr></table>'
    )


def _workflow(c: dict) -> str:
    cells = []
    for index, (number, title, description) in enumerate(c["workflow"]):
        color = SCI_COLORS[index]
        if index:
            cells.append('<td class="column-gap" width="14">&#160;</td>')
        cells.append(
            '<td class="workflow-card" width="25%" valign="top">'
            '<table width="100%" cellspacing="0" cellpadding="0">'
            f'<tr><td class="workflow-accent" height="5" bgcolor="{color}"></td></tr>'
            '<tr><td class="workflow-body" height="66" valign="top">'
            f'<span class="step-number" style="color:{color};">{escape(number)}</span>'
            f'<div class="step-title">{escape(title)}</div>'
            f'<div class="step-description">{escape(description)}</div>'
            '</td></tr></table></td>'
        )
    return (
        '<table class="workflow" width="100%" cellspacing="0" cellpadding="0"><tr>'
        + "".join(cells)
        + "</tr></table>"
    )


def _capabilities(c: dict) -> str:
    rows = []
    capabilities = c["capabilities"]
    for row_start in range(0, len(capabilities), 2):
        row_cells = []
        for index, (title, description) in enumerate(capabilities[row_start:row_start + 2], row_start):
            color = SCI_COLORS[index]
            if index > row_start:
                row_cells.append('<td class="column-gap" width="14">&#160;</td>')
            row_cells.append(
                '<td class="capability-card" width="50%" valign="top">'
                '<table width="100%" cellspacing="0" cellpadding="0">'
                f'<tr><td class="capability-accent" height="4" bgcolor="{color}"></td></tr>'
                '<tr><td class="capability-body" height="58" valign="top">'
                f'<div class="capability-title">{escape(title)}</div>'
                f'<div class="capability-description">{escape(description)}</div>'
                '</td></tr></table></td>'
            )
        if rows:
            rows.append('<tr><td class="row-gap" colspan="3" height="12">&#160;</td></tr>')
        rows.append(f'<tr>{"".join(row_cells)}</tr>')
    return (
        '<table class="capabilities" width="100%" cellspacing="0" cellpadding="0">'
        + "".join(rows)
        + "</table>"
    )


def _reference(c: dict) -> str:
    rows = "".join(
        f'<tr><td class="reference-label" width="20%" height="31">{escape(label)}</td>'
        f'<td class="reference-value" width="80%" height="31">{escape(value)}</td></tr>'
        for label, value in c["reference"]
    )
    return f'<table class="reference" width="100%" cellspacing="0" cellpadding="0">{rows}</table>'


def _vertical_spacer(height: int) -> str:
    """Use a table spacer because QTextDocument ignores some CSS margins."""
    return (
        '<table width="100%" cellspacing="0" cellpadding="0">'
        f'<tr><td class="vertical-spacer" height="{height}">&#160;</td></tr></table>'
    )


def render_home(language: str = "en") -> str:
    """Render a clean academic Home page using QTextBrowser-compatible HTML."""
    c = CONTENT.get(language, CONTENT["en"])
    docs_url = f"{REPOSITORY}/blob/main/{c['docs_path']}"

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body {{ margin:0; background-color:#F6F8FB; color:#536276;
       font-family:"Segoe UI","Helvetica Neue",Arial,"Microsoft YaHei",sans-serif; }}
.outer-space {{ font-size:1px; color:#F6F8FB; }}
.content {{ vertical-align:top; }}
.hero {{ background-color:#FFFFFF; border:1px solid #D9E1EA; }}
.hero-accent {{ width:6px; background-color:#3C5488; }}
.hero-copy {{ padding:27px 30px 25px; vertical-align:top; }}
.kicker {{ color:#3C5488; font-size:11px; font-weight:bold; letter-spacing:0.8px;
           margin-bottom:10px; }}
.app-name {{ color:#17243A; font-size:33px; font-weight:bold; }}
.subtitle {{ color:#2F4057; font-size:17px; font-weight:bold; margin-top:4px; }}
.tagline {{ color:#008C78; font-size:12px; margin-top:10px; }}
.summary {{ color:#536276; font-size:12px; line-height:1.6; margin-top:10px; }}
.hero-start {{ padding:27px 28px; vertical-align:middle;
               background-color:#F0F5F8; border-left:1px solid #D9E1EA; }}
.start-label {{ color:#3C5488; font-size:11px; font-weight:bold; letter-spacing:0.6px;
                margin-bottom:10px; }}
.start-text {{ color:#2F4057; font-size:12px; font-weight:bold; line-height:1.6; }}
.section-heading {{ margin:0; }}
.section-title {{ color:#26384F; font-size:12px; font-weight:bold; letter-spacing:0.65px; }}
.section-note {{ color:#77859A; font-size:10px; }}
.column-gap, .row-gap, .vertical-spacer {{ font-size:1px; color:#F6F8FB; }}
.workflow-card {{ vertical-align:top; background-color:#FFFFFF;
                  border:1px solid #D9E1EA; }}
.workflow-body {{ padding:13px 14px 14px; }}
.step-number {{ font-size:10px; font-weight:bold; }}
.step-title {{ color:#26384F; font-size:13px; font-weight:bold; margin-top:4px; }}
.step-description {{ color:#657388; font-size:11px; line-height:1.4; margin-top:4px; }}
.capability-card {{ vertical-align:top; background-color:#FFFFFF;
                    border:1px solid #D9E1EA; }}
.capability-body {{ padding:13px 16px 14px; }}
.capability-title {{ color:#26384F; font-size:13px; font-weight:bold; margin-bottom:5px; }}
.capability-description {{ color:#657388; font-size:11px; line-height:1.45; }}
.reference {{ background-color:#FFFFFF; border:1px solid #D9E1EA; }}
.reference-label {{ padding:8px 15px; color:#3C5488; font-size:11px;
                    font-weight:bold; border-bottom:1px solid #E8EDF2; }}
.reference-value {{ padding:8px 15px; color:#5D6C80; font-size:11px;
                    border-bottom:1px solid #E8EDF2; }}
.footer {{ padding-top:13px; border-top:1px solid #D9E1EA; }}
.footer-copy {{ color:#77859A; font-size:10px; }}
.footer-link {{ color:#3C5488; font-size:10px; font-weight:bold; text-decoration:none; }}
</style></head><body>

<table width="100%" cellspacing="0" cellpadding="0">
<tr><td class="outer-space" colspan="3" height="28">&#160;</td></tr>
<tr>
<td class="outer-space" width="36">&#160;</td>
<td class="content" valign="top">

<table class="hero" width="100%" cellspacing="0" cellpadding="0"><tr>
  <td class="hero-accent" width="6"></td>
  <td class="hero-copy" width="66%">
    <div class="kicker">{escape(c['kicker'])}</div>
    <div class="app-name">{escape(c['title'])}</div>
    <div class="subtitle">{escape(c['subtitle'])}</div>
    <div class="tagline">{escape(c['tagline'])}</div>
    <div class="summary">{escape(c['summary'])}</div>
  </td>
  <td class="hero-start" width="34%">
    <div class="start-label">{escape(c['start_label'])}</div>
    <div class="start-text">{escape(c['start_text'])}</div>
  </td>
</tr></table>

{_vertical_spacer(27)}
{_section_heading(c['workflow_title'], c['workflow_note'])}
{_vertical_spacer(11)}
{_workflow(c)}

{_vertical_spacer(27)}
{_section_heading(c['cap_title'], c['cap_note'])}
{_vertical_spacer(11)}
{_capabilities(c)}

{_vertical_spacer(27)}
{_section_heading(c['ref_title'])}
{_vertical_spacer(11)}
{_reference(c)}

{_vertical_spacer(19)}
<table class="footer" width="100%" cellspacing="0" cellpadding="0"><tr>
  <td class="footer-copy">{escape(c['footer'])}</td>
  <td align="right">
    <a class="footer-link" href="{docs_url}">{escape(c['docs_text'])}</a>
    <span class="footer-copy"> &nbsp;·&nbsp; </span>
    <a class="footer-link" href="{REPOSITORY}">{escape(c['repo_text'])}</a>
  </td>
</tr></table>

</td>
<td class="outer-space" width="36">&#160;</td>
</tr>
<tr><td class="outer-space" colspan="3" height="26">&#160;</td></tr>
</table>
</body></html>"""
