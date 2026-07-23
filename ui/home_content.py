"""Concise bilingual content and HTML renderer for the NetST Home tab."""

from html import escape


VERSION = "2.0.0"
REPOSITORY = "https://github.com/plant720/netst-py"


CONTENT = {
    "cn": {
        "eyebrow": "群体遗传学 · 分子生态学 · 系统地理学",
        "title": "NetST",
        "subtitle": "单倍型网络分析与可视化工具",
        "summary": "从 DNA/RNA 序列出发，在一个桌面工作流中完成比对、单倍型识别、网络构建和性状可视化。",
        "capabilities_title": "主要功能",
        "capabilities": [
            ("数据与性状", "导入 FASTA、NEXUS、PHYLIP 或 VCF+metadata，并匹配性状。"),
            ("比对与单倍型", "使用 MAFFT 或 MUSCLE 进行比对，识别唯一单倍型及样本归属。"),
            ("网络构建", "支持 TCS、MSN、MJN、RMST 与 McAN Minimum-cost Arborescence Network。"),
            ("查看与辅助解读", "查看交互网络、多样性、距离/PCoA 与拓扑指标。"),
        ],
        "workflow_title": "快速开始",
        "workflow": [
            ("1", "导入数据", "载入 FASTA、NEXUS、PHYLIP，或 VCF 与 metadata。"),
            ("2", "检查样本", "在“数据”页确认名称、序列、性状和选择状态。"),
            ("3", "运行分析", "设置项目名称与输出目录，然后选择比对、单倍型或网络分析。"),
            ("4", "查看结果", "检查网络、比对和单倍型，或在“辅助解读”中查看统计结果。"),
        ],
        "support_title": "支持范围",
        "support": [
            ("算法", "Original TCS · Modified TCS · MSN · MJN · RMST · McAN Minimum-cost Arborescence Network"),
            ("输入", "FASTA · NEXUS · PHYLIP · VCF · CSV/TSV metadata"),
            ("输出", "FASTA · NEXUS · PHYLIP · VCF · GML · 交互式 HTML"),
        ],
        "version_label": "版本",
        "team_label": "开发",
        "help_label": "帮助",
        "help_value": "帮助菜单内置 NetST 与 tcsBU 文档",
        "repo_label": "项目仓库",
        "notice": "提示：正式分析前，请检查序列质量、比对结果、缺失数据和算法参数。",
    },
    "en": {
        "eyebrow": "POPULATION GENETICS · MOLECULAR ECOLOGY · PHYLOGEOGRAPHY",
        "title": "NetST",
        "subtitle": "Haplotype Network Analysis and Visualization",
        "summary": "Align DNA/RNA sequences, identify haplotypes, reconstruct networks, and visualize traits in one desktop workflow.",
        "capabilities_title": "Main capabilities",
        "capabilities": [
            ("Data and traits", "Import FASTA, NEXUS, PHYLIP, or VCF with metadata and map traits."),
            ("Alignment and haplotypes", "Run MAFFT or MUSCLE and identify unique haplotypes with sample assignments."),
            ("Network construction", "Build networks with TCS, MSN, MJN, RMST, or McAN Minimum-cost Arborescence Network."),
            ("Review and interpret", "Explore networks, diversity, distance/PCoA, and topology metrics."),
        ],
        "workflow_title": "Quick start",
        "workflow": [
            ("1", "Import data", "Load FASTA, NEXUS, PHYLIP, or VCF with metadata."),
            ("2", "Review samples", "Check names, sequences, traits, and selection in Data."),
            ("3", "Run analysis", "Set the project and output folder, then choose alignment, haplotype, or network analysis."),
            ("4", "Inspect results", "Review network, alignment, and haplotypes, or open Interpretation statistics."),
        ],
        "support_title": "Supported data and methods",
        "support": [
            ("Methods", "Original TCS · Modified TCS · MSN · MJN · RMST · McAN Minimum-cost Arborescence Network"),
            ("Inputs", "FASTA · NEXUS · PHYLIP · VCF · CSV/TSV metadata"),
            ("Outputs", "FASTA · NEXUS · PHYLIP · VCF · GML · interactive HTML"),
        ],
        "version_label": "Version",
        "team_label": "Development",
        "help_label": "Help",
        "help_value": "NetST and tcsBU manuals are available from Help",
        "repo_label": "Repository",
        "notice": "Before formal analysis, review sequence quality, alignment, missing data, and algorithm parameters.",
    },
}


