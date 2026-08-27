"""Bilingual academic landing-page content for the NetST Home tab."""

from html import escape

REPOSITORY = "https://github.com/plant720/NetST"
WORKFLOW_IMAGE = "netst-workflow.png"

CONTENT = {
    "cn": {
        "title": "NetST",
        "subtitle": (
            "a desktop application for project-based haplotype network analysis "
            "with metadata integration"
        ),
        "lead": (
            "NetST 将序列处理、单倍型识别、网络构建、交互式可视化与描述性分析"
            "整合到一个可保存、可恢复的桌面项目中。"
        ),
        "overview": (
            "六种已发表的构建方法共用同一套样本—单倍型映射，避免重复映射带来的"
            "不一致，使不同规则下的网络可直接比较。分类与连续型元数据可直接导入，"
            "并以同心圆层同时呈现，从而在同一单倍型结构上比较多个注释维度。输入数据、"
            "方法参数、元数据映射、分析输出与可视化配置统一记录于单个可重新导入的 "
            "JSON 项目文件，保留完整且可检视的分析记录。"
        ),
        "detail": (
            "MAFFT / MUSCLE 提供多序列比对；fastHaN 实现 Original TCS、Modified TCS、"
            "MSN、MJN 算法，McAN 实现最小代价树状网络，RMST 按已发表算法独立实现；"
            "使用 tcsBU 进行可视化。"
        ),
        "workflow_alt": (
            "NetST 项目式工作流：输入数据、可选比对、单倍型识别、六种网络构建方法、"
            "元数据可视化、描述性分析以及导出与项目状态"
        ),
        "citation_heading": "引用 NetST",
        "citation": (
            "Zhang Z, Song Y, Yu X, Hou J, Yu Y. NetST: a desktop application "
            "for project-based haplotype network analysis with metadata integration. "
            "[Manuscript]."
        ),
        "docs_text": "使用文档",
        "docs_path": "docs/NetST-使用手册.md",
        "repo_text": "GitHub 仓库",
    },
    "en": {
        "title": "NetST",
        "subtitle": (
            "a desktop application for project-based haplotype network analysis "
            "with metadata integration"
        ),
        "lead": (
            "NetST integrates sequence processing, haplotype identification, network "
            "construction, interactive visualization, and descriptive analysis within "
            "a desktop project that can be saved and restored."
        ),
        "overview": (
            "The six published network construction methods use a shared "
            "sample-to-haplotype mapping. This avoids inconsistencies caused by repeated "
            "mapping and enables direct comparison of networks generated under different "
            "rules. Categorical and continuous metadata can be imported directly and "
            "displayed simultaneously as concentric layers, allowing multiple annotation "
            "dimensions to be compared on the same haplotype structure. Input data, method "
            "parameters, metadata mappings, analytical outputs, and visualization settings "
            "are recorded in a single re-importable JSON project file. Together, these "
            "records preserve a complete and reviewable analysis record."
        ),
        "detail": (
            "MAFFT / MUSCLE provides multiple sequence alignment, while fastHaN implements "
            "the Original TCS, Modified TCS, MSN, and MJN algorithms. McAN implements a "
            "minimum-cost arborescence network, RMST is independently implemented according "
            "to the published algorithm, and tcsBU provides network visualization."
        ),
        "workflow_alt": (
            "NetST project-based workflow: input data, optional alignment, haplotype "
            "identification, six network construction methods, metadata visualization, "
            "descriptive analysis, export, and project state"
        ),
        "citation_heading": "Cite NetST",
        "citation": (
            "Zhang Z, Song Y, Yu X, Hou J, Yu Y. NetST: a desktop application "
            "for project-based haplotype network analysis with metadata integration. "
            "[Manuscript]."
        ),
        "docs_text": "User guide",
        "docs_path": "docs/NetST-User-Manual.md",
        "repo_text": "GitHub repository",
    },
}


def _layout_metrics(viewport_width: int | None) -> dict[str, int]:
    """Return conservative pixel metrics supported by QTextDocument."""
    width = max(320, min(int(viewport_width or 1000), 1800))
    if width <= 620:
        section, frame = 14, 4
        header_v, title, subtitle = 22, 40, 13
    elif width <= 980:
        section, frame = 24, 6
        header_v, title, subtitle = 26, 46, 15
    else:
        section, frame = 34, 8
        header_v, title, subtitle = 30, 52, 16

    image_width = max(240, width - (section * 2) - (frame * 2) - 10)
    return {
        "section": section,
        "frame": frame,
        "header_v": header_v,
        "title": title,
        "subtitle": subtitle,
        "image_width": image_width,
    }


