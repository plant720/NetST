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
import math
import random
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
class MismatchBin:
    differences: int
    pair_count: int
    frequency: float


@dataclass(frozen=True)
class MismatchDistribution:
    callable_site_count: int
    pair_count: int
    mean_differences: Optional[float]
    variance_differences: Optional[float]
    mode_differences: Optional[int]
    bins: Tuple[MismatchBin, ...]


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
    mean_pairwise_differences: Optional[float]
    tajima_d: Optional[float]
    tajima_callable_site_count: int
    mismatch_distribution: MismatchDistribution
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

    @property
    def k(self) -> Optional[float]:
        return self.mean_pairwise_differences


@dataclass(frozen=True)
class PairwiseFst:
    group_a: str
    group_b: str
    sample_count_a: int
    sample_count_b: int
    pi_within_a: Optional[float]
    pi_within_b: Optional[float]
    pi_between: Optional[float]
    fst: Optional[float]


@dataclass(frozen=True)
class FstAnalysis:
    estimator: str
    global_fst: Optional[float]
    p_value: Optional[float]
    permutation_count: int
    pairs: Tuple[PairwiseFst, ...]


@dataclass(frozen=True)
class AmovaAnalysis:
    distance: str
    sample_count: int
    group_count: int
    callable_site_count: int
    df_among: int
    df_within: int
    sum_squares_among: Optional[float]
    sum_squares_within: Optional[float]
    mean_squares_among: Optional[float]
    mean_squares_within: Optional[float]
    variance_among: Optional[float]
    variance_within: Optional[float]
    percent_among: Optional[float]
    percent_within: Optional[float]
    phi_st: Optional[float]
    p_value: Optional[float]
    permutation_count: int


@dataclass(frozen=True)
class DiversityAnalysisResult:
    dataset: AnalysisDataset
    quality: SequenceQualityReport
    overall: DiversitySummary
    groups: Tuple[DiversitySummary, ...]
    fst: FstAnalysis
    amova: AmovaAnalysis
    group_trait: Optional[str]
    missing_policy: MissingDataPolicy
    permutation_count: int
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


def _complete_positions_for_indices(
    dataset: AnalysisDataset,
    indices: Sequence[int],
) -> Tuple[int, ...]:
    return tuple(
        position
        for position in range(dataset.alignment_length)
        if all(
            _is_callable(dataset.samples[index].sequence[position])
            for index in indices
        )
    )


def _difference_count(
    dataset: AnalysisDataset,
    left: int,
    right: int,
    positions: Sequence[int],
) -> int:
    return sum(
        dataset.samples[left].sequence[position]
        != dataset.samples[right].sequence[position]
        for position in positions
    )


def _mismatch_distribution(
    difference_counts: Sequence[int],
    callable_site_count: int,
) -> MismatchDistribution:
    counts = Counter(int(value) for value in difference_counts)
    pair_count = sum(counts.values())
    if not pair_count:
        return MismatchDistribution(
            callable_site_count=callable_site_count,
            pair_count=0,
            mean_differences=None,
            variance_differences=None,
            mode_differences=None,
            bins=(),
        )
    mean = sum(value * count for value, count in counts.items()) / pair_count
    variance = sum(
        count * (value - mean) ** 2 for value, count in counts.items()
    ) / pair_count
    mode = min(
        value for value, count in counts.items() if count == max(counts.values())
    )
    bins = tuple(
        MismatchBin(
            differences=value,
            pair_count=counts.get(value, 0),
            frequency=counts.get(value, 0) / pair_count,
        )
        for value in sorted(counts)
    )
    return MismatchDistribution(
        callable_site_count=callable_site_count,
        pair_count=pair_count,
        mean_differences=mean,
        variance_differences=variance,
        mode_differences=mode,
        bins=bins,
    )


def _tajima_d(
    sample_count: int,
    segregating_sites: int,
    mean_pairwise_differences: Optional[float],
) -> Optional[float]:
    """Return the classic Tajima (1989) D for a fixed-size sequence sample."""
    if sample_count < 2 or segregating_sites <= 0 \
            or mean_pairwise_differences is None:
        return None
    a1 = _harmonic_number(sample_count)
    a2 = sum(1.0 / (index * index) for index in range(1, sample_count))
    if a1 <= 0:
        return None
    b1 = (sample_count + 1.0) / (3.0 * (sample_count - 1.0))
    b2 = 2.0 * (sample_count * sample_count + sample_count + 3.0) / (
        9.0 * sample_count * (sample_count - 1.0)
    )
    c1 = b1 - 1.0 / a1
    c2 = b2 - (sample_count + 2.0) / (a1 * sample_count) + a2 / (a1 * a1)
    e1 = c1 / a1
    e2 = c2 / (a1 * a1 + a2)
    variance = e1 * segregating_sites + e2 * segregating_sites * (
        segregating_sites - 1
    )
    if variance <= 0:
        return None
    return (mean_pairwise_differences - segregating_sites / a1) / math.sqrt(variance)


