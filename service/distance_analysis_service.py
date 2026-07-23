"""Missing-aware genetic distances and classical PCoA.

The old auxiliary analysis treated a distance matrix as ordinary features and
ran PCA on it.  This module instead implements classical multidimensional
scaling (PCoA) from the double-centred squared-distance matrix.  It deliberately
has no GUI or third-party dependency so it can run in NetST's base environment.

Only unambiguous DNA/RNA bases are compared.  Gaps, ``N``, ``?`` and all IUPAC
ambiguity codes are pairwise deleted.  ``U`` is normalised to ``T``.  Distances
that do not meet the configured effective-site threshold remain ``NaN``; they
are never silently replaced with zero or an arbitrary saturation constant.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Sequence, Tuple


class DistanceAnalysisError(ValueError):
    """Raised when distance analysis input or parameters are invalid."""


class DistanceAnalysisCancelled(RuntimeError):
    """Raised when a caller-provided cancellation callback requests a stop."""


@dataclass(frozen=True)
class PCoAResult:
    """Coordinates and eigenspectrum diagnostics from classical PCoA.

    ``explained_variance_ratio`` is calculated over positive eigenvalues only.
    ``negative_eigenvalue_ratio`` is the absolute sum of negative eigenvalues
    divided by the absolute sum of the complete eigenspectrum.  A substantial
    value warns that the supplied distances are appreciably non-Euclidean.
    """

    coordinates: Tuple[Tuple[float, ...], ...]
    eigenvalues: Tuple[float, ...]
    explained_variance_ratio: Tuple[float, ...]
    negative_eigenvalue_ratio: float
    axis_count: int
    warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class DistanceAnalysisResult:
    """Structured result shared by UI, export and future compatibility layers."""

    labels: Tuple[str, ...]
    distance_matrix: Tuple[Tuple[float, ...], ...]
    comparable_sites: Tuple[Tuple[int, ...], ...]
    alignment_length: int
    minimum_comparable_sites: int
    minimum_coverage: float
    pcoa: PCoAResult
    warnings: Tuple[str, ...] = ()
    method: str = "pairwise-deletion p-distance"
    parameters: dict = field(default_factory=dict)

    def to_report_dict(self) -> dict:
        """Return the generic report protocol consumed by Interpretation UI."""
        sample_count = len(self.labels)
        pair_count = sample_count * (sample_count - 1) // 2
        unavailable = sum(
            1
            for row in range(sample_count)
            for column in range(row + 1, sample_count)
            if not math.isfinite(self.distance_matrix[row][column])
        )
        tables = [
            {
                "title": "p-distance",
                "columns": ["Sample"] + list(self.labels),
                "rows": [
                    [label] + list(self.distance_matrix[index])
                    for index, label in enumerate(self.labels)
                ],
            },
            {
                "title": "Comparable sites",
                "columns": ["Sample"] + list(self.labels),
                "rows": [
                    [label] + list(self.comparable_sites[index])
                    for index, label in enumerate(self.labels)
                ],
            },
        ]
        if self.pcoa.axis_count:
            tables.append({
                "title": "PCoA coordinates",
                "columns": ["Sample"] + [
                    f"Axis {index + 1}" for index in range(self.pcoa.axis_count)
                ],
                "rows": [
                    [label] + list(self.pcoa.coordinates[index])
                    for index, label in enumerate(self.labels)
                ],
            })

        summary = [
            ["Sequences", sample_count],
            ["Alignment length", self.alignment_length],
            ["Pairwise comparisons", pair_count],
            ["Unavailable low-coverage pairs", unavailable],
            ["Minimum comparable sites", self.minimum_comparable_sites],
            ["Minimum comparable coverage", self.minimum_coverage],
            ["PCoA axes returned", self.pcoa.axis_count],
            ["Negative eigenvalue ratio", self.pcoa.negative_eigenvalue_ratio],
        ]
        summary.extend(
            [f"PCoA axis {index + 1} positive-eigenvalue proportion", ratio]
            for index, ratio in enumerate(
                self.pcoa.explained_variance_ratio[:self.pcoa.axis_count]
            )
        )

        return {
            "title": "Genetic distance and PCoA",
            "description": (
                "Missing-aware pairwise p-distance followed by classical "
                "principal coordinates analysis (PCoA)."
            ),
            "summary_columns": ["Metric", "Value"],
            "summary": summary,
            "warnings": list(self.warnings) + list(self.pcoa.warnings),
            "notes": [
                "Only A, C, G and T/U are treated as called bases; ambiguity "
                "codes and gaps are pairwise deleted.",
                "PCoA axis percentages are based on positive eigenvalues. "
                "Negative eigenvalues diagnose non-Euclidean distance structure.",
                "Ordination proximity is exploratory and does not by itself "
                "establish populations, ancestry or transmission links.",
            ],
            "tables": tables,
            "provenance": {
                "method": self.method,
                "parameters": dict(self.parameters),
            },
        }


_CALLED_BASES = frozenset("ACGTU")


def compute_p_distance_matrix(
    records: Sequence[Any],
    labels: Optional[Sequence[str]] = None,
    *,
    minimum_comparable_sites: int = 1,
    minimum_coverage: float = 0.0,
    cancel_requested: Optional[Callable[[], bool]] = None,
) -> Tuple[Tuple[str, ...], Tuple[Tuple[float, ...], ...],
           Tuple[Tuple[int, ...], ...], int, Tuple[str, ...]]:
    """Calculate pairwise-deletion p-distances and effective site counts.

    Args:
        records: Objects with a ``sequence`` attribute (and preferably ``name``),
            or plain sequence strings when ``labels`` is supplied.
        labels: Optional explicit labels in record order.
        minimum_comparable_sites: A pair below this count is returned as NaN.
        minimum_coverage: Additional fraction-of-alignment threshold in [0, 1].
        cancel_requested: Optional callback returning true to cancel promptly.

    Returns:
        ``(labels, distances, comparable_sites, alignment_length, warnings)``.
    """
    names, sequences = _coerce_records(records, labels)
    if minimum_comparable_sites < 1:
        raise DistanceAnalysisError("minimum_comparable_sites must be at least 1")
    if not 0.0 <= minimum_coverage <= 1.0:
        raise DistanceAnalysisError("minimum_coverage must be between 0 and 1")

    alignment_length = len(sequences[0])
    required_sites = max(
        minimum_comparable_sites,
        int(math.ceil(alignment_length * minimum_coverage)),
    )
    size = len(sequences)
    distances = [[math.nan] * size for _ in range(size)]
    effective = [[0] * size for _ in range(size)]
    normalised = [sequence.upper().replace("U", "T") for sequence in sequences]

    unrecognised = sorted({
        symbol
        for sequence in sequences
        for symbol in sequence.upper()
        if symbol not in _CALLED_BASES and symbol not in "-?N.RYSWKMBDHVX*"
    })
    low_coverage_pairs: List[Tuple[str, str, int]] = []

    for left in range(size):
        _check_cancelled(cancel_requested)
        called_count = sum(base in "ACGT" for base in normalised[left])
        effective[left][left] = called_count
        distances[left][left] = 0.0
        for right in range(left + 1, size):
            if right % 32 == 0:
                _check_cancelled(cancel_requested)
            valid = 0
            differences = 0
            for first, second in zip(normalised[left], normalised[right]):
                if first not in "ACGT" or second not in "ACGT":
                    continue
                valid += 1
                if first != second:
                    differences += 1
            effective[left][right] = effective[right][left] = valid
            if valid < required_sites:
                low_coverage_pairs.append((names[left], names[right], valid))
                continue
            distance = differences / valid
            distances[left][right] = distances[right][left] = distance

    warnings: List[str] = []
    if low_coverage_pairs:
        examples = ", ".join(
            f"{left}/{right} ({count})"
            for left, right, count in low_coverage_pairs[:5]
        )
        suffix = "" if len(low_coverage_pairs) <= 5 else ", ..."
        warnings.append(
            f"{len(low_coverage_pairs)} sequence pair(s) had fewer than "
            f"{required_sites} comparable sites and were reported as NaN: "
            f"{examples}{suffix}"
        )
    if unrecognised:
        warnings.append(
            "Unrecognised sequence symbols were treated as missing: "
            + ", ".join(unrecognised)
        )

    return (
        names,
        tuple(tuple(row) for row in distances),
        tuple(tuple(row) for row in effective),
        alignment_length,
        tuple(warnings),
    )


def classical_pcoa(
    distance_matrix: Sequence[Sequence[float]],
    *,
    max_axes: int = 2,
    max_samples: int = 200,
    cancel_requested: Optional[Callable[[], bool]] = None,
) -> PCoAResult:
    """Perform classical PCoA using a dependency-free Jacobi eigensolver."""
    matrix = _validate_distance_matrix(distance_matrix)
    size = len(matrix)
    if max_axes < 1:
        raise DistanceAnalysisError("max_axes must be at least 1")
    if max_samples < 2:
        raise DistanceAnalysisError("max_samples must be at least 2")
    if size == 1:
        return PCoAResult(
            coordinates=((),),
            eigenvalues=(0.0,),
            explained_variance_ratio=(),
            negative_eigenvalue_ratio=0.0,
            axis_count=0,
            warnings=("PCoA requires at least two sequences; no axes were returned.",),
        )
    if size > max_samples:
        return PCoAResult(
            coordinates=tuple(() for _ in range(size)),
            eigenvalues=(),
            explained_variance_ratio=(),
            negative_eigenvalue_ratio=0.0,
            axis_count=0,
            warnings=(
                f"PCoA was skipped for {size} sequences because the dependency-free "
                f"solver is limited to {max_samples}. Reduce the set or raise "
                "max_samples after considering the cubic computational cost.",
            ),
        )
    if any(not math.isfinite(value) for row in matrix for value in row):
        return PCoAResult(
            coordinates=tuple(() for _ in range(size)),
            eigenvalues=(),
            explained_variance_ratio=(),
            negative_eigenvalue_ratio=0.0,
            axis_count=0,
            warnings=(
                "PCoA was not calculated because one or more pairwise distances "
                "are unavailable (NaN). Review comparable-site coverage or use a "
                "complete subset; missing distances were not imputed.",
            ),
        )

    squared = [[value * value for value in row] for row in matrix]
    row_means = [sum(row) / size for row in squared]
    grand_mean = sum(row_means) / size
    centred = [
        [
            -0.5 * (
                squared[row][column]
                - row_means[row]
                - row_means[column]
                + grand_mean
            )
            for column in range(size)
        ]
        for row in range(size)
    ]

    eigenvalues, eigenvectors, converged = _jacobi_eigen(
        centred, cancel_requested=cancel_requested
    )
    order = sorted(range(size), key=lambda index: eigenvalues[index], reverse=True)
    eigenvalues = [eigenvalues[index] for index in order]
    eigenvectors = [
        [eigenvectors[row][index] for index in order]
        for row in range(size)
    ]

    scale = max(1.0, max(abs(value) for value in eigenvalues))
    tolerance = scale * 1e-10
    positive_indices = [
        index for index, value in enumerate(eigenvalues) if value > tolerance
    ]
    selected = positive_indices[:max_axes]
    positive_sum = sum(eigenvalues[index] for index in positive_indices)
    # Retain the complete positive spectrum rather than only the axes selected
    # for coordinates.  This lets callers judge how much information was left
    # outside a two-dimensional display.
    ratios = tuple(
        eigenvalues[index] / positive_sum for index in positive_indices
    ) if positive_sum else ()
    coordinates = tuple(
        tuple(
            eigenvectors[row][index] * math.sqrt(eigenvalues[index])
            for index in selected
        )
        for row in range(size)
    )

    negative_sum = sum(-value for value in eigenvalues if value < -tolerance)
    absolute_sum = sum(abs(value) for value in eigenvalues if abs(value) > tolerance)
    negative_ratio = negative_sum / absolute_sum if absolute_sum else 0.0
    warnings: List[str] = []
    if not converged:
        warnings.append(
            "The PCoA eigensolver reached its iteration limit; coordinates may be "
            "numerically approximate."
        )
    if negative_ratio > 1e-8:
        warnings.append(
            f"Negative eigenvalues account for {negative_ratio:.2%} of the absolute "
            "eigenspectrum, indicating non-Euclidean distance structure."
        )
    if not selected:
        warnings.append(
            "All samples have zero or numerically negligible separation; no positive "
            "PCoA axis was available."
        )

    return PCoAResult(
        coordinates=coordinates,
        eigenvalues=tuple(eigenvalues),
        explained_variance_ratio=ratios,
        negative_eigenvalue_ratio=negative_ratio,
        axis_count=len(selected),
        warnings=tuple(warnings),
    )


def analyze_distances(
    records: Sequence[Any],
    labels: Optional[Sequence[str]] = None,
    *,
    minimum_comparable_sites: int = 1,
    minimum_coverage: float = 0.0,
    max_axes: int = 2,
    pcoa_max_samples: int = 200,
    cancel_requested: Optional[Callable[[], bool]] = None,
) -> DistanceAnalysisResult:
    """Run missing-aware p-distance and PCoA as one pure computation."""
    names, distances, comparable, alignment_length, warnings = (
        compute_p_distance_matrix(
            records,
            labels,
            minimum_comparable_sites=minimum_comparable_sites,
            minimum_coverage=minimum_coverage,
            cancel_requested=cancel_requested,
        )
    )
    _check_cancelled(cancel_requested)
    pcoa = classical_pcoa(
        distances,
        max_axes=max_axes,
        max_samples=pcoa_max_samples,
        cancel_requested=cancel_requested,
    )
    return DistanceAnalysisResult(
        labels=names,
        distance_matrix=distances,
        comparable_sites=comparable,
        alignment_length=alignment_length,
        minimum_comparable_sites=minimum_comparable_sites,
        minimum_coverage=minimum_coverage,
        pcoa=pcoa,
        warnings=warnings,
        parameters={
            "missing_data_policy": "pairwise deletion",
            "called_bases": "A,C,G,T (U treated as T)",
            "minimum_comparable_sites": minimum_comparable_sites,
            "minimum_coverage": minimum_coverage,
            "pcoa_max_axes": max_axes,
            "pcoa_max_samples": pcoa_max_samples,
        },
    )


# A descriptive alias for callers that expose the combined operation directly.
analyze_distance_pcoa = analyze_distances


def _coerce_records(
    records: Sequence[Any], labels: Optional[Sequence[str]]
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    if not records:
        raise DistanceAnalysisError("At least one aligned sequence is required")
    sequences: List[str] = []
    inferred_names: List[str] = []
    for index, record in enumerate(records):
        if isinstance(record, str):
            sequence = record
            name = f"Sequence {index + 1}"
        else:
            sequence = getattr(record, "sequence", None)
            name = getattr(record, "name", None) or getattr(
                record, "sample_id", None
            ) or f"Sequence {index + 1}"
        if not isinstance(sequence, str) or not sequence:
            raise DistanceAnalysisError(
                f"Sequence {index + 1} is empty or is not a string"
            )
        sequences.append(sequence)
        inferred_names.append(str(name))

    if labels is not None:
        if len(labels) != len(sequences):
            raise DistanceAnalysisError("labels must have the same length as records")
        names = [str(label) for label in labels]
    else:
        names = inferred_names
    if any(not name.strip() for name in names):
        raise DistanceAnalysisError("Sequence labels cannot be empty")
    if len(set(names)) != len(names):
        raise DistanceAnalysisError("Sequence labels must be unique")
    lengths = {len(sequence) for sequence in sequences}
    if len(lengths) != 1:
        raise DistanceAnalysisError(
            "p-distance requires aligned sequences of equal length"
        )
    return tuple(names), tuple(sequences)


def _validate_distance_matrix(
    distance_matrix: Sequence[Sequence[float]],
) -> List[List[float]]:
    if not distance_matrix:
        raise DistanceAnalysisError("Distance matrix cannot be empty")
    size = len(distance_matrix)
    if any(len(row) != size for row in distance_matrix):
        raise DistanceAnalysisError("Distance matrix must be square")
    matrix: List[List[float]] = []
    for row in distance_matrix:
        try:
            matrix.append([float(value) for value in row])
        except (TypeError, ValueError) as exc:
            raise DistanceAnalysisError("Distance matrix must be numeric") from exc
    for row in range(size):
        diagonal = matrix[row][row]
        if math.isfinite(diagonal) and abs(diagonal) > 1e-10:
            raise DistanceAnalysisError("Distance matrix diagonal must be zero")
        for column in range(row + 1, size):
            left, right = matrix[row][column], matrix[column][row]
            if math.isnan(left) and math.isnan(right):
                continue
            if not math.isfinite(left) or not math.isfinite(right):
                raise DistanceAnalysisError(
                    "Distance matrix must be finite or use symmetric NaN values"
                )
            if left < 0.0 or right < 0.0:
                raise DistanceAnalysisError("Distances cannot be negative")
            if not math.isclose(left, right, rel_tol=1e-10, abs_tol=1e-12):
                raise DistanceAnalysisError("Distance matrix must be symmetric")
    return matrix


def _jacobi_eigen(
    symmetric_matrix: Sequence[Sequence[float]],
    *,
    cancel_requested: Optional[Callable[[], bool]] = None,
) -> Tuple[List[float], List[List[float]], bool]:
    """Return eigenvalues and column eigenvectors of a real symmetric matrix."""
    size = len(symmetric_matrix)
    matrix = [list(row) for row in symmetric_matrix]
    vectors = [
        [1.0 if row == column else 0.0 for column in range(size)]
        for row in range(size)
    ]
    scale = max(1.0, max(abs(value) for row in matrix for value in row))
    tolerance = scale * 1e-13
    max_iterations = max(20, 50 * size * size)

    for iteration in range(max_iterations):
        if iteration % max(1, size) == 0:
            _check_cancelled(cancel_requested)
        largest = 0.0
        pivot_row = 0
        pivot_column = 0
        for row in range(size - 1):
            for column in range(row + 1, size):
                candidate = abs(matrix[row][column])
                if candidate > largest:
                    largest = candidate
                    pivot_row, pivot_column = row, column
        if largest <= tolerance:
            return [matrix[index][index] for index in range(size)], vectors, True

        p, q = pivot_row, pivot_column
        angle = 0.5 * math.atan2(
            2.0 * matrix[p][q], matrix[q][q] - matrix[p][p]
        )
        cosine = math.cos(angle)
        sine = math.sin(angle)
        app, aqq, apq = matrix[p][p], matrix[q][q], matrix[p][q]

        for index in range(size):
            if index == p or index == q:
                continue
            aip, aiq = matrix[index][p], matrix[index][q]
            matrix[index][p] = matrix[p][index] = cosine * aip - sine * aiq
            matrix[index][q] = matrix[q][index] = sine * aip + cosine * aiq
        matrix[p][p] = (
            cosine * cosine * app
            - 2.0 * sine * cosine * apq
            + sine * sine * aqq
        )
        matrix[q][q] = (
            sine * sine * app
            + 2.0 * sine * cosine * apq
            + cosine * cosine * aqq
        )
        matrix[p][q] = matrix[q][p] = 0.0

        for row in range(size):
            vip, viq = vectors[row][p], vectors[row][q]
            vectors[row][p] = cosine * vip - sine * viq
            vectors[row][q] = sine * vip + cosine * viq

    return [matrix[index][index] for index in range(size)], vectors, False


def _check_cancelled(
    cancel_requested: Optional[Callable[[], bool]],
) -> None:
    if cancel_requested is not None and cancel_requested():
        raise DistanceAnalysisCancelled("Distance analysis cancelled")
