"""SVG visualisations for the auxiliary interpretation analyses.

The functions here are deliberately pure: they accept the analysis-result
dataclasses (or plain numbers) and return self-contained SVG / HTML strings.
There is no PyQt and no I/O, so every figure can be unit tested without a
display, and the same SVG is reused by both rendering paths in
``InterpretationTabWidget`` (an embedded ``QWebEngineView`` when available, a
stack of ``QSvgWidget`` otherwise).

The desktop app deliberately avoids a separate plotting stack, so charts are
drawn as hand-written SVG rather than pulling in matplotlib or QtCharts.
"""

from __future__ import annotations

import math
from typing import Any, Callable, List, Mapping, Optional, Sequence, Tuple

Tr = Callable[[str, str], str]

# Unquoted comma list: browsers accept it in both SVG attributes and CSS, and
# it avoids QtSvg's parser treating a quoted list as one missing family name.
FONT = "Segoe UI, PingFang SC, Microsoft YaHei, Helvetica, Arial, sans-serif"

INK = "#233038"
MUTED = "#6b7a82"
FAINT = "#f7f9fa"
GRID = "#e7ecef"
AXIS = "#b9c4ca"
BORDER = "#e2e8eb"

# Categorical palette used for groups / metric panels.
SERIES = [
    "#2f6f9f", "#2a9d8f", "#e9a23b", "#d1495b", "#7b6cd9",
    "#57a55a", "#c65f9e", "#4ba3b8", "#8a6d3b", "#9aa441",
]

