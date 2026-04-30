"""
Tests for attribute_mapping module.
"""

import pytest
import pandas as pd

from geofig_engine.core.attribute_mapping import (
    AttributeMapping,
    validate_attribute_mapping,
    resolve_source,
    ALLOWED_TARGETS,
)
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.dimension_selector import DimensionSelector


@pytest.fixture
def sample_dataset():
    """Create a sample dataset for testing."""
    df = pd.DataFrame({
        "chem1": [1.0, 2.0, 3.0],
        "chem2": [4.0, 5.0, 6.0],
        "group": ["A", "B", "A"],
    })
    dimensions = {
        "chem1": Dimension("chem1", {"analyte": True, "unit": "mg/L"}),
        "chem2": Dimension("chem2", {"analyte": True, "unit": "mg/L"}),
        "group": Dimension("group", {"role": "group"}),
    }
    return Dataset(df, "chem1", dimensions)


class TestAttributeMappingCreation:
    """Test creating AttributeMapping instances."""

    def test_create_with_string_source(self):
        """Can create mapping with string column name."""
        mapping = AttributeMapping(target="x", source="chem1")
        assert mapping.target == "x"
        assert mapping.source == "chem1"

    def test_create_with_list_source(self):
        """Can create mapping with list of column names."""
        mapping = AttributeMapping(target="color", source=["chem1", "chem2"])
        assert mapping.target == "color"
        assert mapping.source == ["chem1", "chem2"]

    def test_create_with_dimension_selector_source(self):
        """Can create mapping with DimensionSelector."""
        selector = DimensionSelector({"analyte": True})
        mapping = AttributeMapping(target="y", source=selector)
        assert mapping.target == "y"
        assert isinstance(mapping.source, DimensionSelector)

    def test_create_with_constant_source(self):
        """Can create mapping with constant value."""
        mapping = AttributeMapping(target="color", source="blue")
        assert mapping.target == "color"
        assert mapping.source == "blue"

    def test_create_with_numeric_constant(self):
        """Can create mapping with numeric constant."""
        mapping = AttributeMapping(target="alpha", source=0.8)
        assert mapping.target == "alpha"
        assert mapping.source == 0.8

    def test_frozen_dataclass(self):
        """AttributeMapping is immutable."""
        mapping = AttributeMapping(target="x", source="chem1")
        with pytest.raises(AttributeError):
            mapping.target = "y"


