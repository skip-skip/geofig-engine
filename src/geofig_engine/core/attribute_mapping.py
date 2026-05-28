"""
AttributeMapping: Declarative visual encoding specifications.

Maps visual attributes (x, y, color, marker, etc.) to data sources.
Purely declarative—stores mappings without accessing data or performing rendering.
"""

from dataclasses import dataclass
from typing import Any, Union

from geofig_engine.core.dimension_selector import DimensionSelector
from geofig_engine.core.dataset import Dataset
from geofig_engine.utils.typing import ALLOWED_TARGETS, SourceType
from geofig_engine.utils.validation import validate_sequence, validate_string


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
        ValueError: If target is not in ALLOWED_TARGETS.
        TypeError: If source is of invalid type.
    """
    validate_string(mapping.target, "target", allow_empty=False)

    if mapping.target not in ALLOWED_TARGETS:
        raise ValueError(
            f"Invalid target '{mapping.target}'. Must be one of {ALLOWED_TARGETS}"
        )

    if isinstance(mapping.source, list):
        validate_sequence(mapping.source, "source", str, allow_empty=False)
    elif isinstance(mapping.source, dict) and not isinstance(
        mapping.source, DimensionSelector
    ):
        raise TypeError(
            "source dict must be a DimensionSelector, not a plain dict"
        )


def resolve_source(
    source: SourceType,
    dataset: Dataset,
    strict: bool = False,
    context: dict[str, Any] | None = None,
) -> Union[list[str], Any]:
    """
    Resolve a source specification to concrete column names or constant value.

    Args:
        source: One of DimensionSelector, str, list[str], or constant
        dataset: Dataset for resolving DimensionSelector
        strict: If True, treat string as column name only (raise if not found).
                If False (default), treat string as constant if column doesn't exist.
        context: Optional context for string formatting placeholders.

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
        if context:
            try:
                source = source.format(**context)
            except KeyError:
                pass

        # Check if it's a column name first
        if source in dataset.dataframe.columns:
            return [source]
        # Not a column; treat as constant
        if strict:
            raise KeyError(f"Column '{source}' not found in dataset")
        return source

    if isinstance(source, list):
        resolved: list[str] = []
        for item in source:
            if context and isinstance(item, str):
                try:
                    item = item.format(**context)
                except KeyError:
                    pass
            if item not in dataset.dataframe.columns:
                raise KeyError(f"Columns not found in dataset: {item}")
            resolved.append(item)
        return resolved

    # Constant value
    return source

