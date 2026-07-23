"""Pure haplotype identification for aligned DNA/RNA sequences.

NetST defines a haplotype as a group of *identical complete aligned
sequences*.  Ambiguous and missing symbols are therefore retained as literal
states here.  Algorithms that need missing-data filtering (for example RMST)
apply that policy later, without changing the sample-to-haplotype mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from service.format_conversion_service import SequenceRecord


SUPPORTED_SEQUENCE_SYMBOLS = frozenset("ACGTURYSWKMBDHVN?-")


class HaplotypeCalculationError(ValueError):
    """Raised when an alignment cannot be used for haplotype calculation."""


@dataclass(frozen=True)
class Haplotype:
    """One unique aligned sequence and its samples."""

    name: str
    sequence: str
    samples: Tuple[str, ...]

    @property
    def sample_count(self) -> int:
        return len(self.samples)


@dataclass(frozen=True)
class HaplotypeAssignment:
    """The stable mapping from one input sample to one haplotype."""

    sample_name: str
    haplotype: str


@dataclass(frozen=True)
class HaplotypeCalculation:
    """Immutable result of grouping one aligned sequence collection."""

    records: Tuple[SequenceRecord, ...]
    haplotypes: Tuple[Haplotype, ...]
    assignments: Tuple[HaplotypeAssignment, ...]
    alignment_length: int

    def assignment_map(self) -> Dict[str, str]:
        return {
            assignment.sample_name: assignment.haplotype
            for assignment in self.assignments
        }


def identify_haplotypes(
    records: Sequence[SequenceRecord],
    check_cancelled: Optional[Callable[[], None]] = None,
) -> HaplotypeCalculation:
    """Group identical aligned sequences using stable first-observation labels.

    Sequences are upper-cased before comparison.  ``U`` and ``T`` remain
    distinct because silently mixing DNA and RNA states would change the input
    data.  Missing symbols and IUPAC ambiguity codes also remain literal.
    """
    if not records:
        raise HaplotypeCalculationError("No sequences were found")

    normalized: List[SequenceRecord] = []
    seen_names = set()
    expected_length: Optional[int] = None

    for record in records:
        if check_cancelled is not None:
            check_cancelled()

        name = str(record.name).strip()
        if not name:
            raise HaplotypeCalculationError("A sequence has an empty name")
        if name in seen_names:
            raise HaplotypeCalculationError(f"Duplicate sequence name: {name}")
        seen_names.add(name)

        sequence = str(record.sequence).upper()
        if not sequence:
            raise HaplotypeCalculationError(f"Sequence is empty: {name}")
        if expected_length is None:
            expected_length = len(sequence)
        elif len(sequence) != expected_length:
            raise HaplotypeCalculationError(
                "Aligned sequences must have equal lengths: "
                f"{name} has {len(sequence)} sites; expected {expected_length}"
            )

        unsupported = sorted(set(sequence) - SUPPORTED_SEQUENCE_SYMBOLS)
        if unsupported:
            symbols = ", ".join(unsupported[:10])
            raise HaplotypeCalculationError(
                f"Sequence {name} contains unsupported DNA/RNA symbols: {symbols}"
            )
        normalized.append(SequenceRecord(name, sequence))

    sequence_to_index: Dict[str, int] = {}
    group_sequences: List[str] = []
    group_samples: List[List[str]] = []
    assignments: List[HaplotypeAssignment] = []

    for record in normalized:
        if check_cancelled is not None:
            check_cancelled()
        group_index = sequence_to_index.get(record.sequence)
        if group_index is None:
            group_index = len(group_sequences)
            sequence_to_index[record.sequence] = group_index
            group_sequences.append(record.sequence)
            group_samples.append([])
        group_samples[group_index].append(record.name)
        assignments.append(HaplotypeAssignment(record.name, f"H{group_index + 1}"))

    haplotypes = tuple(
        Haplotype(f"H{index + 1}", sequence, tuple(group_samples[index]))
        for index, sequence in enumerate(group_sequences)
    )
    return HaplotypeCalculation(
        records=tuple(normalized),
        haplotypes=haplotypes,
        assignments=tuple(assignments),
        alignment_length=expected_length or 0,
    )
