"""
Tests for shared utility functions in geofig_engine.utils.
"""

import pytest
import pandas as pd

from geofig_engine.utils.validation import (
    validate_columns_exist,
    validate_dataframe,
    validate_dict,
    validate_sequence,
    validate_string,
    validate_tuple,
)
from geofig_engine.utils.typing import ALLOWED_TARGETS, DimensionsMap, Selector, SourceType


def test_validate_dataframe_accepts_dataframe():
    df = pd.DataFrame({"x": [1, 2, 3]})
    result = validate_dataframe(df, "dataframe")
    assert result is df


def test_validate_dataframe_rejects_non_dataframe():
    with pytest.raises(TypeError, match="dataframe must be a pandas DataFrame"):
        validate_dataframe([1, 2, 3], "dataframe")


def test_validate_dict_accepts_valid_dict():
    value = {"a": 1}
    result = validate_dict(value, "params", key_type=str)
    assert result == value


def test_validate_dict_rejects_non_dict():
    with pytest.raises(TypeError, match="params must be a dict"):
        validate_dict([1, 2], "params")


def test_validate_dict_rejects_empty_when_not_allowed():
    with pytest.raises(ValueError, match="params cannot be empty"):
        validate_dict({}, "params", allow_empty=False)


def test_validate_string_rejects_non_string():
    with pytest.raises(TypeError, match="name must be a string"):
        validate_string(123, "name")


def test_validate_string_rejects_empty_when_not_allowed():
    with pytest.raises(ValueError, match="name cannot be empty"):
        validate_string("", "name", allow_empty=False)


def test_validate_string_rejects_long_string():
    with pytest.raises(ValueError, match="name cannot exceed 5 characters"):
        validate_string("abcdef", "name", max_length=5)


def test_validate_sequence_accepts_string_sequence():
    result = validate_sequence(["a", "b"], "items", str)
    assert result == ["a", "b"]


def test_validate_sequence_rejects_string_scalar():
    with pytest.raises(TypeError, match="items must be a sequence, not a string"):
        validate_sequence("abc", "items")


def test_validate_sequence_rejects_empty_when_not_allowed():
    with pytest.raises(ValueError, match="items cannot be empty"):
        validate_sequence([], "items", str, allow_empty=False)


def test_validate_columns_exist_accepts_existing_columns():
    df = pd.DataFrame({"a": [1], "b": [2]})
    validate_columns_exist(df, ["a", "b"], "columns")


def test_validate_columns_exist_rejects_missing_columns():
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match=r"columns \['b'\] not found in dataframe"):
        validate_columns_exist(df, ["b"], "columns")


def test_validate_tuple_accepts_valid_tuple():
    result = validate_tuple(("a", "b"), "items", str)
    assert result == ("a", "b")


def test_validate_tuple_rejects_non_tuple():
    with pytest.raises(TypeError, match="items must be a tuple"):
        validate_tuple(["a"], "items", str)


def test_typing_constants_are_available():
    assert "x" in ALLOWED_TARGETS
    assert DimensionsMap is not None
    assert Selector is not None
    assert SourceType is not None