TONE = {
    "good": "#3a9d5d",
    "warn": "#e0a020",
    "bad": "#d1495b",
    "info": "#2f6f9f",
    "accent": "#2f6f9f",
    "neutral": "#5b6b73",
}


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _esc(text: Any) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _num(value: Any) -> Optional[float]:
    """Return a finite float or ``None`` for missing / NaN / inf values."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _fmt(value: Any, digits: int = 4) -> str:
    number = _num(value)
    if number is None:
        return "—"
    if float(number).is_integer() and abs(number) < 1e15:
        return str(int(number))
    return f"{number:.{digits}g}"


def _pct(value: Any, digits: int = 1) -> str:
    number = _num(value)
    if number is None:
        return "—"
    return f"{number * 100:.{digits}f}%"


def _clip(text: Any, length: int) -> str:
    value = str(text)
    return value if len(value) <= length else value[: max(1, length - 1)] + "…"


def _svg(width: float, height: float, body: str, extra: str = "") -> str:
    # No font-family here on purpose: SVG text inherits the page CSS font in the
    # web view and the Qt application font in the QSvgWidget fallback. Both carry
    # CJK glyphs, and omitting it avoids QtSvg's noisy "missing family" warning
    # (its parser does not split a comma-separated family list).
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" '
        f'preserveAspectRatio="xMidYMid meet" {extra}>'
        f'{body}</svg>'
    )


def _text(x: float, y: float, value: Any, *, size: float = 12,
          fill: str = INK, anchor: str = "start", weight: str = "400",
          extra: str = "") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}" {extra}>'
        f'{_esc(value)}</text>'
    )


def _rect(x: float, y: float, width: float, height: float, fill: str, *,
          rx: float = 0, extra: str = "") -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(0.0, width):.1f}" '
        f'height="{max(0.0, height):.1f}" rx="{rx}" fill="{fill}" {extra}/>'
    )


def _line(x1: float, y1: float, x2: float, y2: float, *,
          stroke: str = GRID, width: float = 1, extra: str = "") -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{width}" {extra}/>'
    )


def _circle(cx: float, cy: float, r: float, fill: str, extra: str = "") -> str:
    return (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
        f'fill="{fill}" {extra}/>'
    )


def _tip(body: str, text: Any) -> str:
    """Wrap ``body`` in a group carrying a native hover tooltip (web view)."""
    return f"<g><title>{_esc(text)}</title>{body}</g>"


def _lerp_color(start: Tuple[int, int, int], end: Tuple[int, int, int],
                t: float) -> str:
    t = min(1.0, max(0.0, t))
    channels = tuple(round(start[i] + (end[i] - start[i]) * t) for i in range(3))
    return "#%02x%02x%02x" % channels


def _empty(message: str, width: float = 640, height: float = 120) -> str:
    body = _text(width / 2, height / 2 + 4, message, size=13, fill=MUTED,
                 anchor="middle")
    return _svg(width, height, body)


def _missing_tone(rate: Any) -> str:
    value = _num(rate) or 0.0
    if value < 0.05:
        return "good"
    if value < 0.20:
        return "warn"
    return "bad"


def _missing_color(rate: Any) -> str:
    return TONE[_missing_tone(rate)]


# --------------------------------------------------------------------------- #
# Generic primitives
# --------------------------------------------------------------------------- #
def cards_svg(cards: Sequence[Mapping[str, Any]], columns: int = 4) -> str:
    """Render KPI stat cards. Each card: ``{label, value, tone?, sub?}``."""
    cards = [card for card in cards if card]
    if not cards:
        return ""
    card_w, card_h, gap = 214.0, 94.0, 14.0
    cols = max(1, min(columns, len(cards)))
    rows = math.ceil(len(cards) / cols)
    width = cols * card_w + (cols + 1) * gap
    height = rows * card_h + (rows + 1) * gap
    parts: List[str] = []
    for index, card in enumerate(cards):
        row, col = divmod(index, cols)
        x = gap + col * (card_w + gap)
        y = gap + row * (card_h + gap)
        tone = TONE.get(str(card.get("tone", "info")), TONE["info"])
        parts.append(_rect(x, y, card_w, card_h, "#fbfcfd", rx=12,
                            extra=f'stroke="{BORDER}" stroke-width="1"'))
        parts.append(_rect(x, y + 10, 5, card_h - 20, tone, rx=2.5))
        parts.append(_text(x + 20, y + 44, _clip(card.get("value", "—"), 12),
                           size=27, weight="600"))
        parts.append(_text(x + 20, y + 68, _clip(card.get("label", ""), 24),
                           size=12.5, fill=MUTED))
        if card.get("sub"):
            parts.append(_text(x + 20, y + 85, _clip(card["sub"], 30),
                               size=11, fill=tone))
    return _svg(width, height, "".join(parts))


def hbar_svg(title: str, items: Sequence[Tuple[Any, Any]], *,
             value_fmt: Callable[[Any], str] = _fmt,
             color: Optional[str] = None,
             color_fn: Optional[Callable[[Any], str]] = None,
             max_value: Optional[float] = None,
             note: Optional[str] = None) -> str:
    """Horizontal bar chart from ``(label, value)`` pairs."""
    items = list(items)
    if not items:
        return _empty("—")
    width = 860.0
    top = 48.0 if title else 16.0
    row_h = 26.0
    label_w = 196.0
    plot_left = label_w + 12
    plot_w = width - plot_left - 96
    height = top + row_h * len(items) + 16
    numbers = [_num(value) or 0.0 for _, value in items]
    peak = max_value if max_value is not None else max(numbers + [0.0])
    if not peak or peak <= 0:
        peak = 1.0
    parts: List[str] = []
    if title:
        parts.append(_text(16, 28, title, size=15, weight="600"))
    if note:
        parts.append(_text(width - 16, 28, note, size=11, fill=MUTED,
                           anchor="end"))
    for index, (label, value) in enumerate(items):
        y = top + index * row_h
        number = _num(value)
        parts.append(_text(label_w, y + row_h * 0.68, _clip(label, 28),
                           size=12, anchor="end"))
        parts.append(_rect(plot_left, y + 4, plot_w, row_h - 10, GRID, rx=4))
        bar_len = 0.0 if number is None else max(0.0, number) / peak * plot_w
        fill = color_fn(value) if color_fn else (color or SERIES[0])
        bar = _rect(plot_left, y + 4, bar_len, row_h - 10, fill, rx=4)
        parts.append(_tip(bar, f"{label}: {value_fmt(value)}"))
        parts.append(_text(plot_left + bar_len + 6, y + row_h * 0.68,
                           value_fmt(value), size=11.5, fill=MUTED))
    return _svg(width, height, "".join(parts))


def group_metric_panels_svg(
    title: str,
    groups: Sequence[str],
    metrics: Sequence[Tuple[str, str, Sequence[Any], Callable[[Any], str]]],
) -> str:
    """Small-multiple horizontal bars: one panel per metric, one row per group.

    ``metrics`` items are ``(name, color, values, value_fmt)`` where ``values``
    is aligned with ``groups``. Each panel is scaled to its own maximum so
    metrics on different scales (Hd, pi, theta) stay comparable within a panel.
    """
    groups = list(groups)
    metrics = list(metrics)
    if not groups or not metrics:
        return _empty("—")
    label_w = 150.0
    panel_w = 208.0
    panel_gap = 26.0
    top = 78.0  # leaves a full row between the chart title and panel headers
    row_h = max(20.0, min(30.0, 320.0 / len(groups)))
    plot_h = row_h * len(groups)
    width = label_w + len(metrics) * (panel_w + panel_gap)
    height = top + plot_h + 24
    parts: List[str] = [_text(16, 26, title, size=15, weight="600")]

    # Shared group labels on the far left.
    for row, group in enumerate(groups):
        y = top + row * row_h
        parts.append(_text(label_w - 12, y + row_h * 0.66, _clip(group, 20),
                           size=12, anchor="end"))
        parts.append(_line(label_w, y + row_h - 1, width - 12,
                           y + row_h - 1, stroke="#f0f3f5"))

    for panel, (name, color, values, fmt) in enumerate(metrics):
        px = label_w + panel * (panel_w + panel_gap)
        numbers = [_num(value) or 0.0 for value in values]
        peak = max(numbers + [0.0]) or 1.0
        parts.append(_text(px, top - 24, name, size=13, weight="600",
                           fill=color))
        parts.append(_line(px, top - 12, px + panel_w - 14, top - 12,
                           stroke=GRID))
        for row, value in enumerate(values):
            y = top + row * row_h
            number = _num(value)
            avail = panel_w - 14
            bar_len = 0.0 if number is None else max(0.0, number) / peak * avail
            parts.append(_rect(px, y + 4, avail, row_h - 10, "#f0f3f5", rx=4))
            bar = _rect(px, y + 4, bar_len, row_h - 10, color, rx=4)
            parts.append(_tip(bar, f"{groups[row]} · {name}: {fmt(value)}"))
            parts.append(_text(px + max(bar_len, 2) + 5, y + row_h * 0.66,
                               fmt(value), size=10.5, fill=MUTED))
    return _svg(width, height, "".join(parts))


def scatter_svg(title: str, points: Sequence[Tuple[float, float, str, str]],
                x_label: str, y_label: str, *,
                label_limit: int = 36) -> str:
    """Ordination scatter. ``points`` are ``(x, y, name, group)`` tuples."""
    clean = [(p[0], p[1], p[2], p[3]) for p in points
             if _num(p[0]) is not None and _num(p[1]) is not None]
    if len(clean) < 2:
        return _empty("—", width=720, height=200)
    width, height = 760.0, 560.0
    m_left, m_right, m_top, m_bottom = 62.0, 22.0, 52.0, 58.0
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom
    xs = [p[0] for p in clean]
    ys = [p[1] for p in clean]
    x_lo, x_hi = min(xs), max(xs)
    y_lo, y_hi = min(ys), max(ys)
    x_pad = (x_hi - x_lo) * 0.08 or 1.0
    y_pad = (y_hi - y_lo) * 0.08 or 1.0
    x_lo, x_hi = x_lo - x_pad, x_hi + x_pad
    y_lo, y_hi = y_lo - y_pad, y_hi + y_pad

    def map_x(value: float) -> float:
        return m_left + (value - x_lo) / (x_hi - x_lo) * plot_w

    def map_y(value: float) -> float:
        return m_top + (y_hi - value) / (y_hi - y_lo) * plot_h

    parts: List[str] = [_text(16, 28, title, size=15, weight="600")]
    parts.append(_rect(m_left, m_top, plot_w, plot_h, "#fcfdfe", rx=6,
                       extra=f'stroke="{GRID}" stroke-width="1"'))

    ticks = 4
    for i in range(ticks + 1):
        vx = x_lo + (x_hi - x_lo) * i / ticks
        gx = map_x(vx)
        parts.append(_line(gx, m_top, gx, m_top + plot_h, stroke="#eef2f4"))
        parts.append(_text(gx, m_top + plot_h + 18, _fmt(vx, 3), size=10,
                           fill=MUTED, anchor="middle"))
        vy = y_lo + (y_hi - y_lo) * i / ticks
        gy = map_y(vy)
        parts.append(_line(m_left, gy, m_left + plot_w, gy, stroke="#eef2f4"))
        parts.append(_text(m_left - 8, gy + 3, _fmt(vy, 3), size=10,
                           fill=MUTED, anchor="end"))

    # Zero reference lines when the origin is inside the plotted range.
    if x_lo < 0 < x_hi:
        zx = map_x(0.0)
        parts.append(_line(zx, m_top, zx, m_top + plot_h, stroke=AXIS,
                           extra='stroke-dasharray="3 3"'))
    if y_lo < 0 < y_hi:
        zy = map_y(0.0)
        parts.append(_line(m_left, zy, m_left + plot_w, zy, stroke=AXIS,
                           extra='stroke-dasharray="3 3"'))

    order: List[str] = []
    for _, _, _, group in clean:
        if group not in order:
            order.append(group)
    color_of = {group: SERIES[i % len(SERIES)] for i, group in enumerate(order)}

    show_labels = len(clean) <= label_limit
    for x, y, name, group in clean:
        cx, cy = map_x(x), map_y(y)
        dot = _circle(cx, cy, 5, color_of[group],
                      extra='stroke="#ffffff" stroke-width="1"')
        parts.append(_tip(dot, f"{name} · {group} ({_fmt(x, 3)}, {_fmt(y, 3)})"))
        if show_labels:
            parts.append(_text(cx + 7, cy + 3, _clip(name, 14), size=9.5,
                               fill=MUTED))

    parts.append(_text(m_left + plot_w / 2, height - 16, x_label, size=12,
                       fill=INK, anchor="middle", weight="500"))
    parts.append(f'<text x="18" y="{m_top + plot_h / 2:.1f}" font-size="12" '
                 f'fill="{INK}" text-anchor="middle" font-weight="500" '
                 f'transform="rotate(-90 18 {m_top + plot_h / 2:.1f})">'
                 f'{_esc(y_label)}</text>')

    # Legend (grouped colours), only when groups actually distinguish points.
    if len(order) > 1:
        lx = m_left + 8
        ly = m_top + 8
        for group in order[:8]:
            parts.append(_circle(lx + 5, ly + 4, 5, color_of[group]))
            parts.append(_text(lx + 15, ly + 8, _clip(group, 18), size=11,
                               fill=INK))
            ly += 18
    return _svg(width, height, "".join(parts))


def heatmap_svg(title: str, labels: Sequence[str],
                matrix: Sequence[Sequence[Any]], *,
                max_cells: int = 44) -> str:
    """Symmetric distance heatmap with a sequential colour scale."""
    labels = list(labels)
    n = len(labels)
    if n < 2:
        return _empty("—", width=640, height=160)
    show = min(n, max_cells)
    values = [_num(matrix[i][j]) for i in range(show) for j in range(show)]
    finite = [v for v in values if v is not None]
    if not finite:
        return _empty("—", width=640, height=160)
    vmin, vmax = min(finite), max(finite)
    span = (vmax - vmin) or 1.0
    cell = max(9.0, min(22.0, 560.0 / show))
    label_w = 118.0
    top = 52.0
    grid = cell * show
    width = label_w + grid + 150
    height = top + grid + 30
    low, high = (238, 245, 251), (8, 66, 120)  # light -> deep blue
    parts: List[str] = [_text(16, 28, title, size=15, weight="600")]

    for i in range(show):
        y = top + i * cell
        if cell >= 12:
            parts.append(_text(label_w - 6, y + cell * 0.68, _clip(labels[i], 16),
                               size=min(11, cell * 0.62), fill=INK, anchor="end"))
        for j in range(show):
            x = label_w + j * cell
            value = _num(matrix[i][j])
            if value is None:
                fill = "#dfe4e7"
                tip = f"{labels[i]} · {labels[j]}: NaN"
            else:
                fill = _lerp_color(low, high, (value - vmin) / span)
                tip = f"{labels[i]} · {labels[j]}: {_fmt(value, 4)}"
            rect = _rect(x, y, cell - 0.6, cell - 0.6, fill, rx=1.5)
            parts.append(_tip(rect, tip))

    # Colour legend gradient.
    gx = label_w + grid + 28
    gy = top
    gh = min(grid, 220.0)
    parts.append(
        '<defs><linearGradient id="hm" x1="0" y1="1" x2="0" y2="0">'
        f'<stop offset="0" stop-color="{_lerp_color(low, high, 0)}"/>'
        f'<stop offset="1" stop-color="{_lerp_color(low, high, 1)}"/>'
        '</linearGradient></defs>'
    )
    parts.append(_rect(gx, gy, 16, gh, "url(#hm)", rx=3,
                       extra=f'stroke="{GRID}"'))
    parts.append(_text(gx + 22, gy + 10, _fmt(vmax, 3), size=10, fill=MUTED))
    parts.append(_text(gx + 22, gy + gh, _fmt(vmin, 3), size=10, fill=MUTED))
    parts.append(_text(gx, gy - 8, "p-dist", size=10, fill=MUTED))
    if n > show:
        parts.append(_text(label_w, height - 10,
                           f"… {n} × {n}", size=10.5, fill=MUTED))
    return _svg(width, height, "".join(parts))


def vbar_svg(title: str, items: Sequence[Tuple[Any, Any]], *,
             x_label: str = "", y_label: str = "",
             color: str = SERIES[0],
             value_fmt: Callable[[Any], str] = _fmt) -> str:
    """Vertical bar chart / histogram from ``(label, value)`` pairs."""
    items = list(items)
    if not items:
        return _empty("—")
    width = min(880.0, max(420.0, 60 + len(items) * 46))
    height = 320.0
    m_left, m_right, m_top, m_bottom = 48.0, 18.0, 48.0, 46.0
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom
    numbers = [_num(value) or 0.0 for _, value in items]
    peak = max(numbers + [0.0]) or 1.0
    slot = plot_w / len(items)
    bar_w = min(46.0, slot * 0.62)
    parts: List[str] = [_text(16, 28, title, size=15, weight="600")]
    for i in range(4 + 1):
        vy = peak * i / 4
        gy = m_top + plot_h - (vy / peak) * plot_h
        parts.append(_line(m_left, gy, m_left + plot_w, gy, stroke="#eef2f4"))
        parts.append(_text(m_left - 6, gy + 3, _fmt(vy, 3), size=10,
                           fill=MUTED, anchor="end"))
    for index, (label, value) in enumerate(items):
        number = _num(value) or 0.0
        cx = m_left + slot * (index + 0.5)
        bar_h = number / peak * plot_h
        bar = _rect(cx - bar_w / 2, m_top + plot_h - bar_h, bar_w, bar_h,
                    color, rx=3)
        parts.append(_tip(bar, f"{label}: {value_fmt(value)}"))
        parts.append(_text(cx, m_top + plot_h + 16, _clip(label, 8), size=10,
                           fill=MUTED, anchor="middle"))
    if x_label:
        parts.append(_text(m_left + plot_w / 2, height - 8, x_label, size=11,
                           fill=INK, anchor="middle"))
    if y_label:
        parts.append(f'<text x="14" y="{m_top + plot_h / 2:.1f}" font-size="11" '
                     f'fill="{INK}" text-anchor="middle" '
                     f'transform="rotate(-90 14 {m_top + plot_h / 2:.1f})">'
                     f'{_esc(y_label)}</text>')
    return _svg(width, height, "".join(parts))


def site_track_svg(title: str, alignment_length: int, sites: Sequence[Any], *,
                   tr: Tr) -> str:
    """Genome-browser style overview of variation / missing data by position.

    ``sites`` are ``SiteQuality`` objects (``position``, ``missing_rate``,
    ``variable``, ``parsimony_informative``). Positions are binned to the chart
    width so long alignments still render as a compact track.
    """
    sites = list(sites)
    length = int(alignment_length) or (len(sites) or 1)
    if not sites:
        return _empty("—", width=900, height=140)
    width = 900.0
    m_left, m_right, m_top = 54.0, 18.0, 48.0
    plot_w = width - m_left - m_right
    var_h, miss_h, lane_gap = 70.0, 30.0, 26.0
    height = m_top + var_h + lane_gap + miss_h + 40
    bins = int(min(plot_w, max(40, length)))
    var_frac = [0.0] * bins
    pi_frac = [0.0] * bins
    miss_mean = [0.0] * bins
    counts = [0] * bins
    for site in sites:
        position = int(getattr(site, "position", 0) or 0)
        idx = min(bins - 1, max(0, int((position - 1) / max(1, length) * bins)))
        counts[idx] += 1
        if getattr(site, "variable", False):
            var_frac[idx] += 1
        if getattr(site, "parsimony_informative", False):
            pi_frac[idx] += 1
        miss_mean[idx] += _num(getattr(site, "missing_rate", 0)) or 0.0

    col_w = plot_w / bins
    var_top = m_top
    var_base = var_top + var_h
    miss_top = var_base + lane_gap
    parts: List[str] = [_text(16, 28, title, size=15, weight="600")]
    parts.append(_text(m_left, var_top - 8, tr("变异密度", "Variation density"),
                       size=11, fill=MUTED))
    parts.append(_rect(m_left, var_top, plot_w, var_h, "#fbfcfd", rx=4,
                       extra=f'stroke="{GRID}"'))
    miss_lo, miss_hi = (255, 255, 255), (209, 73, 91)
    for i in range(bins):
        if not counts[i]:
            continue
        x = m_left + i * col_w
        var_ratio = var_frac[i] / counts[i]
        pi_ratio = pi_frac[i] / counts[i]
        vh = var_ratio * var_h
        if vh > 0:
            bar = _rect(x, var_base - vh, max(col_w, 0.8), vh, "#a9c6de")
            parts.append(_tip(bar,
                              f"~{int(i / bins * length) + 1}: "
                              f"{tr('变异', 'variable')} {_pct(var_ratio)}"))
        ph = pi_ratio * var_h
        if ph > 0:
            parts.append(_rect(x, var_base - ph, max(col_w, 0.8), ph, "#2f6f9f"))
        miss_ratio = (miss_mean[i] / counts[i]) if counts[i] else 0.0
        cell = _rect(x, miss_top, max(col_w, 0.8), miss_h,
                     _lerp_color(miss_lo, miss_hi, min(1.0, miss_ratio)))
        parts.append(_tip(cell,
                          f"~{int(i / bins * length) + 1}: "
                          f"{tr('缺失', 'missing')} {_pct(miss_ratio)}"))
    parts.append(_text(m_left, miss_top - 6, tr("缺失率", "Missing rate"),
                       size=11, fill=MUTED))
    parts.append(_rect(m_left, miss_top, plot_w, miss_h, "none", rx=4,
                       extra=f'stroke="{GRID}"'))
    # Position axis.
    axis_y = miss_top + miss_h + 20
    for i in range(5):
        pos = round(length * i / 4)
        gx = m_left + plot_w * i / 4
        parts.append(_line(gx, miss_top + miss_h, gx, miss_top + miss_h + 4,
                           stroke=AXIS))
        parts.append(_text(gx, axis_y, str(pos), size=10, fill=MUTED,
                           anchor="middle" if 0 < i < 4 else
                           ("start" if i == 0 else "end")))
    # Legend.
    lx = m_left + plot_w - 250
    parts.append(_rect(lx, var_top - 20, 10, 10, "#2f6f9f", rx=2))
    parts.append(_text(lx + 15, var_top - 11,
                       tr("简约信息位点", "Parsimony-informative"), size=10,
                       fill=MUTED))
    parts.append(_rect(lx + 150, var_top - 20, 10, 10, "#a9c6de", rx=2))
    parts.append(_text(lx + 165, var_top - 11, tr("变异位点", "Variable"),
                       size=10, fill=MUTED))
    return _svg(width, height, "".join(parts))


# --------------------------------------------------------------------------- #
# Report-level figure builders
# --------------------------------------------------------------------------- #
def diversity_cards(result: Any, tr: Tr) -> List[dict]:
    quality = result.quality
    overall = result.overall
    return [
        {"label": tr("样本数", "Samples"), "value": _fmt(quality.sample_count),
         "tone": "info"},
        {"label": tr("比对长度", "Alignment length"),
         "value": _fmt(quality.alignment_length), "tone": "neutral"},
        {"label": tr("总体缺失率", "Overall missing"),
         "value": _pct(quality.total_missing_rate),
         "tone": _missing_tone(quality.total_missing_rate)},
        {"label": tr("变异位点", "Variable sites"),
         "value": _fmt(quality.variable_site_count),
         "sub": tr(f"简约信息 {quality.parsimony_informative_site_count}",
                   f"{quality.parsimony_informative_site_count} informative"),
         "tone": "info"},
        {"label": tr("单倍型多样性 Hd", "Haplotype div. Hd"),
         "value": _fmt(overall.hd), "tone": "accent"},
        {"label": tr("核苷酸多样性 π", "Nucleotide div. π"),
         "value": _fmt(overall.pi), "tone": "accent"},
    ]


def diversity_figures(result: Any, tr: Tr) -> List[dict]:
    figures: List[dict] = []
    groups = list(result.groups)
    if len(groups) >= 1:
        labels = [group.label for group in groups]
        metrics = [
            (tr("样本数", "N"), SERIES[4], [g.sample_count for g in groups], _fmt),
            (tr("单倍型数", "Haplotypes"), SERIES[0],
             [g.haplotype_richness for g in groups], _fmt),
            ("Hd", SERIES[1], [g.hd for g in groups], _fmt),
            ("π", SERIES[2], [g.pi for g in groups], _fmt),
            ("θW", SERIES[3], [g.theta_w for g in groups], _fmt),
        ]
        figures.append({
            "svg": group_metric_panels_svg(
                tr("分组多样性对比", "Group diversity comparison"),
                labels, metrics),
            "desc": tr(
                "每个面板按各自量程独立缩放；组间比较应同时结合样本量与缺失率。",
                "Each panel is scaled independently; compare groups alongside "
                "their sample sizes and missing rates."),
        })

    samples = sorted(result.quality.samples,
                     key=lambda s: _num(s.missing_rate) or 0.0, reverse=True)
    top = [s for s in samples if (_num(s.missing_rate) or 0.0) > 0][:25]
    if top:
        figures.append({
            "svg": hbar_svg(
                tr("样本缺失率（前 25）", "Sample missing rate (top 25)"),
                [(s.sample_name, s.missing_rate) for s in top],
                value_fmt=lambda v: _pct(v), color_fn=_missing_color,
                max_value=max(_num(s.missing_rate) or 0.0 for s in top),
                note=tr("按缺失率降序", "sorted by missing rate")),
            "desc": tr(
                "绿 / 黄 / 红 分别表示低 (<5%) / 中 (<20%) / 高 缺失比例。",
                "Green / amber / red mark low (<5%) / medium (<20%) / high "
                "missing proportions."),
        })

    if result.quality.sites:
        figures.append({
            "svg": site_track_svg(
                tr("位点变异与缺失分布", "Per-site variation and missing data"),
                result.quality.alignment_length, result.quality.sites, tr=tr),
            "desc": tr(
                "沿比对位置概览：上轨为变异密度（深色为简约信息位点），下轨为缺失率热带。",
                "Overview along the alignment: the top lane shows variability "
                "density (dark = parsimony-informative), the bottom lane is a "
                "missing-rate heat strip."),
        })
    return figures


def distance_cards(result: Any, tr: Tr) -> List[dict]:
    n = len(result.labels)
    pair_count = n * (n - 1) // 2
    unavailable = sum(
        _num(result.distance_matrix[i][j]) is None
        for i in range(n) for j in range(i + 1, n))
    ratios = list(result.pcoa.explained_variance_ratio)
    negative = result.pcoa.negative_eigenvalue_ratio
    return [
        {"label": tr("序列数", "Sequences"), "value": _fmt(n), "tone": "info"},
        {"label": tr("序列对", "Pairwise comparisons"),
         "value": _fmt(pair_count), "tone": "neutral"},
        {"label": tr("缺失距离对", "Unavailable pairs"),
         "value": _fmt(unavailable),
         "tone": "good" if not unavailable else "warn"},
        {"label": tr("PCoA 轴1 解释度", "PCoA axis 1"),
         "value": _pct(ratios[0]) if ratios else "—", "tone": "accent"},
        {"label": tr("PCoA 轴2 解释度", "PCoA axis 2"),
         "value": _pct(ratios[1]) if len(ratios) > 1 else "—", "tone": "accent"},
        {"label": tr("负特征值比例", "Negative eigenvalue"),
         "value": _pct(negative),
         "tone": "good" if (_num(negative) or 0) < 0.1 else "warn"},
    ]


def distance_figures(result: Any, tr: Tr,
                     group_map: Optional[Mapping[str, str]] = None) -> List[dict]:
    figures: List[dict] = []
    group_map = group_map or {}
    ungrouped = tr("未分组", "Ungrouped")
    ratios = list(result.pcoa.explained_variance_ratio)
    if result.pcoa.axis_count >= 2:
        coords = result.pcoa.coordinates
        points = [
            (coords[i][0], coords[i][1], label,
             group_map.get(label) or ungrouped)
            for i, label in enumerate(result.labels)
            if len(coords[i]) >= 2
        ]
        x_label = tr(f"PCoA 轴 1 ({_pct(ratios[0])})",
                     f"PCoA axis 1 ({_pct(ratios[0])})") if ratios else "PCoA 1"
        y_label = tr(f"PCoA 轴 2 ({_pct(ratios[1])})",
                     f"PCoA axis 2 ({_pct(ratios[1])})") \
            if len(ratios) > 1 else "PCoA 2"
        figures.append({
            "svg": scatter_svg(tr("PCoA 排序图", "PCoA ordination"),
                               points, x_label, y_label),
            "desc": tr(
                "点间距离越近表示序列越相似；聚集仅供探索，不能单独证明群体或传播关系。",
                "Closer points are more similar sequences; clustering is "
                "exploratory and does not by itself establish populations or "
                "transmission."),
        })

    figures.append({
        "svg": heatmap_svg(tr("遗传距离热图", "Genetic distance heatmap"),
                           result.labels, result.distance_matrix),
        "desc": tr(
            "颜色越深表示 p-distance 越大；灰色格表示可比位点不足、距离不可用。",
            "Darker cells are larger p-distances; grey cells are pairs with "
            "too few comparable sites (distance unavailable)."),
    })
    return figures


def topology_cards(result: Any, tr: Tr) -> List[dict]:
    graph = result.graph
    return [
        {"label": tr("节点数", "Nodes"), "value": _fmt(graph.node_count),
         "sub": tr(f"中间节点 {graph.intermediate_node_count}",
                   f"{graph.intermediate_node_count} intermediate"),
         "tone": "info"},
        {"label": tr("边数", "Edges"), "value": _fmt(graph.edge_count),
         "tone": "neutral"},
        {"label": tr("连通分量", "Components"),
         "value": _fmt(graph.component_count),
         "tone": "good" if graph.component_count <= 1 else "warn"},
        {"label": tr("网络密度", "Density"), "value": _fmt(graph.density),
         "tone": "accent"},
        {"label": tr("环秩", "Cycle rank"), "value": _fmt(graph.cycle_rank),
         "sub": tr("独立环数", "independent loops"),
         "tone": "accent"},
        {"label": tr("观测单倍型", "Observed nodes"),
         "value": _fmt(graph.observed_node_count), "tone": "info"},
    ]


def topology_figures(result: Any, tr: Tr) -> List[dict]:
    figures: List[dict] = []
    nodes = list(result.nodes)
    if nodes:
        degree_counts: dict = {}
        for node in nodes:
            degree_counts[node.degree] = degree_counts.get(node.degree, 0) + 1
        items = [(str(deg), count)
                 for deg, count in sorted(degree_counts.items())]
        figures.append({
            "svg": vbar_svg(tr("节点度分布", "Node degree distribution"),
                            items,
                            x_label=tr("度（相邻单倍型数）", "Degree (neighbours)"),
                            y_label=tr("节点数", "Node count")),
            "desc": tr(
                "多数单倍型只与少数邻居相连；高度节点是网络枢纽。",
                "Most haplotypes connect to only a few neighbours; high-degree "
                "nodes are network hubs."),
        })

        ranked = sorted(nodes, key=lambda n: _num(n.betweenness) or 0.0,
                        reverse=True)
        top = [n for n in ranked if (_num(n.betweenness) or 0.0) > 0][:20]
        if top:
            figures.append({
                "svg": _topology_hub_svg(top, tr),
                "desc": tr(
                    "介数越高的节点越可能位于网络的关键通路上；割点移除后会切断网络。",
                    "Higher-betweenness nodes lie on more of the network's "
                    "shortest paths; removing an articulation point disconnects "
                    "the network."),
            })
    return figures


def _topology_hub_svg(nodes: Sequence[Any], tr: Tr) -> str:
    """Horizontal betweenness bars with articulation points highlighted red."""
    articulation = {str(node.node_id) for node in nodes
                    if node.articulation_point}
    peak = max((_num(node.betweenness) or 0.0 for node in nodes), default=0.0) \
        or 1.0
    width = 860.0
    top = 48.0
    row_h = 26.0
    label_w = 196.0
    plot_left = label_w + 12
    plot_w = width - plot_left - 96
    height = top + row_h * len(nodes) + 16
    parts: List[str] = [
        _text(16, 28, tr("枢纽节点（介数中心性前 20）",
                         "Hub nodes (top 20 by betweenness)"),
              size=15, weight="600"),
        _text(width - 16, 28, tr("红色为割点", "red = articulation point"),
              size=11, fill=MUTED, anchor="end"),
    ]
    for index, node in enumerate(nodes):
        y = top + index * row_h
        node_id = str(node.node_id)
        is_cut = node_id in articulation
        colour_value = TONE["bad"] if is_cut else TONE["neutral"]
        value = _num(node.betweenness) or 0.0
        parts.append(_text(label_w, y + row_h * 0.68, _clip(node_id, 28),
                           size=12, anchor="end",
                           fill=TONE["bad"] if is_cut else INK))
        parts.append(_rect(plot_left, y + 4, plot_w, row_h - 10, GRID, rx=4))
        bar_len = value / peak * plot_w
        bar = _rect(plot_left, y + 4, bar_len, row_h - 10, colour_value, rx=4)
        parts.append(_tip(bar, f"{node_id}: {_fmt(value, 4)}"
                               + (tr(" · 割点", " · articulation") if is_cut else "")))
        parts.append(_text(plot_left + bar_len + 6, y + row_h * 0.68,
                           _fmt(value, 3), size=11.5, fill=MUTED))
    return _svg(width, height, "".join(parts))


# --------------------------------------------------------------------------- #
# Page assembly
# --------------------------------------------------------------------------- #
def figures_html(figures: Sequence[Mapping[str, Any]],
                 background: str = "#ffffff") -> str:
    """Wrap figures into a responsive HTML page for a QWebEngineView."""
    blocks: List[str] = []
    for figure in figures:
        svg = figure.get("svg") or ""
        if not svg:
            continue
        desc = figure.get("desc")
        caption = f'<p class="desc">{_esc(desc)}</p>' if desc else ""
        blocks.append(f'<section class="fig">{svg}{caption}</section>')
    body = "".join(blocks) or (
        f'<p class="empty">{_esc("—")}</p>')
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        '<style>'
        f'*{{box-sizing:border-box;}}'
        f'body{{margin:0;padding:16px;background:{background};'
        f'font-family:{FONT};color:{INK};}}'
        '.fig{background:#fff;border:1px solid ' + BORDER + ';border-radius:12px;'
        'padding:14px 16px 12px;margin:0 0 16px;'
        'box-shadow:0 1px 3px rgba(20,40,60,.05);}'
        '.fig svg{width:100%;height:auto;display:block;}'
        f'.desc{{margin:10px 2px 2px;color:{MUTED};font-size:12.5px;'
        'line-height:1.55;}'
        f'.empty{{color:{MUTED};text-align:center;padding:40px;}}'
        '</style></head><body>' + body + '</body></html>'
    )
