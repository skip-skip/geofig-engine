"""
Core data models for mathematical function definitions.

Provides enums and dataclasses for representing functions with
full metadata, categories, types, and geospatial information.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FunctionType(Enum):
    """Supported mathematical function types."""

    LINEAR = "linear"              # y = mx + b
    POLYNOMIAL = "polynomial"      # y = ax^n + ... + c
    EXPONENTIAL = "exponential"    # y = a*e^(bx) or a*b^x
    LOGARITHMIC = "logarithmic"    # y = a*ln(x) + b
    POWER = "power"                # y = a*x^b
    RATIONAL = "rational"          # y = (ax+b)/(cx+d)
    CUSTOM = "custom"              # Arbitrary expression


class FunctionCategory(Enum):
    """Domain/application categories for functions."""

    WATER_ISOTOPE = "water_isotope"    # Isotope reference lines (GMWL, LMWL, etc.)
    CALIBRATION = "calibration"        # Lab calibration curves
    EMPIRICAL = "empirical"            # Empirical relationships
    REFERENCE = "reference"            # Standard/theoretical references
    CUSTOM = "custom"                  # User-defined


@dataclass(frozen=True)
class GeospatialMetadata:
    """Geospatial metadata for a function."""

    region: str | None = None              # Geographic region (e.g., "Pacific Northwest")
    state: str | None = None               # State/province code (e.g., "ID", "WA")
    city: str | None = None                # City/locality (e.g., "Moscow", "Pullman")
    water_body: str | None = None          # Water body name (e.g., "Snake River", "Palouse River")
    water_type: str | None = None          # Water type (e.g., "meteoric", "surface", "ground")


@dataclass(frozen=True)
class MathFunction:
    """Represents a mathematical function with full metadata."""

    # Identity
    id: str                             # Unique identifier (e.g., "GMWL", "ID_MOSCOW")
    category: FunctionCategory          # Domain classification

    # Function definition
    func_type: FunctionType             # Mathematical type
    expression: str                     # Raw expression (e.g., "8*x + 10")
    variables: tuple[str, ...]          # Variables in expression (e.g., ("x",))

    # Visualization
    color: str                          # Plot color (e.g., "black")
    linestyle: str                      # Plot linestyle (e.g., "--")
    label: str                          # Display label

    # Metadata
    reference: str | None = None        # Citation/source
    description: str | None = None      # Detailed description
    valid_domain: str | None = None     # Domain constraint (e.g., "x > 0")

    # Geospatial
    geospatial: GeospatialMetadata = field(default_factory=GeospatialMetadata)

    # Custom metadata
    custom_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate fields."""
        if not self.id or not isinstance(self.id, str):
            raise ValueError("id must be a non-empty string")
        if not self.label or not isinstance(self.label, str):
            raise ValueError("label must be a non-empty string")
        if not self.expression or not isinstance(self.expression, str):
            raise ValueError("expression must be a non-empty string")
        if not self.variables or len(self.variables) == 0:
            raise ValueError("variables must be a non-empty tuple")
        if not self.color or not isinstance(self.color, str):
            raise ValueError("color must be a non-empty string")
        if not self.linestyle or not isinstance(self.linestyle, str):
            raise ValueError("linestyle must be a non-empty string")
