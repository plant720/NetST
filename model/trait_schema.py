"""Project-level metadata (trait) schema for haplotype-network visualization.

A project may carry several named traits per sample. Each trait is either
``discrete`` (a categorical grouping shown as segmented rings) or ``continuous``
(a numeric value shown as a colour gradient). Exactly one discrete trait is the
*group*: the primary grouping drawn as the innermost ring and used as the
default for grouped analyses.

This module owns only the schema and the built-in colour tables. It has no Qt or
rendering dependency so it can be unit-tested and reused by the config
generator, the metadata tab, and the import/export services.
"""

from __future__ import annotations

import colorsys
from dataclasses import dataclass, field
import hashlib
import math
import random
from typing import Dict, List, Optional, Sequence, Tuple


DISCRETE = "discrete"
CONTINUOUS = "continuous"
TRAIT_KINDS = (DISCRETE, CONTINUOUS)


# Curated categorical palettes selected by the total number of categories.
CATEGORICAL_COLOR_SETS: Dict[int, Tuple[str, ...]] = {
    1: ("#0072B2",),
    2: ("#0072B2", "#D55E00"),
    3: ("#D85356", "#D7AA36", "#94BBAD"),
    4: ("#F0776D", "#FBD2CB", "#29B4B6", "#C5E7E8"),
    5: ("#8386A8", "#D15C6B", "#F5CF36", "#8FB943", "#78B9D2"),
    6: ("#DA352A", "#FF8748", "#5BAA56", "#B8BB5B", "#4186B7", "#8679BE"),
    7: ("#794292", "#44599B", "#2C8FA0", "#40A93B", "#EFE644", "#E97124", "#DF4442"),
    8: ("#FF7F00", "#FDBF6F", "#E31A1C", "#FB9A99",
        "#33A02C", "#B2DF8A", "#1F78B4", "#A6CEE3"),
    9: ("#E71F19", "#2CB8BB", "#55B333", "#6A1B86", "#E2C9E1",
        "#A4C5E8", "#EF7A1C", "#F9CA9C", "#F7C3C4"),
    10: ("#009F72", "#D25F27", "#E49E21", "#EFE341", "#1F78B4",
         "#FB9A99", "#E21A1C", "#EAD59F", "#C9B1D4", "#52310F"),
}
# Retain the public one-theme palette registry for saved schema compatibility.
DISCRETE_PALETTES: Dict[str, Tuple[str, ...]] = {
    "Default": CATEGORICAL_COLOR_SETS[10],
}
DEFAULT_DISCRETE_PALETTE = "Default"

# Neutral fill for the implicit "unassigned / missing" category.
UNASSIGNED_COLOR = "#DDDDDD"


# One built-in numeric gradient. Its endpoints remain manually editable.
CONTINUOUS_SCHEMES: Dict[str, Tuple[str, str]] = {
    "Default": ("#BDBDBD", "#000000"),
}
DEFAULT_CONTINUOUS_SCHEME = "Default"


def normalize_hex_color(value: object) -> Optional[str]:
    """Return a normalized ``#RRGGBB`` colour, or ``None`` when invalid."""
    text = str(value or "").strip()
    if not text.startswith("#"):
        text = "#" + text
    body = text[1:]
    if len(body) == 3 and all(c in "0123456789abcdefABCDEF" for c in body):
        body = "".join(c * 2 for c in body)
    if len(body) == 6 and all(c in "0123456789abcdefABCDEF" for c in body):
        return "#" + body.upper()
    return None


def _sanitize_hex(value: str, fallback: str) -> str:
    return normalize_hex_color(value) or fallback


