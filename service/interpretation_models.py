"""Canonical, immutable data models used by interpretation analyses.

The desktop data table stores mutable :class:`model.taxon_data.TaxonData`
objects.  Interpretation services deliberately consume a small immutable
snapshot instead, so a background calculation cannot observe partially edited
rows.  The adapter also accepts mappings and simple objects with
``name``/``sequence`` attributes, which keeps the computation layer independent
from PyQt and file formats.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Tuple


class AnalysisDataError(ValueError):
    """Raised when records cannot form a valid aligned analysis dataset."""


def _record_value(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(key, default)
    return getattr(record, key, default)


def _normalise_trait_pairs(value: Any, default_name: str) -> Tuple[Tuple[str, str], ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, Mapping):
        pairs = value.items()
    elif isinstance(value, str):
        pairs = ((default_name, value),)
    else:
        try:
            pairs = tuple(value)
        except TypeError as exc:
            raise AnalysisDataError(
                f"Traits for '{default_name}' must be a mapping, string, or key/value pairs"
            ) from exc

    normalised = []
    for key, trait_value in pairs:
        key_text = str(key).strip()
        if not key_text:
            raise AnalysisDataError("Trait names cannot be empty")
        normalised.append((key_text, str(trait_value).strip()))
    return tuple(sorted(normalised))


@dataclass(frozen=True)
class SequenceSample:
    """One aligned sequence and its traits.

    Traits are stored as sorted tuples rather than mutable dictionaries.  The
    ``traits`` properties expose read-only mapping views for convenient lookup.
    """

    name: str
    sequence: str
    discrete_trait_items: Tuple[Tuple[str, str], ...] = ()
    continuous_trait_items: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        sequence = "".join(str(self.sequence).split()).upper().replace("U", "T")
        if not name:
            raise AnalysisDataError("Sample names cannot be empty")
        if not sequence:
            raise AnalysisDataError(f"Sequence for sample '{name}' is empty")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "sequence", sequence)
        object.__setattr__(
            self,
            "discrete_trait_items",
            _normalise_trait_pairs(self.discrete_trait_items, "trait"),
        )
        object.__setattr__(
            self,
            "continuous_trait_items",
            _normalise_trait_pairs(self.continuous_trait_items, "continuous_trait"),
        )

    @property
    def discrete_traits(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self.discrete_trait_items))

    @property
    def continuous_traits(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self.continuous_trait_items))

    @property
    def traits(self) -> Mapping[str, str]:
        """Alias for discrete traits used by generic record adapters."""
        return self.discrete_traits

    def discrete_trait(self, name: str, default: str = "") -> str:
        return dict(self.discrete_trait_items).get(name, default)

    @classmethod
    def from_record(cls, record: Any, default_trait_name: str = "trait") -> "SequenceSample":
        """Create a sample from TaxonData, a mapping, or a simple object."""
        name = _record_value(record, "name", _record_value(record, "sample_id", ""))
        sequence = _record_value(record, "sequence", "")

        discrete = _record_value(record, "traits", None)
        if discrete is None:
            discrete = _record_value(record, "discrete_traits", None)
        continuous = _record_value(record, "continuous_traits", None)

        # TaxonData uses one string-valued discrete and continuous trait column.
        if isinstance(discrete, str):
            discrete = ((default_trait_name, discrete),) if discrete.strip() else ()
        if isinstance(continuous, str):
            continuous = (
                (("continuous_trait", continuous),) if continuous.strip() else ()
            )
        return cls(
            name=name,
            sequence=sequence,
            discrete_trait_items=discrete or (),
            continuous_trait_items=continuous or (),
        )


@dataclass(frozen=True)
class AnalysisDataset:
    """Validated immutable snapshot of an aligned sequence collection."""

    samples: Tuple[SequenceSample, ...]
    alignment_length: int
    source_label: str = ""

    def __post_init__(self) -> None:
        samples = tuple(self.samples)
        if not samples:
            raise AnalysisDataError("At least one sequence is required")
        lengths = {len(sample.sequence) for sample in samples}
        if len(lengths) != 1:
            details = ", ".join(
                f"{sample.name}={len(sample.sequence)}" for sample in samples[:5]
            )
            raise AnalysisDataError(f"Sequences must be aligned to equal length ({details})")
        length = lengths.pop()
        if length <= 0:
            raise AnalysisDataError("Aligned sequences cannot be empty")
        names = [sample.name for sample in samples]
        duplicate_names = sorted({name for name in names if names.count(name) > 1})
        if duplicate_names:
            raise AnalysisDataError(
                "Sample names must be unique: " + ", ".join(duplicate_names[:5])
            )
        if self.alignment_length not in (0, length):
            raise AnalysisDataError(
                f"alignment_length={self.alignment_length} does not match sequence length {length}"
            )
        object.__setattr__(self, "samples", samples)
        object.__setattr__(self, "alignment_length", length)

    @classmethod
    def from_records(
            cls,
            records: Iterable[Any],
            *,
            default_trait_name: str = "trait",
            source_label: str = "",
    ) -> "AnalysisDataset":
        samples = tuple(
            record
            if isinstance(record, SequenceSample)
            else SequenceSample.from_record(record, default_trait_name)
            for record in records
        )
        return cls(samples=samples, alignment_length=0, source_label=source_label)

    @classmethod
    def from_taxons(
            cls,
            taxons: Iterable[Any],
            *,
            trait_name: str = "trait",
            selected_only: bool = False,
            source_label: str = "",
    ) -> "AnalysisDataset":
        records = (
            taxon
            for taxon in taxons
            if not selected_only or bool(_record_value(taxon, "selected", True))
        )
        return cls.from_records(
            records,
            default_trait_name=trait_name,
            source_label=source_label,
        )

    @property
    def sample_count(self) -> int:
        return len(self.samples)


def ensure_analysis_dataset(
        data: Any,
        *,
        default_trait_name: str = "trait",
) -> AnalysisDataset:
    """Return ``data`` as an :class:`AnalysisDataset` snapshot."""
    if isinstance(data, AnalysisDataset):
        return data
    return AnalysisDataset.from_records(data, default_trait_name=default_trait_name)
