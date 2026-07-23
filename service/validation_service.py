"""Pure validation helpers shared by GUI analysis workflows."""

from dataclasses import dataclass, field
import math
import os
import re
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    details: Dict[str, Any] = field(default_factory=dict)


def find_duplicates(values: Iterable[str]) -> List[str]:
    seen = set()
    duplicates = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def has_meaningful_continuous_trait(value: Any) -> bool:
    """Return whether a trait is finite and numerically different from zero."""
    try:
        numeric = float(str(value).strip())
    except (TypeError, ValueError):
        return False
    return math.isfinite(numeric) and numeric != 0.0


def validate_taxons(taxons: Iterable[Any]) -> Optional[ValidationIssue]:
    """Validate only the taxons that will actually enter an analysis."""
    selected = list(taxons)
    for taxon in selected:
        name = str(getattr(taxon, "name", "")).strip()
        sequence = str(getattr(taxon, "sequence", "")).strip()
        continuous = str(getattr(taxon, "continuous_traits", "")).strip()
        taxon_id = getattr(taxon, "id", "")

        if not name:
            return ValidationIssue("empty_name", {"id": taxon_id})
        if re.search(r"\s", name):
            return ValidationIssue(
                "invalid_name_whitespace", {"id": taxon_id, "name": name})
        if not sequence:
            return ValidationIssue("empty_sequence", {"id": taxon_id, "name": name})
        try:
            continuous_value = float(continuous)
        except (TypeError, ValueError):
            return ValidationIssue(
                "invalid_continuous",
                {"id": taxon_id, "name": name, "value": continuous},
            )
        if not math.isfinite(continuous_value):
            return ValidationIssue(
                "invalid_continuous",
                {"id": taxon_id, "name": name, "value": continuous},
            )

    duplicates = find_duplicates(
        str(getattr(taxon, "name", "")).strip() for taxon in selected
    )
    if duplicates:
        return ValidationIssue("duplicate_names", {"names": duplicates})
    return None


def validate_project_prefix(prefix: str) -> Optional[ValidationIssue]:
    """Reject project names that can create paths outside the output folder."""
    value = prefix.strip()
    if not value:
        return ValidationIssue("empty_project_name")
    if value in {".", ".."}:
        return ValidationIssue("invalid_project_name", {"value": value})
    if os.path.isabs(value) or re.search(r'[\\/:*?"<>|\x00-\x1f]', value):
        return ValidationIssue("invalid_project_name", {"value": value})
    if value.endswith((" ", ".")):
        return ValidationIssue("invalid_project_name", {"value": value})
    windows_stem = value.split('.')[0].upper()
    if windows_stem in {
        'CON', 'PRN', 'AUX', 'NUL',
        *(f'COM{i}' for i in range(1, 10)),
        *(f'LPT{i}' for i in range(1, 10)),
    }:
        return ValidationIssue("invalid_project_name", {"value": value})
    return None
