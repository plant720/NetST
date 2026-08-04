"""
Data model representing a single taxon/sequence entry.
Corresponds to the rows in the VB.NET DataGridView.
"""
from dataclasses import dataclass, field
import math
from typing import Dict


@dataclass
class TaxonData:
    """Data model for a single taxon/sequence entry.

    ``discrete_traits`` and ``continuous_traits`` hold the *group* and *primary
    continuous* trait values respectively, kept for backward compatibility with
    the classic single-trait pipeline. ``traits`` holds every named trait value
    (including those two) so a project can carry several traits per sample; the
    project-level :class:`~model.trait_schema.TraitSchema` describes their type
    and how each is visualized.
    """

    id: int = 0
    name: str = ""
    sequence: str = ""
    discrete_traits: str = ""
    continuous_traits: str = "0"
    quantity: int = 1
    organism: str = ""
    selected: bool = True
    traits: Dict[str, str] = field(default_factory=dict)

    def trait_value(self, name: str, default: str = "") -> str:
        """Return the value for a named trait, or ``default`` if absent."""
        value = self.traits.get(name)
        return default if value is None else str(value)

    @property
    def display_sequence(self) -> str:
        """Returns truncated sequence for display (max 1000 chars)."""
        if self.sequence and len(self.sequence) > 1000:
            return self.sequence[:1000] + "..."
        return self.sequence

    @property
    def sequence_length(self) -> int:
        """Returns the length of the sequence."""
        return len(self.sequence) if self.sequence else 0

    def is_valid_continuous_traits(self) -> bool:
        """Return whether the continuous trait is a finite numeric value."""
        try:
            return math.isfinite(float(self.continuous_traits))
        except (ValueError, TypeError):
            return False

    def to_fasta_header(self, delimiter: str = "|") -> str:
        """Generate FASTA header string."""
        delimiter = str(delimiter).replace("\r", "").replace("\n", "") or "|"
        parts = [
            self._single_line_header(self.name).replace(delimiter, "_"),
            self._single_line_header(self.discrete_traits).replace(delimiter, "_"),
            self._single_line_header(self.continuous_traits).replace(delimiter, "_"),
        ]
        return ">" + delimiter.join(parts)

    def to_analysis_header(self) -> str:
        """Generate header for analysis FASTA file."""
        return f">{self._single_line_header(self.name)}"

    @staticmethod
    def _single_line_header(value: object) -> str:
        """Normalize user-editable text before placing it in a FASTA header."""
        return str(value).replace("\r", "_").replace("\n", "_")

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'sequence': self.sequence,
            'discrete_traits': self.discrete_traits,
            'continuous_traits': self.continuous_traits,
            'quantity': self.quantity,
            'organism': self.organism,
            'selected': self.selected,
            'traits': dict(self.traits),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TaxonData':
        """Create TaxonData from dictionary."""
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            sequence=data.get('sequence', ''),
            discrete_traits=data.get('discrete_traits', ''),
            continuous_traits=data.get('continuous_traits', '0'),
            quantity=data.get('quantity', 1),
            organism=data.get('organism', ''),
            selected=data.get('selected', True),
            traits=dict(data.get('traits') or {}),
        )

    def __str__(self) -> str:
        return f"TaxonData(id={self.id}, name='{self.name}', seq_len={self.sequence_length})"
