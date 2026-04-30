"""
AttributeMapping: Declarative visual encoding specifications.

Maps visual attributes (x, y, color, marker, etc.) to data sources.
Purely declarative—stores mappings without accessing data or performing rendering.
"""

from dataclasses import dataclass
from typing import Any, Union

from geofig_engine.core.dimension_selector import DimensionSelector
from geofig_engine.core.dataset import Dataset


SourceType = Union[DimensionSelector, str, list[str], Any]

ALLOWED_TARGETS = {"x", "y", "color", "marker", "size", "alpha", "linestyle"}


@dataclass(frozen=True)
class AttributeMapping:
    """
    Declarative mapping from visual attribute to data source.

    Attributes:
        target: Visual attribute name (x, y, color, marker, etc.)
        source: Data source specification:
            - DimensionSelector: resolves to matching columns
            - str: single column name
            - list[str]: explicit column names
            - Any: constant value (color, number, etc.)
    """

    target: str
    source: SourceType

    def __post_init__(self) -> None:
        """Validate mapping on creation."""
        validate_attribute_mapping(self)


def validate_attribute_mapping(mapping: AttributeMapping) -> None:
    """
    Validate an AttributeMapping.

    Raises:
        ValueError: If target is not in ALLOWED_TARGETS
        TypeError: If source is of invalid type
        ValueError: If source is a DimensionSelector with invalid structure
    """
    if mapping.target not in ALLOWED_TARGETS:
        raise ValueError(
            f"Invalid target '{mapping.target}'. "
            f"Must be one of {ALLOWED_TARGETS}"
        )

    if not isinstance(mapping.source, (DimensionSelector, str, list)):
        # Allow Any for constants, but it must not be a dict (unless DimensionSelector)
        if isinstance(mapping.source, dict) and not isinstance(
            mapping.source, DimensionSelector
        ):
            raise TypeError(
                "source dict must be a DimensionSelector, not a plain dict"
            )

    if isinstance(mapping.source, list):
        if not mapping.source:
            raise ValueError("source list cannot be empty")
        if not all(isinstance(col, str) for col in mapping.source):
            raise TypeError("all elements in source list must be strings")


def resolve_source(
    source: SourceType, dataset: Dataset, strict: bool = False
) -> Union[list[str], Any]:
    """
    Resolve a source specification to concrete column names or constant value.

    Args:
        source: One of DimensionSelector, str, list[str], or constant
        dataset: Dataset for resolving DimensionSelector
        strict: If True, treat string as column name only (raise if not found).
                If False (default), treat string as constant if column doesn't exist.

    Returns:
        - DimensionSelector → list of column names
        - str → list with single column name (if in dataset) or constant value
        - list[str] → list as-is
        - constant → value as-is

    Raises:
        ValueError: If DimensionSelector matches no columns
        KeyError: If column names don't exist in dataset (strict mode)
    """
    if isinstance(source, DimensionSelector):
        return source.resolve(dataset)

    if isinstance(source, str):
        # Check if it's a column name first
        if source in dataset.dataframe.columns:
            return [source]
        # Not a column; treat as constant
        if strict:
            raise KeyError(f"Column '{source}' not found in dataset")
        return source

    if isinstance(source, list):
        missing = set(source) - set(dataset.dataframe.columns)
        if missing:
            raise KeyError(f"Columns not found in dataset: {missing}")
        return source

    # Constant value
    return source
