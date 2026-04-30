"""
Validation utilities for FigEngine.

Provides common validation functions used across the FigEngine codebase.
These functions centralize validation logic and ensure consistent error handling.
"""

from typing import Any, Sequence, Type

import pandas as pd


def validate_dataframe(value: Any, param_name: str = "dataframe") -> pd.DataFrame:
    """
    Validate that value is a pandas DataFrame.

    Args:
        value: Value to validate.
        param_name: Name of the parameter for error messages.

    Returns:
        The validated DataFrame.

    Raises:
        TypeError: If value is not a DataFrame.
    """
    if not isinstance(value, pd.DataFrame):
        raise TypeError(f"{param_name} must be a pandas DataFrame")
    return value


def validate_dict(
    value: Any,
    param_name: str,
    key_type: Type = str,
    allow_empty: bool = True
) -> dict:
    """
    Validate that value is a dict with optional key type constraints.

    Args:
        value: Value to validate.
        param_name: Name of the parameter for error messages.
        key_type: Required type for dict keys.
        allow_empty: Whether empty dicts are allowed.

    Returns:
        The validated dict.

    Raises:
        TypeError: If value is not a dict or keys are wrong type.
        ValueError: If dict is empty and allow_empty=False.
    """
    if not isinstance(value, dict):
        raise TypeError(f"{param_name} must be a dict")

    if not allow_empty and not value:
        raise ValueError(f"{param_name} cannot be empty")

    if key_type is not None:
        for key in value.keys():
            if not isinstance(key, key_type):
                raise TypeError(f"all keys in {param_name} must be {key_type.__name__}")

    return value


def validate_string(
    value: Any,
    param_name: str,
    allow_empty: bool = False,
    max_length: int = None
) -> str:
    """
    Validate that value is a string with optional constraints.

    Args:
        value: Value to validate.
        param_name: Name of the parameter for error messages.
        allow_empty: Whether empty strings are allowed.
        max_length: Maximum allowed string length.

    Returns:
        The validated string.

    Raises:
        TypeError: If value is not a string.
        ValueError: If string is empty and allow_empty=False, or exceeds max_length.
    """
    if not isinstance(value, str):
        raise TypeError(f"{param_name} must be a string")

    if not allow_empty and not value:
        raise ValueError(f"{param_name} cannot be empty")

    if max_length is not None and len(value) > max_length:
        raise ValueError(f"{param_name} cannot exceed {max_length} characters")

    return value


def validate_sequence(
    value: Any,
    param_name: str,
    item_type: Type = str,
    allow_empty: bool = False
) -> Sequence:
    """
    Validate that value is a sequence with optional item type constraints.

    Args:
        value: Value to validate.
        param_name: Name of the parameter for error messages.
        item_type: Required type for sequence items.
        allow_empty: Whether empty sequences are allowed.

    Returns:
        The validated sequence.

    Raises:
        TypeError: If value is not a sequence or items are wrong type.
        ValueError: If sequence is empty and allow_empty=False.
    """
    if isinstance(value, str):
        # Strings are sequences but we usually want to treat them as scalars
        raise TypeError(f"{param_name} must be a sequence, not a string")

    try:
        # Check if it's sequence-like
        len(value)
        iter(value)
    except (TypeError, AttributeError):
        raise TypeError(f"{param_name} must be a sequence")

    if not allow_empty and not value:
        raise ValueError(f"{param_name} cannot be empty")

    if item_type is not None:
        for item in value:
            if not isinstance(item, item_type):
                raise TypeError(f"all items in {param_name} must be {item_type.__name__}")

    return value


def validate_columns_exist(
    df: pd.DataFrame,
    columns: Sequence[str],
    param_name: str = "columns"
) -> None:
    """
    Validate that all specified columns exist in the DataFrame.

    Args:
        df: DataFrame to check against.
        columns: Column names to validate.
        param_name: Name of the parameter for error messages.

    Raises:
        ValueError: If any columns are missing from the DataFrame.
    """
    validate_dataframe(df, "df")
    validate_sequence(columns, param_name, str, allow_empty=True)

    missing = set(columns) - set(df.columns)
    if missing:
        raise ValueError(f"{param_name} {sorted(missing)} not found in dataframe")


def validate_no_duplicates(
    items: Sequence,
    param_name: str
) -> None:
    """
    Validate that a sequence contains no duplicate items.

    Args:
        items: Sequence to check for duplicates.
        param_name: Name of the parameter for error messages.

    Raises:
        ValueError: If duplicates are found.
    """
    validate_sequence(items, param_name, allow_empty=True)

    seen = set()
    duplicates = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)

    if duplicates:
        raise ValueError(f"{param_name} contains duplicates: {sorted(duplicates)}")


def validate_tuple(
    value: Any,
    param_name: str,
    item_type: Type = str,
    allow_empty: bool = True
) -> tuple:
    """
    Validate that value is a tuple with optional item type constraints.

    Args:
        value: Value to validate.
        param_name: Name of the parameter for error messages.
        item_type: Required type for tuple items.
        allow_empty: Whether empty tuples are allowed.

    Returns:
        The validated tuple.

    Raises:
        TypeError: If value is not a tuple or items are wrong type.
        ValueError: If tuple is empty and allow_empty=False.
    """
    if not isinstance(value, tuple):
        raise TypeError(f"{param_name} must be a tuple")

    if not allow_empty and not value:
        raise ValueError(f"{param_name} cannot be empty")

    if item_type is not None:
        for item in value:
            if not isinstance(item, item_type):
                raise TypeError(f"all items in {param_name} must be {item_type.__name__}")

    return value