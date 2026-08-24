"""
Core data models for categorized geometry presets.

A geom preset is a named, categorized catalog entry that hydrates into
one or more standard Layers built from annotation geometry types
(reference lines, bands, rectangles, labels). Presets are data-only:
adding a new preset requires no code changes.

Supported geometry kinds (see GEOM_KINDS):
    function_line  - expression-driven reference line (e.g., GMWL)
    abline         - slope/intercept or two-point line
    hspan          - horizontal band (ymin..ymax via mapping)
    vspan          - vertical band (xmin..xmax via mapping)
    rect           - rectangle (all four bounds via mapping)
    text           - positioned annotation label (x/y/label via mapping)
"""

from dataclasses import dataclass, field
from typing import Any


GEOM_KINDS: tuple[str, ...] = (
    "function_line",
    "abline",
    "hspan",
    "vspan",
    "rect",
    "text",
)


@dataclass(frozen=True)
class GeomPresetItem:
    """One drawable element within a geom preset."""

    # Geometry identity and validated parameters (kind-specific)
    geom_type: str                      # One of GEOM_KINDS
    params: dict[str, Any]              # e.g. {"func": "8*x + 10"} for function_line
    mapping: dict[str, Any]             # Constant visual mapping (scalars only)

    zorder: int | None = None

    # function_line only: legacy FunctionType value ("linear", etc.)
    # retained so the deprecated MathFunction shim round-trips losslessly.
    func_type: str | None = None

    def __post_init__(self) -> None:
        if self.geom_type not in GEOM_KINDS:
            raise ValueError(f"geom_type '{self.geom_type}' not in {GEOM_KINDS}")
        if not isinstance(self.params, dict):
            raise TypeError("params must be a dict")
        if not isinstance(self.mapping, dict):
            raise TypeError("mapping must be a dict")
        if self.zorder is not None and (not isinstance(self.zorder, int) or isinstance(self.zorder, bool)):
            raise TypeError("zorder must be an int or None")


@dataclass(frozen=True)
class GeomPreset:
    """Named preset entry resolving to one or more Layers."""

    id: str                             # Unique identifier (e.g., "GMWL")
    category: str                       # Category key (e.g., "water_isotope")
    items: tuple[GeomPresetItem, ...]   # Drawable elements

    tags: tuple[str, ...] = ()          # Free-form queryable tags
    reference: str | None = None        # Citation/source
    description: str | None = None      # Detailed description
    valid_domain: str | None = None     # Domain constraint (e.g., "x > 0")
    geospatial: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise ValueError("id must be a non-empty string")
        if not self.category or not isinstance(self.category, str):
            raise ValueError("category must be a non-empty string")
        if not isinstance(self.items, tuple) or len(self.items) == 0:
            raise ValueError("items must be a non-empty tuple of GeomPresetItem")
        for item in self.items:
            if not isinstance(item, GeomPresetItem):
                raise TypeError("items must contain only GeomPresetItem instances")
        if not isinstance(self.tags, tuple) or not all(isinstance(t, str) for t in self.tags):
            raise TypeError("tags must be a tuple of strings")
        if not isinstance(self.geospatial, dict):
            raise TypeError("geospatial must be a dict")

    @property
    def state(self) -> str | None:
        """State/province code from geospatial metadata, if any."""
        return self.geospatial.get("state")

    @property
    def geom_kinds(self) -> set[str]:
        """Set of geometry kinds used by this preset's items."""
        return {item.geom_type for item in self.items}
