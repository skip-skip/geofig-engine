"""
Utility helpers for FigEngine.

This package exports shared types, constants, and validation helpers used by
core modules across the FigEngine codebase.
"""

from .typing import (
    ALLOWED_TARGETS,
    DimensionsMap,
    Selector,
    SourceType,
    VISUAL_ATTRIBUTES,
)
from .validation import (
    validate_columns_exist,
    validate_dataframe,
    validate_dict,
    validate_no_duplicates,
    validate_sequence,
    validate_string,
    validate_tuple,
)

__all__ = [
    "ALLOWED_TARGETS",
    "DimensionsMap",
    "Selector",
    "SourceType",
    "VISUAL_ATTRIBUTES",
    "validate_columns_exist",
    "validate_dataframe",
    "validate_dict",
    "validate_no_duplicates",
    "validate_sequence",
    "validate_string",
    "validate_tuple",
]