def default_category_colors(
    categories: Sequence[str], *, seed: str = "", excluded: Sequence[str] = ()
) -> Dict[str, str]:
    """Return default colours in first-seen category order.

    Two through ten categories use the corresponding curated set. Larger
    collections receive deterministic pseudo-random colours, with explicit
    collision avoidance so refreshes are stable and every category is unique.
    """
    ordered = list(dict.fromkeys(str(category) for category in categories))
    palette = CATEGORICAL_COLOR_SETS.get(len(ordered))
    if palette is not None:
        return dict(zip(ordered, palette))

    reserved = {
        color for value in excluded
        if (color := normalize_hex_color(value)) is not None
    }
    reserved.add(UNASSIGNED_COLOR)
    seed_text = "\0".join([str(seed)] + ordered)
    digest = hashlib.sha256(seed_text.encode("utf-8")).digest()
    generator = random.Random(int.from_bytes(digest[:8], "big"))
    result: Dict[str, str] = {}
    for category in ordered:
        while True:
            # Restrict saturation/value to keep colours visible on white while
            # retaining a broad random hue distribution.
            hue = generator.random()
            saturation = 0.52 + generator.random() * 0.38
            value = 0.62 + generator.random() * 0.32
            red, green, blue = colorsys.hsv_to_rgb(hue, saturation, value)
            color = "#{:02X}{:02X}{:02X}".format(
                round(red * 255), round(green * 255), round(blue * 255))
            if color not in reserved:
                reserved.add(color)
                result[category] = color
                break
    return result


@dataclass
class TraitDefinition:
    """One named trait and how it should be visualized."""

    name: str
    kind: str = DISCRETE
    is_group: bool = False
    visualize: bool = True
    order: int = 0
    # Discrete: palette name plus explicit per-category overrides.
    palette: str = DEFAULT_DISCRETE_PALETTE
    category_colors: Dict[str, str] = field(default_factory=dict)
    # Continuous: gradient scheme name.
    scheme: str = DEFAULT_CONTINUOUS_SCHEME
    # Optional user-selected endpoints.  Keeping these separate from ``scheme``
    # lets the UI return to any built-in gradient without losing the selected
    # scheme name.
    gradient_low: Optional[str] = None
    gradient_high: Optional[str] = None

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        if self.kind not in TRAIT_KINDS:
            raise ValueError(f"Unknown trait kind: {self.kind!r}")
        if self.kind == CONTINUOUS:
            # A continuous trait can never be the discrete grouping.
            self.is_group = False

    def resolve_category_colors(
        self, categories: Sequence[str]
    ) -> Dict[str, str]:
        """Assign a stable colour to each discrete category.

        Explicit overrides win. Two to ten categories use the matching curated
        palette; larger collections use stable, non-repeating random colours.
        """
        if self.kind != DISCRETE:
            return {}
        ordered = list(dict.fromkeys(str(category) for category in categories))
        overrides = {
            category: color
            for category in ordered
            if (color := normalize_hex_color(self.category_colors.get(category)))
        }
        defaults = default_category_colors(
            ordered, seed=self.name, excluded=tuple(overrides.values()))
        return {
            category: overrides.get(category, defaults[category])
            for category in ordered
        }

    def gradient_endpoints(self) -> Tuple[str, str]:
        """Return the (low, high) gradient colours for a continuous trait."""
        default_low, default_high = CONTINUOUS_SCHEMES.get(
            self.scheme, CONTINUOUS_SCHEMES[DEFAULT_CONTINUOUS_SCHEME])
        return (
            _sanitize_hex(self.gradient_low, default_low)
            if self.gradient_low else default_low,
            _sanitize_hex(self.gradient_high, default_high)
            if self.gradient_high else default_high,
        )

    def has_custom_gradient(self) -> bool:
        return bool(self.gradient_low or self.gradient_high)

    def clear_custom_gradient(self) -> None:
        self.gradient_low = None
        self.gradient_high = None