def render_home(language: str = "en", viewport_width: int | None = None) -> str:
    """Render the localized Home page using QTextBrowser-compatible HTML."""
    selected = "cn" if language == "cn" else "en"
    c = CONTENT[selected]
    html_language = "zh-CN" if selected == "cn" else "en"
    docs_url = f"{REPOSITORY}/blob/main/{c['docs_path']}"
    metrics = _layout_metrics(viewport_width)

    return f"""<!DOCTYPE html>
<html lang="{html_language}"><head><meta charset="UTF-8"><style>
body {{ margin:0; background-color:#FFFFFF; color:#17242F;
       font-family:"Segoe UI","Helvetica Neue",Arial,"Microsoft YaHei",sans-serif; }}
.page {{ background-color:#FFFFFF; }}
.header {{ padding:{metrics['header_v']}px {metrics['section'] + 12}px;
           border-bottom:1px solid #DBE4E9; }}
.app-name {{ color:#101C25; font-family:Georgia,"Times New Roman",serif;
             font-size:{metrics['title']}px; font-style:italic; font-weight:bold;
             letter-spacing:-2px; }}
.subtitle {{ color:#496B7E; font-family:Georgia,"Times New Roman",serif;
             font-size:{metrics['subtitle']}px; font-weight:bold; line-height:1.45;
             margin-top:9px; }}
.intro-wrap {{ padding:0 {metrics['section']}px 24px; }}
.intro {{ background-color:#FFFFFF; border:1px solid #DCE6EA; }}
.intro-body {{ padding:18px 22px 19px; color:#33454F; font-size:15px; line-height:1.68; }}
.lead {{ color:#23343E; font-size:17px; line-height:1.62; margin-bottom:10px; }}
.overview {{ color:#33454F; font-size:15px; line-height:1.72; }}
.detail {{ color:#40515D; font-size:14px; line-height:1.65; margin-top:12px;
           padding-top:11px; border-top:1px solid #D7E2E7; }}
.workflow-wrap {{ padding:0 {metrics['section']}px 24px; }}
.workflow-frame {{ padding:{metrics['frame']}px; background-color:#FFFFFF;
                   border:1px solid #C8D5DC; text-align:center; }}
.citation-wrap {{ padding:0 {metrics['section']}px 0; }}
.citation {{ background-color:#FFFFFF; border:1px solid #DFE2CF; }}
.citation-body {{ padding:17px 20px 18px; }}
.citation-title {{ color:#1A2B34; font-size:14px; font-weight:bold;
                   letter-spacing:0.5px; margin-bottom:7px; }}
.citation-copy {{ color:#344650; font-family:Georgia,"Times New Roman",serif;
                  font-size:12px; line-height:1.6; }}
.footer {{ padding:15px {metrics['section']}px 22px; }}
.footer-link {{ color:#326F94; font-size:10px; font-weight:bold; text-decoration:none; }}
.footer-separator {{ color:#9AABB4; font-size:10px; }}
</style></head><body>

<table width="100%" cellspacing="0" cellpadding="0">
<tr>
<td class="page" valign="top">

<div class="header">
  <div class="app-name">{escape(c['title'])}</div>
  <div class="subtitle">{escape(c['subtitle'])}</div>
</div>

<div class="intro-wrap">
  <table class="intro" width="100%" cellspacing="0" cellpadding="0"><tr>
    <td class="intro-body">
      <div class="lead">{escape(c['lead'])}</div>
      <div class="overview">{escape(c['overview'])}</div>
      <div class="detail">{escape(c['detail'])}</div>
    </td>
  </tr></table>
</div>

<div class="workflow-wrap">
  <div class="workflow-frame">
    <img src="{WORKFLOW_IMAGE}" width="{metrics['image_width']}"
         alt="{escape(c['workflow_alt'])}">
  </div>
</div>

<div class="citation-wrap">
  <table class="citation" width="100%" cellspacing="0" cellpadding="0"><tr>
    <td class="citation-body">
      <div class="citation-title">{escape(c['citation_heading'])}</div>
      <div class="citation-copy">{escape(c['citation'])}</div>
    </td>
  </tr></table>
</div>

<table class="footer" width="100%" cellspacing="0" cellpadding="0"><tr>
  <td align="right">
    <a class="footer-link" href="{docs_url}">{escape(c['docs_text'])}</a>
    <span class="footer-separator"> &nbsp;·&nbsp; </span>
    <a class="footer-link" href="{REPOSITORY}">{escape(c['repo_text'])}</a>
  </td>
</tr></table>

</td>
</tr>
</table>
</body></html>"""
