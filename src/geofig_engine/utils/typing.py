"""
Type definitions and constants for FigEngine.

Centralized location for all type aliases, constants, and enumerations
used throughout the FigEngine codebase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Sequence, Union

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