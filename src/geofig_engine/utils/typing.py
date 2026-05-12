"""
Type definitions and constants for FigEngine.

Centralized location for all type aliases, constants, and enumerations
used throughout the FigEngine codebase.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Dict, Sequence, Union

from geofig_engine.core.iterator import DimensionIterator

if TYPE_CHECKING:
    from geofig_engine.core.dimension import Dimension
    from geofig_engine.core.dimension_selector import DimensionSelector
else:
    Dimension = object
    DimensionSelector = object

# Type aliases
DimensionsMap = Dict[str, Dimension]
SourceType = Union[DimensionSelector, str, Sequence[str], Any]
Selector = Union[str, Sequence[str], Dict[str, Any]]

# Constants
ALLOWED_TARGETS = {"x", "y", "color", "marker", "size", "alpha", "linestyle"}
VISUAL_ATTRIBUTES = ALLOWED_TARGETS  # Alias for clarity

# Validation constants
MAX_TEMPLATE_NAME_LENGTH = 100
MAX_DIMENSION_NAME_LENGTH = 100
MAX_STRING_LENGTH = 1000  # General purpose max string length
"y2", "color", "marker", "size", "style", "alpha", "width"
class ATTRIBUTE(Enum):
    X= auto(),
    Y= auto(),
    Y2 = auto(),
    COLOR = auto(),
    MARKER = auto(),
    SIZE = auto(),
    STYLE = auto(),
    ALPHA = auto(),
    WIDTH = auto(),
class SourceType(Enum):
    SINGLE = [int, str, float]
    ITERATOR = DimensionIterator    # Must also be in DIMENSION mode
    DIMENSION = Dimension

@dataclass(frozen=True)
class Mapping():
    attribute = ATTRIBUTE,
    allowed_types = tuple[SourceType],
    enforce_alignment = bool,
    required = bool,
    #dependencies = tuple[ATTRIBUTE]
MAPPINGS = [
    Mapping(
        attribute = ATTRIBUTE.X,
        allowed_types = (SourceType.ITERATOR, SourceType.DIMENSION),
        enforce_alignment = True,
        required = True
    ),
    Mapping(
        attribute = ATTRIBUTE.Y,
        allowed_types = (SourceType.ITERATOR, SourceType.DIMENSION),
        enforce_alignment = True,
        required = True
    ),

    Mapping(
        attribute = ATTRIBUTE.COLOR,
        allowed_types = (SourceType.SINGLE, SourceType.ITERATOR, SourceType.DIMENSION),
        enforce_alignment = False,
        required = False
    ),
    Mapping(
        attribute = ATTRIBUTE.MARKER,
        allowed_types = (SourceType.SINGLE, SourceType.ITERATOR, SourceType.DIMENSION),
        enforce_alignment = False,
        required = False
    ),
    Mapping(
        attribute = ATTRIBUTE.SIZE,
        allowed_types = (SourceType.SINGLE, SourceType.ITERATOR, SourceType.DIMENSION),
        enforce_alignment = False,
        required = False
    ),
    Mapping(
        attribute = ATTRIBUTE.STYLE,
        allowed_types = (SourceType.SINGLE, SourceType.ITERATOR, SourceType.DIMENSION),
        enforce_alignment = False,
        required = False
    ),
    Mapping(
        attribute = ATTRIBUTE.ALPHA,
        allowed_types = (SourceType.SINGLE, SourceType.ITERATOR, SourceType.DIMENSION),
        enforce_alignment = False,
        required = False
    ),
    Mapping(
        attribute = ATTRIBUTE.WIDTH,
        allowed_types = (SourceType.SINGLE, SourceType.ITERATOR, SourceType.DIMENSION),
        enforce_alignment = False,
        required = False
    )
]
