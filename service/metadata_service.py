"""Pure logic for importing multi-trait sample metadata.

The Load Metadata workflow lets the user tag each column of a CSV/TSV as the
sample name, a discrete trait, or a continuous trait, and pick which discrete
trait is the group. This module turns that column mapping plus the data rows
into a :class:`~model.trait_schema.TraitSchema` and a per-sample value map,
enforcing the rule that at least one discrete trait (the group) is present.

It has no Qt dependency: the dialog only collects the mapping; all validation
and construction happen here so they can be unit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from model.trait_schema import CONTINUOUS, DISCRETE, TraitDefinition, TraitSchema
from service.continuous_transform_service import (
    ContinuousTransform,
    ContinuousTransformError,
    transform_continuous_values,
)
from service.validation_service import find_duplicates


class MetadataImportError(ValueError):
    """Raised when a metadata column mapping or its data is invalid."""


@dataclass(frozen=True)
class TraitColumn:
    """One column mapped to a trait, with its declared kind."""

    index: int
    name: str
    kind: str  # DISCRETE or CONTINUOUS
    transform: Optional[ContinuousTransform] = None


@dataclass(frozen=True)
class MetadataMapping:
    """The column roles chosen in the Load Metadata dialog."""

    name_col: int
    trait_columns: Tuple[TraitColumn, ...]
    group_trait: Optional[str] = None


@dataclass(frozen=True)
class MetadataImport:
    """Result of interpreting a metadata table against a column mapping."""

    schema: TraitSchema
    values_by_sample: Dict[str, Dict[str, str]]
    warnings: Tuple[str, ...] = ()


def _cell(row: Sequence[str], index: int) -> str:
    return row[index].strip() if 0 <= index < len(row) else ""


def build_metadata(
    data_rows: Sequence[Sequence[str]],
    mapping: MetadataMapping,
) -> MetadataImport:
    """Build a trait schema and per-sample values from mapped columns.

    Args:
        data_rows: Data rows (header already removed) as lists of cells.
        mapping: Column roles selected by the user.

    Returns:
        A :class:`MetadataImport` with the schema, ``{sample: {trait: value}}``,
        and any non-fatal warnings.
    """
    trait_columns = list(mapping.trait_columns)
    if not trait_columns:
        raise MetadataImportError("Select at least one trait column")

    names = [column.name.strip() for column in trait_columns]
    if any(not name for name in names):
        raise MetadataImportError("Every trait column needs a non-empty name")
    duplicate_names = find_duplicates(names)
    if duplicate_names:
        raise MetadataImportError(
            "Duplicate trait names: " + ", ".join(duplicate_names))
    if mapping.name_col in {column.index for column in trait_columns}:
        raise MetadataImportError(
            "The sample-name column cannot also be used as a trait")

    for column in trait_columns:
        if column.kind not in (DISCRETE, CONTINUOUS):
            raise MetadataImportError(
                f"Trait {column.name!r} has an unknown kind: {column.kind!r}")

    discrete_names = [c.name for c in trait_columns if c.kind == DISCRETE]
    if not discrete_names:
        raise MetadataImportError(
            "At least one discrete trait is required to serve as the group")

    group = mapping.group_trait
    if group is not None and group not in discrete_names:
        raise MetadataImportError(
            f"The group trait {group!r} must be one of the discrete traits")
    if group is None:
        group = discrete_names[0]

    schema = TraitSchema([
        TraitDefinition(name=column.name, kind=column.kind, order=index)
        for index, column in enumerate(trait_columns)
    ])
    schema.set_group(group)

    values_by_sample: Dict[str, Dict[str, str]] = {}
    warnings: List[str] = []
    seen_names: set = set()
    usable_rows = []
    for row_number, row in enumerate(data_rows, start=2):
        sample = _cell(row, mapping.name_col)
        if not sample:
            continue
        if sample in seen_names:
            raise MetadataImportError(
                f"Duplicate sample in metadata: {sample}")
        seen_names.add(sample)
        usable_rows.append((row_number, row, sample))

    converted_columns: Dict[int, Tuple[str, ...]] = {}
    for column in trait_columns:
        if column.kind != CONTINUOUS:
            if column.transform is not None:
                raise MetadataImportError(
                    f"Categorical trait {column.name!r} cannot use a numeric conversion")
            continue
        try:
            converted_columns[column.index] = transform_continuous_values(
                [_cell(row, column.index) for _row_number, row, _sample in usable_rows],
                column.transform,
                row_numbers=[row_number for row_number, _row, _sample in usable_rows],
            )
        except ContinuousTransformError as exc:
            raise MetadataImportError(f"Trait {column.name!r}: {exc}") from exc

    for usable_index, (_row_number, row, sample) in enumerate(usable_rows):
        sample_values: Dict[str, str] = {}
        for column in trait_columns:
            if column.kind == CONTINUOUS:
                sample_values[column.name] = converted_columns[column.index][usable_index]
            else:
                sample_values[column.name] = _cell(row, column.index)
        values_by_sample[sample] = sample_values

    if not values_by_sample:
        raise MetadataImportError("The metadata table has no usable rows")

    return MetadataImport(
        schema=schema,
        values_by_sample=values_by_sample,
        warnings=tuple(warnings),
    )