def render_home(language: str = "en") -> str:
    """Render a compact Home page without requiring Qt."""
    info = CONTENT.get(language, CONTENT["en"])

    capability_rows = []
    for index in range(0, len(info["capabilities"]), 2):
        cells = "".join(
            f'<td class="card"><div class="card-title">{escape(title)}</div>'
            f'<div class="card-text">{escape(description)}</div></td>'
            for title, description in info["capabilities"][index:index + 2]
        )
        capability_rows.append(f"<tr>{cells}</tr>")

    workflow_rows = "".join(
        f'<tr><td class="step-number">{escape(number)}</td>'
        f'<td class="step-title">{escape(title)}</td>'
        f'<td class="step-text">{escape(description)}</td></tr>'
        for number, title, description in info["workflow"]
    )

    support_columns = "".join(
        f'<td class="support-item"><div class="support-label">{escape(label)}</div>'
        f'<div class="support-value">{escape(value)}</div></td>'
        for label, value in info["support"]
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body {{ margin:0; background:#f5f7f9; color:#344454; font-family:Arial, "Microsoft YaHei", sans-serif; }}
.page {{ margin:0 auto; padding:28px 34px 34px; max-width:1080px; }}
.hero-table, .panel, .cards, .workflow, .support, .footer-table {{ width:100%; }}
.hero-table, .panel, .cards, .workflow, .support, .footer-table {{ border-collapse:separate; }}
.hero-accent {{ width:6px; background:#587da3; }}
.hero-content {{ background:#ffffff; padding:24px 28px 22px; border:1px solid #dce3ea; }}
.eyebrow {{ color:#587da3; font-size:10px; font-weight:bold; letter-spacing:1.1px; margin-bottom:7px; }}
.title {{ color:#243b53; font-size:34px; font-weight:bold; margin:0; }}
.subtitle {{ color:#415a73; font-size:18px; margin:3px 0 10px; }}
.summary {{ color:#617384; font-size:13px; line-height:1.6; margin:0; }}
.meta {{ color:#8090a0; font-size:10px; margin-top:13px; }}
.panel {{ margin-top:15px; background:#ffffff; border:1px solid #dce3ea; }}
.panel-cell {{ padding:17px 19px 18px; }}
.section-title {{ color:#2d465f; font-size:17px; font-weight:bold; margin-bottom:10px; }}
.cards {{ border-spacing:7px; }}
.card {{ width:50%; vertical-align:top; background:#f8fafc; border:1px solid #e0e6ec; padding:12px 14px; }}
.card-title {{ color:#344f69; font-size:12px; font-weight:bold; margin-bottom:5px; }}
.card-text {{ color:#657686; font-size:11px; line-height:1.5; }}
.workflow {{ border-collapse:collapse; }}
.workflow td {{ border-bottom:1px solid #e5eaef; padding:8px; }}
.step-number {{ width:25px; text-align:center; color:#486b8d; background:#eaf0f6; font-weight:bold; }}
.step-title {{ width:105px; color:#344f69; font-size:12px; font-weight:bold; }}
.step-text {{ color:#657686; font-size:11px; line-height:1.45; }}
.support {{ border-spacing:7px; }}
.support-item {{ width:33.33%; vertical-align:top; background:#f8fafc; border:1px solid #e0e6ec; padding:11px 13px; }}
.support-label {{ color:#344f69; font-size:11px; font-weight:bold; margin-bottom:5px; }}
.support-value {{ color:#657686; font-size:10px; line-height:1.5; }}
.footer-table {{ margin-top:15px; background:#eef2f5; border:1px solid #dce3e8; }}
.footer-cell {{ padding:11px 14px; color:#667786; font-size:10px; line-height:1.55; }}
.footer-cell strong {{ color:#40576d; }}
.footer-cell a {{ color:#486f98; font-weight:bold; text-decoration:none; }}
.notice {{ margin-top:8px; color:#7a704f; }}
</style></head><body><div class="page">
<table class="hero-table" width="100%" cellspacing="0" cellpadding="0"><tr>
  <td class="hero-accent">&nbsp;</td>
  <td class="hero-content">
    <div class="eyebrow">{escape(info['eyebrow'])}</div>
    <div class="title">{escape(info['title'])}</div>
    <div class="subtitle">{escape(info['subtitle'])}</div>
    <div class="summary">{escape(info['summary'])}</div>
    <div class="meta">Version {VERSION} &nbsp;·&nbsp; Plant720 Lab &nbsp;·&nbsp; 中文 / English</div>
  </td>
</tr></table>
<table class="panel" width="100%" cellspacing="0" cellpadding="0"><tr><td class="panel-cell">
  <div class="section-title">{escape(info['capabilities_title'])}</div>
  <table class="cards" width="100%" cellspacing="7" cellpadding="0">{"".join(capability_rows)}</table>
</td></tr></table>
<table class="panel" width="100%" cellspacing="0" cellpadding="0"><tr><td class="panel-cell">
  <div class="section-title">{escape(info['workflow_title'])}</div>
  <table class="workflow" width="100%" cellspacing="0" cellpadding="0">{workflow_rows}</table>
</td></tr></table>
<table class="panel" width="100%" cellspacing="0" cellpadding="0"><tr><td class="panel-cell">
  <div class="section-title">{escape(info['support_title'])}</div>
  <table class="support" width="100%" cellspacing="7" cellpadding="0"><tr>{support_columns}</tr></table>
</td></tr></table>
<table class="footer-table" width="100%" cellspacing="0" cellpadding="0"><tr><td class="footer-cell">
  <strong>{escape(info['version_label'])}:</strong> {VERSION} &nbsp;·&nbsp;
  <strong>{escape(info['team_label'])}:</strong> Plant720 Lab &nbsp;·&nbsp;
  <strong>{escape(info['help_label'])}:</strong> {escape(info['help_value'])}<br>
  <strong>{escape(info['repo_label'])}:</strong> <a href="{REPOSITORY}">{REPOSITORY}</a>
  <div class="notice">{escape(info['notice'])}</div>
</td></tr></table>
</div></body></html>"""