class TraitSchema:
    """Ordered collection of trait definitions with exactly one group."""

    def __init__(self, definitions: Optional[Sequence[TraitDefinition]] = None) -> None:
        self._by_name: Dict[str, TraitDefinition] = {}
        self._order: List[str] = []
        for definition in definitions or ():
            self.add(definition)
        self._normalize_group()

    # ── construction ────────────────────────────────────────────────────────

    def add(self, definition: TraitDefinition) -> TraitDefinition:
        if not definition.name:
            raise ValueError("Trait name cannot be empty")
        if definition.name not in self._by_name:
            self._order.append(definition.name)
        self._by_name[definition.name] = definition
        return definition

    @classmethod
    def from_columns(
        cls, columns: Sequence[Tuple[str, str]], group: Optional[str] = None
    ) -> "TraitSchema":
        """Build a schema from ``(name, kind)`` pairs in display order.

        The group defaults to the first discrete trait unless one is named.
        """
        definitions = [
            TraitDefinition(name=name, kind=kind, order=index)
            for index, (name, kind) in enumerate(columns)
        ]
        schema = cls(definitions)
        if group and group in schema._by_name and schema._by_name[group].kind == DISCRETE:
            schema.set_group(group)
        return schema

    # ── queries ─────────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._order)

    def __contains__(self, name: str) -> bool:
        return name in self._by_name

    def get(self, name: str) -> Optional[TraitDefinition]:
        return self._by_name.get(name)

    def ordered(self) -> List[TraitDefinition]:
        return [self._by_name[name] for name in self._order]

    def discrete(self) -> List[TraitDefinition]:
        return [d for d in self.ordered() if d.kind == DISCRETE]

    def continuous(self) -> List[TraitDefinition]:
        return [d for d in self.ordered() if d.kind == CONTINUOUS]

    def visualized(self) -> List[TraitDefinition]:
        """Traits drawn as rings: the group innermost, then the rest by order."""
        group = self.group()
        rest = [
            d for d in self.ordered()
            if d.visualize and not (group is not None and d.name == group.name)
        ]
        rings = [group] if group is not None and group.visualize else []
        return rings + rest

    def group(self) -> Optional[TraitDefinition]:
        for definition in self.ordered():
            if definition.kind == DISCRETE and definition.is_group:
                return definition
        return None

    def has_group(self) -> bool:
        return self.group() is not None

    def primary_continuous(self) -> Optional[TraitDefinition]:
        """The first visualized continuous trait (drives the classic outer ring)."""
        for definition in self.continuous():
            if definition.visualize:
                return definition
        return self.continuous()[0] if self.continuous() else None

    # ── mutation ────────────────────────────────────────────────────────────

    def merge(self, other: "TraitSchema") -> None:
        """Add traits from ``other`` (a later Load Metadata) into this schema.

        Existing traits keep their definition (kind, colours, group flag); only
        genuinely new trait names are appended. If this schema has no group yet,
        the other schema's group is adopted.
        """
        had_group = self.has_group()
        for definition in other.ordered():
            if definition.name not in self._by_name:
                self.add(TraitDefinition(
                    name=definition.name,
                    kind=definition.kind,
                    order=len(self._order),
                    visualize=definition.visualize,
                    palette=definition.palette,
                    category_colors=dict(definition.category_colors),
                    scheme=definition.scheme,
                    gradient_low=definition.gradient_low,
                    gradient_high=definition.gradient_high,
                ))
        if not had_group and other.has_group():
            adopted = other.group().name
            if adopted in self._by_name and self._by_name[adopted].kind == DISCRETE:
                self.set_group(adopted)
        self._normalize_group()

    def set_group(self, name: str) -> None:
        target = self._by_name.get(name)
        if target is None or target.kind != DISCRETE:
            raise ValueError(f"Trait {name!r} cannot be the group")
        for definition in self._by_name.values():
            definition.is_group = definition.name == name

    def _normalize_group(self) -> None:
        """Ensure at most/at least one discrete group when discrete traits exist."""
        groups = [d for d in self.ordered() if d.kind == DISCRETE and d.is_group]
        discretes = self.discrete()
        if not discretes:
            for definition in groups:
                definition.is_group = False
            return
        if len(groups) == 1:
            return
        if len(groups) > 1:
            for definition in groups[1:]:
                definition.is_group = False
            return
        # No group set yet: promote the first discrete trait.
        discretes[0].is_group = True


def is_meaningful_continuous(value: object) -> bool:
    """Whether a continuous value is finite and non-zero (worth visualizing)."""
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number != 0.0