def _mean(values: Sequence[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


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

    # Tajima's D and a classical mismatch distribution require every pair to
    # refer to the same sequence length.  They therefore use the positions that
    # are callable in every member of this summary, even when pi itself uses
    # pairwise deletion.
    complete_positions = _complete_positions_for_indices(dataset, indices)
    complete_difference_counts = [
        _difference_count(dataset, left, right, complete_positions)
        for left, right in combinations(indices, 2)
    ] if complete_positions else []
    mismatch = _mismatch_distribution(
        complete_difference_counts, len(complete_positions))
    tajima_segregating_sites = sum(
        len({dataset.samples[index].sequence[position] for index in indices}) >= 2
        for position in complete_positions
    )
    tajima_d = _tajima_d(
        n, tajima_segregating_sites, mismatch.mean_differences)

    pi: Optional[float] = None
    comparable_pairs = 0
    if n >= 2:
        pair_distances: List[float] = []
        if policy is MissingDataPolicy.COMPLETE_DELETION:
            for left, right in combinations(indices, 2):
                if complete_positions:
                    differences = _difference_count(
                        dataset, left, right, complete_positions)
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

    if n >= 2 and not complete_positions:
        warnings.append(
            "No complete sites are available for Tajima's D or mismatch distribution"
        )
    elif n >= 2 and tajima_segregating_sites == 0:
        warnings.append("Tajima's D is undefined when no complete site is segregating")
    elif n >= 2 and tajima_d is None:
        warnings.append("Tajima's D is undefined for this sample size and variation")
    if policy is MissingDataPolicy.PAIRWISE_DELETION and complete_positions:
        warnings.append(
            "Tajima's D and mismatch distribution use complete sites so every pair has the same sequence length"
        )

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
        mean_pairwise_differences=mismatch.mean_differences,
        tajima_d=tajima_d,
        tajima_callable_site_count=len(complete_positions),
        mismatch_distribution=mismatch,
        warnings=tuple(warnings),
    )


def _pairwise_distance_matrix(
    dataset: AnalysisDataset,
    policy: MissingDataPolicy,
    complete_indices: Optional[Sequence[int]] = None,
) -> Tuple[List[List[Optional[float]]], Tuple[int, ...]]:
    n = dataset.sample_count
    complete_positions = _complete_positions_for_indices(
        dataset, complete_indices if complete_indices is not None else range(n))
    matrix: List[List[Optional[float]]] = [
        [None for _ in range(n)] for _ in range(n)
    ]
    for index in range(n):
        matrix[index][index] = 0.0
    for left, right in combinations(range(n), 2):
        positions: Sequence[int]
        if policy is MissingDataPolicy.COMPLETE_DELETION:
            positions = complete_positions
        else:
            positions = tuple(
                position
                for position in range(dataset.alignment_length)
                if _is_callable(dataset.samples[left].sequence[position])
                and _is_callable(dataset.samples[right].sequence[position])
            )
        if not positions:
            continue
        distance = _difference_count(dataset, left, right, positions) / len(positions)
        matrix[left][right] = distance
        matrix[right][left] = distance
    return matrix, complete_positions


def _within_pi(
    matrix: Sequence[Sequence[Optional[float]]],
    indices: Sequence[int],
) -> Optional[float]:
    values = [
        matrix[left][right]
        for left, right in combinations(indices, 2)
        if matrix[left][right] is not None
    ]
    return _mean([float(value) for value in values])


def _between_pi(
    matrix: Sequence[Sequence[Optional[float]]],
    left_indices: Sequence[int],
    right_indices: Sequence[int],
) -> Optional[float]:
    values = [
        matrix[left][right]
        for left in left_indices
        for right in right_indices
        if matrix[left][right] is not None
    ]
    return _mean([float(value) for value in values])


def _hudson_pair_fst(
    within_a: Optional[float],
    within_b: Optional[float],
    between: Optional[float],
) -> Optional[float]:
    if within_a is None or within_b is None or between is None or between <= 0:
        return None
    return 1.0 - ((within_a + within_b) / 2.0) / between


def _global_hudson_fst(
    matrix: Sequence[Sequence[Optional[float]]],
    grouped_indices: Dict[str, List[int]],
) -> Optional[float]:
    if len(grouped_indices) < 2 or any(len(indices) < 2 for indices in grouped_indices.values()):
        return None
    group_names = sorted(grouped_indices)
    within_values = [
        _within_pi(matrix, grouped_indices[name]) for name in group_names
    ]
    between_values = [
        _between_pi(matrix, grouped_indices[left], grouped_indices[right])
        for left, right in combinations(group_names, 2)
    ]
    if any(value is None for value in within_values + between_values):
        return None
    within = _mean([float(value) for value in within_values])
    between = _mean([float(value) for value in between_values])
    if within is None or between is None or between <= 0:
        return None
    return 1.0 - within / between


def _amova_components(
    matrix: Sequence[Sequence[Optional[float]]],
    grouped_indices: Dict[str, List[int]],
) -> Optional[Dict[str, float]]:
    """One-level AMOVA using p-distance as the molecular squared distance."""
    groups = [indices for indices in grouped_indices.values() if indices]
    sample_count = sum(len(indices) for indices in groups)
    group_count = len(groups)
    if group_count < 2 or sample_count <= group_count:
        return None
    all_indices = [index for indices in groups for index in indices]
    total_values = [
        matrix[left][right]
        for left, right in combinations(all_indices, 2)
    ]
    if not total_values or any(value is None for value in total_values):
        return None
    total_ss = sum(float(value) for value in total_values) / sample_count
    within_ss = 0.0
    for indices in groups:
        values = [matrix[left][right] for left, right in combinations(indices, 2)]
        if any(value is None for value in values):
            return None
        within_ss += sum(float(value) for value in values) / len(indices)
    among_ss = total_ss - within_ss
    df_among = group_count - 1
    df_within = sample_count - group_count
    ms_among = among_ss / df_among
    ms_within = within_ss / df_within
    n_c = (
        sample_count
        - sum(len(indices) ** 2 for indices in groups) / sample_count
    ) / df_among
    if n_c <= 0:
        return None
    variance_within = ms_within
    variance_among = (ms_among - ms_within) / n_c
    total_variance = variance_among + variance_within
    phi_st = variance_among / total_variance if total_variance != 0 else None
    return {
        "df_among": float(df_among),
        "df_within": float(df_within),
        "ss_among": among_ss,
        "ss_within": within_ss,
        "ms_among": ms_among,
        "ms_within": ms_within,
        "variance_among": variance_among,
        "variance_within": variance_within,
        "percent_among": variance_among / total_variance * 100.0
        if total_variance != 0 else math.nan,
        "percent_within": variance_within / total_variance * 100.0
        if total_variance != 0 else math.nan,
        "phi_st": phi_st if phi_st is not None else math.nan,
    }


def _permuted_groups(
    grouped_indices: Dict[str, List[int]],
    rng: random.Random,
) -> Dict[str, List[int]]:
    names = sorted(grouped_indices)
    shuffled = [index for name in names for index in grouped_indices[name]]
    rng.shuffle(shuffled)
    result: Dict[str, List[int]] = {}
    cursor = 0
    for name in names:
        size = len(grouped_indices[name])
        result[name] = shuffled[cursor:cursor + size]
        cursor += size
    return result


def _analyze_population_structure(
    dataset: AnalysisDataset,
    grouped_indices: Dict[str, List[int]],
    policy: MissingDataPolicy,
    permutation_count: int,
    permutation_seed: int,
    cancel_check: CancelCheck,
) -> Tuple[FstAnalysis, AmovaAnalysis, Tuple[str, ...]]:
    warnings: List[str] = []
    fst_matrix, global_complete_positions = _pairwise_distance_matrix(dataset, policy)
    complete_matrix, _ = _pairwise_distance_matrix(
        dataset, MissingDataPolicy.COMPLETE_DELETION)
    group_names = sorted(grouped_indices)
    fst_pairs: List[PairwiseFst] = []
    for left_name, right_name in combinations(group_names, 2):
        left = grouped_indices[left_name]
        right = grouped_indices[right_name]
        pair_matrix = fst_matrix
        if policy is MissingDataPolicy.COMPLETE_DELETION:
            pair_matrix, _ = _pairwise_distance_matrix(
                dataset, policy, (*left, *right))
        within_left = _within_pi(pair_matrix, left)
        within_right = _within_pi(pair_matrix, right)
        between = _between_pi(pair_matrix, left, right)
        fst_pairs.append(PairwiseFst(
            group_a=left_name,
            group_b=right_name,
            sample_count_a=len(left),
            sample_count_b=len(right),
            pi_within_a=within_left,
            pi_within_b=within_right,
            pi_between=between,
            fst=_hudson_pair_fst(within_left, within_right, between),
        ))

    observed_fst = _global_hudson_fst(fst_matrix, grouped_indices)
    observed_amova = _amova_components(complete_matrix, grouped_indices)
    if len(group_names) < 2:
        warnings.append("FST and AMOVA require at least two groups")
    if any(len(indices) < 2 for indices in grouped_indices.values()):
        warnings.append(
            "Hudson FST is undefined for comparisons containing a group with fewer than two samples"
        )
    if not global_complete_positions:
        warnings.append("AMOVA requires at least one site callable in every sample")
    elif policy is MissingDataPolicy.PAIRWISE_DELETION:
        warnings.append(
            "AMOVA uses sites callable in every sample to keep one complete molecular-distance matrix"
        )

    fst_extreme = 0
    amova_extreme = 0
    fst_permutations = 0
    amova_permutations = 0
    if permutation_count > 0 and (observed_fst is not None or observed_amova is not None):
        rng = random.Random(permutation_seed)
        observed_phi = (
            observed_amova.get("phi_st") if observed_amova is not None else None
        )
        for iteration in range(permutation_count):
            if iteration % 16 == 0:
                _check_cancelled(cancel_check)
            permuted = _permuted_groups(grouped_indices, rng)
            if observed_fst is not None:
                value = _global_hudson_fst(fst_matrix, permuted)
                if value is not None:
                    fst_permutations += 1
                    if value >= observed_fst:
                        fst_extreme += 1
            if observed_phi is not None and math.isfinite(observed_phi):
                components = _amova_components(complete_matrix, permuted)
                value = components.get("phi_st") if components is not None else None
                if value is not None and math.isfinite(value):
                    amova_permutations += 1
                    if value >= observed_phi:
                        amova_extreme += 1

    fst_p = (
        (fst_extreme + 1) / (fst_permutations + 1)
        if observed_fst is not None and fst_permutations else None
    )
    fst_result = FstAnalysis(
        estimator="Hudson sequence FST (equal population weighting)",
        global_fst=observed_fst,
        p_value=fst_p,
        permutation_count=fst_permutations,
        pairs=tuple(fst_pairs),
    )

    components = observed_amova or {}
    phi = components.get("phi_st")
    phi_value = float(phi) if phi is not None and math.isfinite(phi) else None
    amova_p = (
        (amova_extreme + 1) / (amova_permutations + 1)
        if phi_value is not None and amova_permutations else None
    )
    amova_result = AmovaAnalysis(
        distance="uncorrected nucleotide p-distance",
        sample_count=dataset.sample_count,
        group_count=len(grouped_indices),
        callable_site_count=len(global_complete_positions),
        df_among=int(components.get("df_among", max(0, len(grouped_indices) - 1))),
        df_within=int(components.get(
            "df_within", max(0, dataset.sample_count - len(grouped_indices)))),
        sum_squares_among=components.get("ss_among"),
        sum_squares_within=components.get("ss_within"),
        mean_squares_among=components.get("ms_among"),
        mean_squares_within=components.get("ms_within"),
        variance_among=components.get("variance_among"),
        variance_within=components.get("variance_within"),
        percent_among=(components.get("percent_among")
                       if components and math.isfinite(components.get("percent_among", math.nan))
                       else None),
        percent_within=(components.get("percent_within")
                        if components and math.isfinite(components.get("percent_within", math.nan))
                        else None),
        phi_st=phi_value,
        p_value=amova_p,
        permutation_count=amova_permutations,
    )
    return fst_result, amova_result, tuple(warnings)


def analyze_diversity(
    data: Any,
    *,
    group_trait: Optional[str] = "trait",
    missing_policy: Any = MissingDataPolicy.COMPLETE_DELETION,
    permutation_count: int = 999,
    permutation_seed: int = 1729,
    cancel_check: CancelCheck = None,
) -> DiversityAnalysisResult:
    """Calculate QC plus overall and optional discrete-trait diversity.

    ``data`` may be an :class:`AnalysisDataset`, TaxonData sequence, mapping
    records, or objects exposing ``name``, ``sequence`` and ``traits``.  Empty
    trait values are retained as the explicit ``(missing)`` group.
    """
    dataset = ensure_analysis_dataset(data, default_trait_name=group_trait or "trait")
    policy = _coerce_policy(missing_policy)
    try:
        permutation_count = int(permutation_count)
    except (TypeError, ValueError) as exc:
        raise DiversityAnalysisError("Permutation count must be an integer") from exc
    if permutation_count < 0 or permutation_count > 100000:
        raise DiversityAnalysisError("Permutation count must be between 0 and 100000")
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
    grouped_indices: Dict[str, List[int]] = defaultdict(list)
    warnings: List[str] = []
    if group_trait:
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

    fst, amova, structure_warnings = _analyze_population_structure(
        dataset,
        dict(grouped_indices),
        policy,
        permutation_count,
        int(permutation_seed),
        cancel_check,
    )
    warnings.extend(structure_warnings)

    return DiversityAnalysisResult(
        dataset=dataset,
        quality=quality,
        overall=overall,
        groups=tuple(grouped_results),
        fst=fst,
        amova=amova,
        group_trait=group_trait,
        missing_policy=policy,
        permutation_count=permutation_count,
        warnings=tuple(warnings),
    )
