"""
Type definitions and constants for FigEngine.

Centralized location for all type aliases, constants, and enumerations
used throughout the FigEngine codebase.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Sequence, Union

if TYPE_CHECKING:
    from geofig_engine.core.dimension import Dimension
    from geofig_engine.core.dimension_selector import DimensionSelector
else:
    Dimension = object
    DimensionSelector = object

# Type aliases
DimensionsMap = Dict[str, Dimension]
Selector = Union[str, Sequence[str], Dict[str, Any]]
SourceType = Union[DimensionSelector, str, Sequence[str], Any]

# Constants
ALLOWED_TARGETS = {"x", "y", "x2", "y2", "color", "marker", "size", "style", "alpha", "width"}
VISUAL_ATTRIBUTES = ALLOWED_TARGETS  # Alias for clarity

# Validation constants
MAX_TEMPLATE_NAME_LENGTH = 100
MAX_DIMENSION_NAME_LENGTH = 100
MAX_STRING_LENGTH = 1000  # General purpose max string length


class Channel(Enum):
    """Standard channels for visual elements. Values match mapping keys."""
    X = "x"
    Y = "y"
    X2 = "x2"
    Y2 = "y2"
    COLOR = "color"
    MARKER = "marker"
    SIZE = "size"
    STYLE = "style"
    ALPHA = "alpha"
    WIDTH = "width"
    
@dataclass(frozen=True)
class MappingData:
    """Metadata for a mapping target."""
    name: str  # e.g., "x", "color"
    channel: Channel
    allowed_types: tuple[type, ...]  # (DimensionSelector, str, Dimension, etc.)
    enforce_alignment: bool
    required: bool


class Mapping(Enum):
    """Enum of all available mappings, keyed by semantic name."""
    
    X = MappingData(
        name="x",
        channel=Channel.X,
        allowed_types=(DimensionSelector, str, Sequence, int, float),
        enforce_alignment=True,
        required=True,
    )
    Y = MappingData(
        name="y",
        channel=Channel.Y,
        allowed_types=(DimensionSelector, str, Sequence, int, float),
        enforce_alignment=True,
        required=True,
    )
    X2 = MappingData(
        name="x2",
        channel=Channel.X2,
        allowed_types=(DimensionSelector, str, Sequence, int, float),
        enforce_alignment=False,
        required=False,
    )
    Y2 = MappingData(
        name="y2",
        channel=Channel.Y2,
        allowed_types=(DimensionSelector, str, Sequence, int, float),
        enforce_alignment=False,
        required=False,
    )
    COLOR = MappingData(
        name="color",
        channel=Channel.COLOR,
        allowed_types=(DimensionSelector, str, Sequence, int, float),
        enforce_alignment=False,
        required=False,
    )
    MARKER = MappingData(
        name="marker",
        channel=Channel.MARKER,
        allowed_types=(DimensionSelector, str, Sequence, int, float),
        enforce_alignment=False,
        required=False,
    )
    SIZE = MappingData(
        name="size",
        channel=Channel.SIZE,
        allowed_types=(DimensionSelector, str, Sequence, int, float),
        enforce_alignment=False,
        required=False,
    )
    STYLE = MappingData(
        name="style",
        channel=Channel.STYLE,
        allowed_types=(DimensionSelector, str, Sequence, int, float),
        enforce_alignment=False,
        required=False,
    )
    ALPHA = MappingData(
        name="alpha",
        channel=Channel.ALPHA,
        allowed_types=(DimensionSelector, str, Sequence, int, float),
        enforce_alignment=False,
        required=False,
    )
    WIDTH = MappingData(
        name="width",
        channel=Channel.WIDTH,
        allowed_types=(DimensionSelector, str, Sequence, int, float),
        enforce_alignment=False,
        required=False,
    )
    OXYGEN_18 = MappingData(
        name="oxygen_18",
        channel=Channel.X,
        allowed_types=(DimensionSelector, str, Sequence, int, float),
        enforce_alignment=True,
        required=True,
    )
    DEUTERIUM = MappingData(
        name="deuterium",
        channel=Channel.Y,
        allowed_types=(DimensionSelector, str, Sequence, int, float),
        enforce_alignment=True,
        required=True,
    )
