"""Sequence quality control and descriptive nucleotide diversity statistics.

This module intentionally does not calculate or interpret Tajima's D.  A raw
value without a defensible null model, recombination assumptions and sampling
assessment is liable to be over-interpreted in an interactive application.

DNA/RNA ``U`` is normalised to ``T`` by the canonical data model.  ``-`` is a
gap, ``N`` and ``?`` are missing, and all IUPAC ambiguity codes are ambiguous;
all are non-callable for the statistics below.  Unsupported sequence symbols
are rejected rather than silently counted as alleles.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum
from itertools import combinations
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from service.interpretation_models import AnalysisDataset, ensure_analysis_dataset


CANONICAL_BASES = frozenset("ACGT")
GAP_SYMBOLS = frozenset("-")
MISSING_SYMBOLS = frozenset("N?")
IUPAC_AMBIGUITY_SYMBOLS = frozenset("RYSWKMBDHV")
SUPPORTED_SYMBOLS = (
    CANONICAL_BASES | GAP_SYMBOLS | MISSING_SYMBOLS | IUPAC_AMBIGUITY_SYMBOLS
)
UNASSIGNED_GROUP = "(missing)"


class DiversityAnalysisError(ValueError):
    """Raised when diversity statistics cannot be computed from the input."""


class AnalysisCancelled(RuntimeError):
    """Raised when an optional cancellation callback requests cancellation."""


class MissingDataPolicy(str, Enum):
    """How non-callable states are excluded from diversity calculations."""

    COMPLETE_DELETION = "complete_deletion"
    PAIRWISE_DELETION = "pairwise_deletion"


@dataclass(frozen=True)
class SampleQuality:
    sample_name: str
    missing_count: int
    missing_rate: float
    gap_count: int
    gap_rate: float
    unknown_count: int
    unknown_rate: float
    ambiguity_count: int
    ambiguity_rate: float


@dataclass(frozen=True)
class SiteQuality:
    position: int
    callable_count: int
    missing_count: int
    missing_rate: float
    gap_count: int
    unknown_count: int
    ambiguity_count: int
    alleles: Tuple[Tuple[str, int], ...]
    effective: bool
    variable: bool
    parsimony_informative: bool


@dataclass(frozen=True)
class SequenceQualityReport:
    sample_count: int
    alignment_length: int
    missing_policy: MissingDataPolicy
    total_missing_count: int
    total_missing_rate: float
    effective_site_count: int
    variable_site_count: int
    parsimony_informative_site_count: int
    samples: Tuple[SampleQuality, ...]
    sites: Tuple[SiteQuality, ...]


@dataclass(frozen=True)
class DiversitySummary:
    label: str
    sample_count: int
    callable_site_count: int
    segregating_site_count: int
    comparable_pair_count: int
    haplotype_site_count: int
    haplotype_richness: int
    private_haplotype_count: Optional[int]
    private_haplotypes: Tuple[str, ...]
    haplotype_diversity: Optional[float]
    nucleotide_diversity: Optional[float]
    watterson_theta: Optional[float]
    warnings: Tuple[str, ...] = ()

    @property
    def hd(self) -> Optional[float]:
        return self.haplotype_diversity

    @property
    def pi(self) -> Optional[float]:
        return self.nucleotide_diversity

    @property
    def theta_w(self) -> Optional[float]:
        return self.watterson_theta


@dataclass(frozen=True)
class DiversityAnalysisResult:
    dataset: AnalysisDataset
    quality: SequenceQualityReport
    overall: DiversitySummary
    groups: Tuple[DiversitySummary, ...]
    group_trait: Optional[str]
    missing_policy: MissingDataPolicy
    warnings: Tuple[str, ...] = ()


CancelCheck = Optional[Callable[[], bool]]


def _check_cancelled(cancel_check: CancelCheck) -> None:
    if cancel_check is not None and cancel_check():
        raise AnalysisCancelled("Diversity analysis cancelled")


def _coerce_policy(policy: Any) -> MissingDataPolicy:
    if isinstance(policy, MissingDataPolicy):
        return policy
    try:
        return MissingDataPolicy(str(policy))
    except ValueError as exc:
        allowed = ", ".join(item.value for item in MissingDataPolicy)
        raise DiversityAnalysisError(f"Unknown missing-data policy; expected {allowed}") from exc


def _validate_symbols(dataset: AnalysisDataset) -> None:
    invalid: Dict[str, set[str]] = {}
    for sample in dataset.samples:
        bad = set(sample.sequence) - SUPPORTED_SYMBOLS
        if bad:
            invalid[sample.name] = bad
    if invalid:
        details = "; ".join(
            f"{name}: {','.join(sorted(symbols))}"
            for name, symbols in list(invalid.items())[:5]
        )
        raise DiversityAnalysisError(f"Unsupported sequence symbols ({details})")


def _is_callable(base: str) -> bool:
    return base in CANONICAL_BASES


def calculate_sequence_quality(
    data: Any,
    *,
    missing_policy: Any = MissingDataPolicy.COMPLETE_DELETION,
    cancel_check: CancelCheck = None,
) -> SequenceQualityReport:
    """Calculate per-sample/per-site missingness and aligned-site QC."""
    dataset = ensure_analysis_dataset(data)
    policy = _coerce_policy(missing_policy)
    _validate_symbols(dataset)
    sample_count = dataset.sample_count
    length = dataset.alignment_length

    sample_reports: List[SampleQuality] = []
    for index, sample in enumerate(dataset.samples):
        if index % 64 == 0:
            _check_cancelled(cancel_check)
        gap_count = sum(base in GAP_SYMBOLS for base in sample.sequence)
        ambiguity_count = sum(
            base in IUPAC_AMBIGUITY_SYMBOLS for base in sample.sequence
        )
        missing_symbol_count = sum(base in MISSING_SYMBOLS for base in sample.sequence)
        non_callable = gap_count + ambiguity_count + missing_symbol_count
        sample_reports.append(
            SampleQuality(
                sample_name=sample.name,
                missing_count=non_callable,
                missing_rate=non_callable / length,
                gap_count=gap_count,
                gap_rate=gap_count / length,
                unknown_count=missing_symbol_count,
                unknown_rate=missing_symbol_count / length,
                ambiguity_count=ambiguity_count,
                ambiguity_rate=ambiguity_count / length,
            )
        )

    site_reports: List[SiteQuality] = []
    for position in range(length):
        if position % 256 == 0:
            _check_cancelled(cancel_check)
        column = [sample.sequence[position] for sample in dataset.samples]
        allele_counts = Counter(base for base in column if _is_callable(base))
        callable_count = sum(allele_counts.values())
        gap_count = sum(base in GAP_SYMBOLS for base in column)
        ambiguity_count = sum(base in IUPAC_AMBIGUITY_SYMBOLS for base in column)
        missing_count = sample_count - callable_count
        effective = (
            callable_count == sample_count
            if policy is MissingDataPolicy.COMPLETE_DELETION
            else callable_count >= 2
        )
        variable = effective and len(allele_counts) >= 2
        parsimony = variable and sum(count >= 2 for count in allele_counts.values()) >= 2
        site_reports.append(
            SiteQuality(
                position=position + 1,
                callable_count=callable_count,
                missing_count=missing_count,
                missing_rate=missing_count / sample_count,
                gap_count=gap_count,
                unknown_count=sum(base in MISSING_SYMBOLS for base in column),
                ambiguity_count=ambiguity_count,
                alleles=tuple(sorted(allele_counts.items())),
                effective=effective,
                variable=variable,
                parsimony_informative=parsimony,
            )
        )

    total_cells = sample_count * length
    total_missing = sum(report.missing_count for report in sample_reports)
    return SequenceQualityReport(
        sample_count=sample_count,
        alignment_length=length,
        missing_policy=policy,
        total_missing_count=total_missing,
        total_missing_rate=total_missing / total_cells,
        effective_site_count=sum(site.effective for site in site_reports),
        variable_site_count=sum(site.variable for site in site_reports),
        parsimony_informative_site_count=sum(
            site.parsimony_informative for site in site_reports
        ),
        samples=tuple(sample_reports),
        sites=tuple(site_reports),
    )


def _harmonic_number(sample_count: int) -> float:
    return sum(1.0 / index for index in range(1, sample_count))


def _global_haplotype_signatures(dataset: AnalysisDataset) -> Tuple[Tuple[int, ...], Tuple[str, ...]]:
    positions = tuple(
        position
        for position in range(dataset.alignment_length)
        if all(_is_callable(sample.sequence[position]) for sample in dataset.samples)
    )
    signatures = tuple(
        "".join(sample.sequence[position] for position in positions)
        for sample in dataset.samples
    )
    return positions, signatures


def _haplotype_labels(signatures: Sequence[str]) -> Dict[str, str]:
    # Stable first-observation labels are suitable for tables and tests; they do
    # not imply evolutionary ordering or ancestry.
    labels: Dict[str, str] = {}
    for signature in signatures:
        if signature not in labels:
            labels[signature] = f"H{len(labels) + 1}"
    return labels


def _summary_for_indices(
    dataset: AnalysisDataset,
    indices: Sequence[int],
    label: str,
    policy: MissingDataPolicy,
    haplotype_positions: Sequence[int],
    signatures: Sequence[str],
    private_signatures: Sequence[str],
    haplotype_labels: Dict[str, str],
    cancel_check: CancelCheck,
) -> DiversitySummary:
    n = len(indices)
    warnings: List[str] = []
    if n < 2:
        warnings.append("At least two samples are required for Hd, pi and theta_w")

    selected_signatures = [signatures[index] for index in indices]
    hap_counts = Counter(selected_signatures)
    hap_richness = len(hap_counts)
    hd: Optional[float] = None
    if n >= 2:
        hd = n / (n - 1) * (
            1.0 - sum((count / n) ** 2 for count in hap_counts.values())
        )

    callable_sites = 0
    segregating_sites = 0
    theta_numerator = 0.0
    for position in range(dataset.alignment_length):
        if position % 256 == 0:
            _check_cancelled(cancel_check)
        alleles = Counter(
            dataset.samples[index].sequence[position]
            for index in indices
            if _is_callable(dataset.samples[index].sequence[position])
        )
        called_n = sum(alleles.values())
        effective = (
            called_n == n
            if policy is MissingDataPolicy.COMPLETE_DELETION
            else called_n >= 2
        )
        if not effective:
            continue
        callable_sites += 1
        if len(alleles) >= 2:
            segregating_sites += 1
            if policy is MissingDataPolicy.PAIRWISE_DELETION:
                theta_numerator += 1.0 / _harmonic_number(called_n)

    pi: Optional[float] = None
    comparable_pairs = 0
    if n >= 2:
        pair_distances: List[float] = []
        if policy is MissingDataPolicy.COMPLETE_DELETION:
            complete_positions = [
                position
                for position in range(dataset.alignment_length)
                if all(
                    _is_callable(dataset.samples[index].sequence[position])
                    for index in indices
                )
            ]
            for left, right in combinations(indices, 2):
                if complete_positions:
                    differences = sum(
                        dataset.samples[left].sequence[position]
                        != dataset.samples[right].sequence[position]
                        for position in complete_positions
                    )
                    pair_distances.append(differences / len(complete_positions))
        else:
            for left, right in combinations(indices, 2):
                comparable = [
                    position
                    for position in range(dataset.alignment_length)
                    if _is_callable(dataset.samples[left].sequence[position])
                    and _is_callable(dataset.samples[right].sequence[position])
                ]
                if comparable:
                    differences = sum(
                        dataset.samples[left].sequence[position]
                        != dataset.samples[right].sequence[position]
                        for position in comparable
                    )
                    pair_distances.append(differences / len(comparable))
        comparable_pairs = len(pair_distances)
        if pair_distances:
            pi = sum(pair_distances) / len(pair_distances)
        else:
            warnings.append("No sample pair has callable sites for nucleotide diversity")

    theta_w: Optional[float] = None
    if n >= 2 and callable_sites:
        if policy is MissingDataPolicy.COMPLETE_DELETION:
            theta_w = segregating_sites / (_harmonic_number(n) * callable_sites)
        else:
            theta_w = theta_numerator / callable_sites
    elif n >= 2:
        warnings.append("No callable sites are available for Watterson's theta")

    if not haplotype_positions:
        warnings.append(
            "No globally complete sites; haplotype metrics cannot distinguish samples"
        )
    elif policy is MissingDataPolicy.PAIRWISE_DELETION:
        warnings.append(
            "Haplotype metrics use globally complete sites so missing patterns do not create haplotypes"
        )

    private_labels = tuple(
        sorted(haplotype_labels[signature] for signature in private_signatures)
    )
    return DiversitySummary(
        label=label,
        sample_count=n,
        callable_site_count=callable_sites,
        segregating_site_count=segregating_sites,
        comparable_pair_count=comparable_pairs,
        haplotype_site_count=len(haplotype_positions),
        haplotype_richness=hap_richness,
        private_haplotype_count=len(private_labels),
        private_haplotypes=private_labels,
        haplotype_diversity=hd,
        nucleotide_diversity=pi,
        watterson_theta=theta_w,
        warnings=tuple(warnings),
    )


def analyze_diversity(
    data: Any,
    *,
    group_trait: Optional[str] = "trait",
    missing_policy: Any = MissingDataPolicy.COMPLETE_DELETION,
    cancel_check: CancelCheck = None,
) -> DiversityAnalysisResult:
    """Calculate QC plus overall and optional discrete-trait diversity.

    ``data`` may be an :class:`AnalysisDataset`, TaxonData sequence, mapping
    records, or objects exposing ``name``, ``sequence`` and ``traits``.  Empty
    trait values are retained as the explicit ``(missing)`` group.
    """
    dataset = ensure_analysis_dataset(data, default_trait_name=group_trait or "trait")
    policy = _coerce_policy(missing_policy)
    _validate_symbols(dataset)
    _check_cancelled(cancel_check)
    quality = calculate_sequence_quality(
        dataset,
        missing_policy=policy,
        cancel_check=cancel_check,
    )
    hap_positions, signatures = _global_haplotype_signatures(dataset)
    labels = _haplotype_labels(signatures)

    overall = _summary_for_indices(
        dataset,
        tuple(range(dataset.sample_count)),
        "Overall",
        policy,
        hap_positions,
        signatures,
        (),
        labels,
        cancel_check,
    )
    # Private haplotypes only have meaning relative to a grouping; leave the
    # overall value undefined rather than calling every haplotype "private".
    overall = DiversitySummary(
        **{
            **overall.__dict__,
            "private_haplotype_count": None,
            "private_haplotypes": (),
        }
    )

    grouped_results: List[DiversitySummary] = []
    warnings: List[str] = []
    if group_trait:
        grouped_indices: Dict[str, List[int]] = defaultdict(list)
        for index, sample in enumerate(dataset.samples):
            value = sample.discrete_trait(group_trait).strip() or UNASSIGNED_GROUP
            grouped_indices[value].append(index)
        if len(grouped_indices) <= 1:
            warnings.append(
                f"Discrete trait '{group_trait}' contains fewer than two groups"
            )

        signature_groups: Dict[str, set[str]] = defaultdict(set)
        for group_name, indices in grouped_indices.items():
            for index in indices:
                signature_groups[signatures[index]].add(group_name)

        for group_name in sorted(grouped_indices):
            indices = grouped_indices[group_name]
            private = sorted(
                {
                    signatures[index]
                    for index in indices
                    if signature_groups[signatures[index]] == {group_name}
                }
            )
            grouped_results.append(
                _summary_for_indices(
                    dataset,
                    indices,
                    group_name,
                    policy,
                    hap_positions,
                    signatures,
                    private,
                    labels,
                    cancel_check,
                )
            )

    if policy is MissingDataPolicy.PAIRWISE_DELETION:
        warnings.append(
            "Pairwise pi values can use different callable sites for different sample pairs"
        )

    return DiversityAnalysisResult(
        dataset=dataset,
        quality=quality,
        overall=overall,
        groups=tuple(grouped_results),
        group_trait=group_trait,
        missing_policy=policy,
        warnings=tuple(warnings),
    )