class TestAttributeMappingValidation:
    """Test validation of AttributeMapping."""

    def test_valid_targets(self):
        """All allowed targets are valid."""
        for target in ALLOWED_TARGETS:
            mapping = AttributeMapping(target=target, source="col")
            assert mapping.target == target

    def test_invalid_target_raises_value_error(self):
        """Invalid target raises ValueError."""
        with pytest.raises(ValueError, match="Invalid target"):
            AttributeMapping(target="invalid", source="col")

    def test_invalid_source_dict_raises_type_error(self):
        """Plain dict as source (not DimensionSelector) raises TypeError."""
        with pytest.raises(TypeError, match="must be a DimensionSelector"):
            AttributeMapping(target="x", source={"invalid": "dict"})

    def test_empty_list_source_raises_value_error(self):
        """Empty list as source raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            AttributeMapping(target="x", source=[])

    def test_non_string_list_elements_raise_type_error(self):
        """List with non-string elements raises TypeError."""
        with pytest.raises(TypeError, match="must be strings"):
            AttributeMapping(target="x", source=["chem1", 123])

    def test_explicit_validation_call(self):
        """Can call validate_attribute_mapping directly."""
        mapping = AttributeMapping(target="x", source="col")
        # Should not raise
        validate_attribute_mapping(mapping)


class TestResolveSource:
    """Test resolve_source function."""

    def test_resolve_string_returns_list(self, sample_dataset):
        """Resolving string source returns list with column name."""
        result = resolve_source("chem1", sample_dataset)
        assert result == ["chem1"]

    def test_resolve_list_returns_unchanged(self, sample_dataset):
        """Resolving list source returns list unchanged."""
        source = ["chem1", "chem2"]
        result = resolve_source(source, sample_dataset)
        assert result == ["chem1", "chem2"]

    def test_resolve_dimension_selector(self, sample_dataset):
        """Resolving DimensionSelector returns matching columns."""
        selector = DimensionSelector({"analyte": True})
        result = resolve_source(selector, sample_dataset)
        assert sorted(result) == ["chem1", "chem2"]

    def test_resolve_constant_returns_unchanged(self, sample_dataset):
        """Resolving constant returns value unchanged."""
        assert resolve_source("blue", sample_dataset) == "blue"
        assert resolve_source(0.8, sample_dataset) == 0.8
        assert resolve_source(None, sample_dataset) is None

    def test_resolve_string_as_constant_when_not_column(self, sample_dataset):
        """String that's not a column name is treated as constant."""
        result = resolve_source("not_a_column", sample_dataset)
        assert result == "not_a_column"

    def test_resolve_string_strict_mode_raises_for_non_column(self, sample_dataset):
        """Strict mode raises error for string that's not a column."""
        with pytest.raises(KeyError, match="not found"):
            resolve_source("not_a_column", sample_dataset, strict=True)

    def test_resolve_string_nonexistent_column_raises_key_error_strict(
        self, sample_dataset
    ):
        """In strict mode, resolving non-existent column raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            resolve_source("nonexistent", sample_dataset, strict=True)

    def test_resolve_list_with_missing_columns_raises_key_error(
        self, sample_dataset
    ):
        """Resolving list with missing columns raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            resolve_source(["chem1", "nonexistent"], sample_dataset)

    def test_resolve_dimension_selector_no_matches_raises_value_error(
        self, sample_dataset
    ):
        """Resolving DimensionSelector with no matches raises ValueError."""
        selector = DimensionSelector({"nonexistent_role": True})
        with pytest.raises(ValueError, match="No dimensions match"):
            resolve_source(selector, sample_dataset)


class TestAttributeMappingIntegration:
    """Test AttributeMapping in integrated workflows."""

    def test_mapping_creation_and_resolution_workflow(self, sample_dataset):
        """Full workflow: create mapping → validate → resolve."""
        # Create mapping with selector
        selector = DimensionSelector({"analyte": True})
        mapping = AttributeMapping(target="x", source=selector)

        # Validate (implicit in creation, but can be explicit)
        validate_attribute_mapping(mapping)

        # Resolve
        resolved = resolve_source(mapping.source, sample_dataset)
        assert sorted(resolved) == ["chem1", "chem2"]

    def test_multiple_mappings_in_dict(self, sample_dataset):
        """Can store multiple mappings in dict (typical usage)."""
        mappings = {
            "x": AttributeMapping("x", DimensionSelector({"analyte": True})),
            "y": AttributeMapping("y", "chem1"),
            "color": AttributeMapping("color", "blue"),
            "marker": AttributeMapping("marker", "group"),
        }

        # Resolve all
        resolved = {
            name: resolve_source(m.source, sample_dataset)
            for name, m in mappings.items()
        }

        assert sorted(resolved["x"]) == ["chem1", "chem2"]
        assert resolved["y"] == ["chem1"]
        assert resolved["color"] == "blue"
        assert resolved["marker"] == ["group"]

    def test_dataset_not_mutated_during_resolution(self, sample_dataset):
        """Resolving mappings does not mutate dataset."""
        original_columns = set(sample_dataset.dataframe.columns)
        original_shape = sample_dataset.dataframe.shape

        selector = DimensionSelector({"analyte": True})
        mapping = AttributeMapping("x", selector)
        resolve_source(mapping.source, sample_dataset)

        assert set(sample_dataset.dataframe.columns) == original_columns
        assert sample_dataset.dataframe.shape == original_shape
