"""
FigureSpec: Renderer-agnostic plotting instructions.

Concrete, fully resolved plotting instruction that serves as the contract
between the FigEngine system and rendering backends.
"""

from dataclasses import dataclass, field
from typing import Any, Union

import pandas as pd

from geofig_engine.layers.base import FigureLayer
from geofig_engine.utils.validation import (
    validate_columns_exist,
    validate_dataframe,
    validate_dict,
    validate_sequence,
    validate_string,
    validate_tuple,
)


@dataclass(frozen=True)
class FigureSpec:
    """
    Concrete plotting instruction for renderers.

    This is the final, fully resolved specification that renderers use to
    create visualizations. All DimensionSelectors have been resolved to
    concrete column names, and all data references are validated.

    Attributes:
        data: The DataFrame containing the data to plot.
        mappings: Dict mapping visual attributes to resolved data sources:
            - list[str]: column names (concatenated if multiple)
            - Any: constant values (colors, numbers, etc.)
        settings: Dict of rendering settings (alpha, title, figsize, etc.).
        context: Dict of iterator context values for this figure.
        template_name: Name of the template that generated this spec.
        iterator_key: Tuple of column names used for iteration (empty if none).
    """

    data: pd.DataFrame
    mappings: dict[str, Any]
    settings: dict[str, Any]
    context: dict[str, Any]
    template_name: str
    iterator_key: tuple[str, ...] = ()
    layers: list[FigureLayer] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate spec on creation."""
        validate_figure_spec(self)


def validate_figure_spec(spec: FigureSpec) -> None:
    """
    Validate a FigureSpec instance.

    Args:
        spec: The FigureSpec to validate.

    Raises:
        TypeError: If data is not a DataFrame, or mappings/settings/context
                   are not dicts, or template_name is not a string,
                   or iterator_key is not a tuple.
        ValueError: If template_name is empty, or iterator_key contains
                    non-strings, or mappings contain invalid values.
    """
    validate_dataframe(spec.data, "data")
    validate_dict(spec.mappings, "mappings")

    for key, value in spec.mappings.items():
        if isinstance(value, list):
            validate_sequence(value, f"mapping '{key}'", str, allow_empty=False)
            validate_columns_exist(spec.data, value, f"mapping '{key}'")
        elif isinstance(value, dict):
            raise TypeError(f"mapping '{key}' must be a DimensionSelector, not a plain dict")

    validate_dict(spec.settings, "settings")
    validate_dict(spec.context, "context")
    validate_string(spec.template_name, "template_name", allow_empty=False)
    validate_tuple(spec.iterator_key, "iterator_key", str, allow_empty=True)


def build_spec(
    data: pd.DataFrame,
    mappings: dict[str, Any],
    settings: dict[str, Any],
    context: dict[str, Any],
    template_name: str,
    iterator_key: tuple[str, ...] = (),
    layers: list[FigureLayer] | None = None,
) -> FigureSpec:
    """
    Factory function to create and validate a FigureSpec.

    Args:
        data: The DataFrame containing the data to plot.
        mappings: Dict mapping visual attributes to resolved data sources.
        settings: Dict of rendering settings.
        context: Dict of iterator context values.
        template_name: Name of the template that generated this spec.
        iterator_key: Tuple of column names used for iteration.

    Returns:
        A validated FigureSpec instance.

    Raises:
        TypeError: If inputs have invalid types.
        ValueError: If inputs have invalid values.
    """
    return FigureSpec(
        data=data,
        mappings=mappings,
        settings=settings,
        context=context,
        template_name=template_name,
        iterator_key=iterator_key,
        layers=layers or [],
    )


def extract_data_for_mapping(
    spec: FigureSpec, mapping_key: str
) -> Union[pd.Series, Any, None]:
    """
    Extract the actual data for a given mapping key.

    Args:
        spec: The FigureSpec to extract from.
        mapping_key: The mapping key to extract (e.g., "x", "y", "color").

    Returns:
        - For column mappings: pd.Series (concatenated if multiple columns)
        - For constant mappings: the constant value
        - For missing mappings: None

    Raises:
        KeyError: If mapping references non-existent columns.
    """
    if mapping_key not in spec.mappings:
        return None

    mapping_value = spec.mappings[mapping_key]

    if isinstance(mapping_value, list):
        # Column reference(s)
        if len(mapping_value) == 1:
            return spec.data[mapping_value[0]]
        else:
            # Multiple columns - concatenate
            series_list = [spec.data[col] for col in mapping_value]
            return pd.concat(series_list, ignore_index=True)
    else:
        # Constant value
        return mapping_value