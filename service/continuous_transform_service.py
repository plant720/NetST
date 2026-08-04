"""Convert imported continuous metadata into visualization-ready numbers.

The source metadata file remains untouched.  A conversion rule is selected for
each continuous column in the import dialog, then every non-empty cell is
validated and converted before it enters the project's trait table.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime
import math
import re
from typing import Dict, Optional, Sequence, Tuple


MODE_NUMBER = "number"
MODE_DATE = "date"
MODE_MEASUREMENT = "measurement"
TRANSFORM_MODES = (MODE_NUMBER, MODE_DATE, MODE_MEASUREMENT)

DATE_DAYS = "days"
DATE_MONTHS = "months"
DATE_YEARS = "years"
DATE_UNITS = (DATE_DAYS, DATE_MONTHS, DATE_YEARS)

QUANTITY_LENGTH = "length"
QUANTITY_MASS = "mass"
QUANTITY_TEMPERATURE = "temperature"
QUANTITIES = (QUANTITY_LENGTH, QUANTITY_MASS, QUANTITY_TEMPERATURE)

# Unit definitions are (scale, offset) for: base = value * scale + offset.
# Base units are metre, gram and degree Celsius respectively.
UNIT_DEFINITIONS: Dict[str, Dict[str, Tuple[float, float]]] = {
    QUANTITY_LENGTH: {
        "mm": (0.001, 0.0),
        "cm": (0.01, 0.0),
        "m": (1.0, 0.0),
        "km": (1000.0, 0.0),
        "in": (0.0254, 0.0),
        "ft": (0.3048, 0.0),
    },
    QUANTITY_MASS: {
        "mg": (0.001, 0.0),
        "g": (1.0, 0.0),
        "kg": (1000.0, 0.0),
    },
    QUANTITY_TEMPERATURE: {
        "c": (1.0, 0.0),
        "f": (5.0 / 9.0, -32.0 * 5.0 / 9.0),
        "k": (1.0, -273.15),
    },
}

_UNIT_ALIASES = {
    "millimeter": "mm", "millimeters": "mm", "毫米": "mm",
    "centimeter": "cm", "centimeters": "cm", "厘米": "cm",
    "meter": "m", "meters": "m", "metre": "m", "metres": "m", "米": "m",
    "kilometer": "km", "kilometers": "km", "千米": "km",
    "inch": "in", "inches": "in",
    "foot": "ft", "feet": "ft",
    "milligram": "mg", "milligrams": "mg", "毫克": "mg",
    "gram": "g", "grams": "g", "克": "g",
    "kilogram": "kg", "kilograms": "kg", "千克": "kg", "公斤": "kg",
    "°c": "c", "℃": "c", "celsius": "c",
    "°f": "f", "℉": "f", "fahrenheit": "f",
    "kelvin": "k",
}

_NUMBER_PATTERN = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_MEASUREMENT_RE = re.compile(
    rf"^\s*(?P<number>{_NUMBER_PATTERN})\s*(?P<unit>[^\d\s]+)?\s*$")


class ContinuousTransformError(ValueError):
    """Raised when a continuous value or conversion rule is invalid."""


@dataclass(frozen=True)
class ContinuousTransform:
    """How one imported continuous column is converted to numeric values."""

    mode: str = MODE_NUMBER
    date_unit: str = DATE_YEARS
    date_origin: str = ""  # blank means earliest valid date in the column
    quantity: str = QUANTITY_LENGTH
    target_unit: str = "m"
    bare_unit: str = "m"  # unit assumed when a measurement has no suffix


def parse_date_value(value: object) -> date:
    """Parse common ISO-like dates such as 2022-10-1 or 2022/10/1."""
    text = _as_text(value)
    if not text:
        raise ContinuousTransformError("date is empty")

    # datetime.fromisoformat handles ISO dates/times and timezone suffixes.
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    for pattern in (
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%Y-%m", "%Y/%m", "%Y.%m", "%Y",
    ):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ContinuousTransformError(
        f"unsupported date {text!r}; use YYYY-MM-DD, YYYY/MM/DD, YYYY-MM or YYYY")


def transform_continuous_values(
    values: Sequence[object],
    transform: Optional[ContinuousTransform] = None,
    *,
    row_numbers: Optional[Sequence[int]] = None,
) -> Tuple[str, ...]:
    """Convert one continuous column, preserving blank cells as blank strings."""
    rule = transform or ContinuousTransform()
    _validate_rule(rule)
    rows = list(row_numbers) if row_numbers is not None else list(range(1, len(values) + 1))
    if len(rows) != len(values):
        raise ValueError("row_numbers must match values")

    origin: Optional[date] = None
    parsed_dates: Dict[int, date] = {}
    if rule.mode == MODE_DATE:
        for index, raw in enumerate(values):
            if not _as_text(raw):
                continue
            try:
                parsed_dates[index] = parse_date_value(raw)
            except ContinuousTransformError as exc:
                raise ContinuousTransformError(f"row {rows[index]}: {exc}") from exc
        if rule.date_origin.strip():
            try:
                origin = parse_date_value(rule.date_origin)
            except ContinuousTransformError as exc:
                raise ContinuousTransformError(f"invalid start date: {exc}") from exc
        elif parsed_dates:
            origin = min(parsed_dates.values())

    converted = []
    for index, raw in enumerate(values):
        text = _as_text(raw)
        if not text:
            converted.append("")
            continue
        try:
            if rule.mode == MODE_NUMBER:
                number = _parse_plain_number(text)
            elif rule.mode == MODE_DATE:
                if origin is None:
                    raise ContinuousTransformError("cannot determine a start date")
                days = (parsed_dates[index] - origin).days
                if rule.date_unit == DATE_DAYS:
                    number = float(days)
                else:
                    months = _elapsed_calendar_months(origin, parsed_dates[index])
                    number = months if rule.date_unit == DATE_MONTHS else months / 12.0
            else:
                number = _convert_measurement(text, rule)
        except ContinuousTransformError as exc:
            raise ContinuousTransformError(f"row {rows[index]}: {exc}") from exc
        converted.append(_format_number(number))
    return tuple(converted)


def _as_text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _validate_rule(rule: ContinuousTransform) -> None:
    if rule.mode not in TRANSFORM_MODES:
        raise ContinuousTransformError(f"unknown continuous conversion mode: {rule.mode}")
    if rule.mode == MODE_DATE and rule.date_unit not in DATE_UNITS:
        raise ContinuousTransformError(f"unknown elapsed-time unit: {rule.date_unit}")
    if rule.mode == MODE_MEASUREMENT:
        units = UNIT_DEFINITIONS.get(rule.quantity)
        if units is None:
            raise ContinuousTransformError(f"unknown measurement type: {rule.quantity}")
        target = _normalize_unit(rule.target_unit)
        bare = _normalize_unit(rule.bare_unit or rule.target_unit)
        if target not in units:
            raise ContinuousTransformError(
                f"unit {rule.target_unit!r} is not valid for {rule.quantity}")
        if bare not in units:
            raise ContinuousTransformError(
                f"unit {rule.bare_unit!r} is not valid for {rule.quantity}")


def _parse_plain_number(text: str) -> float:
    if not re.fullmatch(_NUMBER_PATTERN, text):
        raise ContinuousTransformError(
            f"{text!r} is not a number; choose Date or Measurement conversion if needed")
    number = float(text)
    if not math.isfinite(number):
        raise ContinuousTransformError(f"{text!r} is not finite")
    return number


def _normalize_unit(unit: object) -> str:
    text = str(unit or "").strip().lower().replace("μ", "u").replace("µ", "u")
    return _UNIT_ALIASES.get(text, text)


def _convert_measurement(text: str, rule: ContinuousTransform) -> float:
    match = _MEASUREMENT_RE.fullmatch(text)
    if match is None:
        raise ContinuousTransformError(
            f"cannot parse measurement {text!r}; examples: 1.5m, 120 cm")
    value = float(match.group("number"))
    source = _normalize_unit(match.group("unit") or rule.bare_unit or rule.target_unit)
    target = _normalize_unit(rule.target_unit)
    units = UNIT_DEFINITIONS[rule.quantity]
    if source not in units:
        raise ContinuousTransformError(
            f"unit {match.group('unit')!r} is not valid for {rule.quantity}")
    source_scale, source_offset = units[source]
    target_scale, target_offset = units[target]
    base_value = value * source_scale + source_offset
    return (base_value - target_offset) / target_scale


def _elapsed_calendar_months(origin: date, current: date) -> float:
    """Return a calendar-aware, fractional month interval.

    Matching days in adjacent months are exactly one month apart. A remaining
    partial month is divided by the length of the relevant anchored month. This
    is more intuitive for sampling dates than dividing every interval by a
    fixed average month length.
    """
    if current == origin:
        return 0.0
    if current < origin:
        return -_elapsed_calendar_months(current, origin)

    whole_months = (current.year - origin.year) * 12 + current.month - origin.month
    anchor = _add_months(origin, whole_months)
    if anchor > current:
        whole_months -= 1
        anchor = _add_months(origin, whole_months)
    next_anchor = _add_months(origin, whole_months + 1)
    span_days = (next_anchor - anchor).days
    fraction = (current - anchor).days / span_days if span_days else 0.0
    return whole_months + fraction


def _add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        raise ContinuousTransformError("converted value is not finite")
    if abs(value) < 5e-13:
        value = 0.0
    return format(value, ".12g")
