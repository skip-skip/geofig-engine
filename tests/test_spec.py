"""
Tests for spec module.
"""

import pytest
import pandas as pd

from geofig_engine.core.spec import (
    FigureSpec,
    validate_figure_spec,
    build_spec,
    extract_data_for_mapping,
)


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        "x": [1, 2, 3, 4],
        "y": [10, 20, 30, 40],
        "color": ["red", "blue", "red", "blue"],
        "group": ["A", "A", "B", "B"],
    })


@pytest.fixture
def valid_mappings():
    """Create valid mappings for testing."""
    return {
        "x": ["x"],
        "y": ["y"],
        "color": "blue",  # constant
        "marker": ["group"],  # column reference
    }


@pytest.fixture
def valid_settings():
    """Create valid settings for testing."""
    return {
        "alpha": 0.8,
        "title": "Test Plot",
        "figsize": (10, 6),
    }


@pytest.fixture
def valid_context():
    """Create valid context for testing."""
    return {"analyte": "chem1", "group": "A"}


class TestFigureSpecCreation:
    """Test creating FigureSpec instances."""

    def test_create_valid_spec(
        self, sample_dataframe, valid_mappings, valid_settings, valid_context
    ):
        """Can create a valid FigureSpec."""
        spec = FigureSpec(
            data=sample_dataframe,
            mappings=valid_mappings,
            settings=valid_settings,
            context=valid_context,
            template_name="bivariate",
            iterator_key=("analyte", "group"),
        )
        assert spec.data is sample_dataframe
        assert spec.mappings == valid_mappings
        assert spec.settings == valid_settings
        assert spec.context == valid_context
        assert spec.template_name == "bivariate"
        assert spec.iterator_key == ("analyte", "group")

    def test_frozen_dataclass(self, sample_dataframe, valid_mappings):
        """FigureSpec is immutable."""
        spec = FigureSpec(
            data=sample_dataframe,
            mappings=valid_mappings,
            settings={},
            context={},
            template_name="test",
        )
        with pytest.raises(AttributeError):
            spec.data = pd.DataFrame()

    def test_default_iterator_key(self, sample_dataframe, valid_mappings):
        """iterator_key defaults to empty tuple."""
        spec = FigureSpec(
            data=sample_dataframe,
            mappings=valid_mappings,
            settings={},
            context={},
            template_name="test",
        )
        assert spec.iterator_key == ()


class TestFigureSpecValidation:
    """Test validation of FigureSpec."""

    def test_validate_valid_spec(self, sample_dataframe, valid_mappings):
        """Valid spec passes validation."""
        spec = FigureSpec(
            data=sample_dataframe,
            mappings=valid_mappings,
            settings={},
            context={},
            template_name="test",
        )
        # Should not raise
        validate_figure_spec(spec)

    def test_invalid_data_type_raises_type_error(self, valid_mappings):
        """Non-DataFrame data raises TypeError."""
        with pytest.raises(TypeError, match="data must be a pandas DataFrame"):
            FigureSpec(
                data="not a dataframe",
                mappings=valid_mappings,
                settings={},
                context={},
                template_name="test",
            )

    def test_invalid_mappings_type_raises_type_error(self, sample_dataframe):
        """Non-dict mappings raises TypeError."""
        with pytest.raises(TypeError, match="mappings must be a dict"):
            FigureSpec(
                data=sample_dataframe,
                mappings="not a dict",
                settings={},
                context={},
                template_name="test",
            )

    def test_empty_mapping_list_raises_value_error(self, sample_dataframe):
        """Empty list in mappings raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            FigureSpec(
                data=sample_dataframe,
                mappings={"x": []},
                settings={},
                context={},
                template_name="test",
            )

    def test_non_string_list_elements_raises_type_error(self, sample_dataframe):
        """Non-string elements in mapping list raises TypeError."""
        with pytest.raises(TypeError, match="must be strings"):
            FigureSpec(
                data=sample_dataframe,
                mappings={"x": ["col1", 123]},
                settings={},
                context={},
                template_name="test",
            )

    def test_plain_dict_mapping_raises_type_error(self, sample_dataframe):
        """Plain dict (not DimensionSelector) in mappings raises TypeError."""
        with pytest.raises(TypeError, match="must be a DimensionSelector"):
            FigureSpec(
                data=sample_dataframe,
                mappings={"x": {"invalid": "dict"}},
                settings={},
                context={},
                template_name="test",
            )

    def test_invalid_settings_type_raises_type_error(self, sample_dataframe, valid_mappings):
        """Non-dict settings raises TypeError."""
        with pytest.raises(TypeError, match="settings must be a dict"):
            FigureSpec(
                data=sample_dataframe,
                mappings=valid_mappings,
                settings="not a dict",
                context={},
                template_name="test",
            )

    def test_invalid_context_type_raises_type_error(self, sample_dataframe, valid_mappings):
        """Non-dict context raises TypeError."""
        with pytest.raises(TypeError, match="context must be a dict"):
            FigureSpec(
                data=sample_dataframe,
                mappings=valid_mappings,
                settings={},
                context="not a dict",
                template_name="test",
            )

    def test_empty_template_name_raises_value_error(self, sample_dataframe, valid_mappings):
        """Empty template_name raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            FigureSpec(
                data=sample_dataframe,
                mappings=valid_mappings,
                settings={},
                context={},
                template_name="",
            )

    def test_invalid_template_name_type_raises_type_error(self, sample_dataframe, valid_mappings):
        """Non-string template_name raises TypeError."""
        with pytest.raises(TypeError, match="template_name must be a string"):
            FigureSpec(
                data=sample_dataframe,
                mappings=valid_mappings,
                settings={},
                context={},
                template_name=123,
            )

    def test_invalid_iterator_key_type_raises_type_error(self, sample_dataframe, valid_mappings):
        """Non-tuple iterator_key raises TypeError."""
        with pytest.raises(TypeError, match="iterator_key must be a tuple"):
            FigureSpec(
                data=sample_dataframe,
                mappings=valid_mappings,
                settings={},
                context={},
                template_name="test",
                iterator_key="not a tuple",
            )

    def test_non_string_iterator_key_elements_raises_type_error(self, sample_dataframe, valid_mappings):
        """Non-string elements in iterator_key raises TypeError."""
        with pytest.raises(TypeError, match="must be strings"):
            FigureSpec(
                data=sample_dataframe,
                mappings=valid_mappings,
                settings={},
                context={},
                template_name="test",
                iterator_key=("col1", 123),
            )

    def test_missing_column_in_mappings_raises_value_error(self, sample_dataframe):
        """Referenced column not in data raises ValueError."""
        with pytest.raises(ValueError, match="not found in data"):
            FigureSpec(
                data=sample_dataframe,
                mappings={"x": ["nonexistent_column"]},
                settings={},
                context={},
                template_name="test",
            )


class TestBuildSpec:
    """Test build_spec factory function."""

    def test_build_spec_creates_valid_spec(
        self, sample_dataframe, valid_mappings, valid_settings, valid_context
    ):
        """build_spec creates and validates a FigureSpec."""
        spec = build_spec(
            data=sample_dataframe,
            mappings=valid_mappings,
            settings=valid_settings,
            context=valid_context,
            template_name="bivariate",
            iterator_key=("analyte",),
        )
        assert isinstance(spec, FigureSpec)
        assert spec.template_name == "bivariate"
        assert spec.iterator_key == ("analyte",)

    def test_build_spec_validates_input(self, sample_dataframe):
        """build_spec validates its inputs."""
        with pytest.raises(ValueError, match="cannot be empty"):
            build_spec(
                data=sample_dataframe,
                mappings={"x": ["x"]},
                settings={},
                context={},
                template_name="",  # invalid
            )


class TestExtractDataForMapping:
    """Test extract_data_for_mapping function."""

    def test_extract_single_column_mapping(self, sample_dataframe, valid_mappings):
        """Extract data for single column mapping."""
        spec = FigureSpec(
            data=sample_dataframe,
            mappings={"x": ["x"]},
            settings={},
            context={},
            template_name="test",
        )
        result = extract_data_for_mapping(spec, "x")
        pd.testing.assert_series_equal(result, sample_dataframe["x"])

    def test_extract_multiple_column_mapping(self, sample_dataframe):
        """Extract data for multiple column mapping."""
        spec = FigureSpec(
            data=sample_dataframe,
            mappings={"x": ["x", "y"]},
            settings={},
            context={},
            template_name="test",
        )
        result = extract_data_for_mapping(spec, "x")
        expected = pd.concat([sample_dataframe["x"], sample_dataframe["y"]], ignore_index=True)
        pd.testing.assert_series_equal(result, expected)

    def test_extract_constant_mapping(self, sample_dataframe):
        """Extract data for constant mapping."""
        spec = FigureSpec(
            data=sample_dataframe,
            mappings={"color": "blue"},
            settings={},
            context={},
            template_name="test",
        )
        result = extract_data_for_mapping(spec, "color")
        assert result == "blue"

    def test_extract_missing_mapping_returns_none(self, sample_dataframe):
        """Extract data for missing mapping returns None."""
        spec = FigureSpec(
            data=sample_dataframe,
            mappings={"x": ["x"]},
            settings={},
            context={},
            template_name="test",
        )
        result = extract_data_for_mapping(spec, "missing")
        assert result is None


class TestSpecIntegration:
    """Integration tests for FigureSpec."""

    def test_complete_spec_workflow(self, sample_dataframe):
        """Complete workflow: create → validate → extract."""
        # Create spec
        spec = build_spec(
            data=sample_dataframe,
            mappings={
                "x": ["x"],
                "y": ["y"],
                "color": "red",
                "marker": ["group"],
            },
            settings={"alpha": 0.8, "title": "Integration Test"},
            context={"analyte": "chem1", "group": "A"},
            template_name="bivariate",
            iterator_key=("analyte", "group"),
        )

        # Validate (implicit in creation)
        validate_figure_spec(spec)

        # Extract data
        x_data = extract_data_for_mapping(spec, "x")
        y_data = extract_data_for_mapping(spec, "y")
        color = extract_data_for_mapping(spec, "color")
        marker_data = extract_data_for_mapping(spec, "marker")

        # Verify
        pd.testing.assert_series_equal(x_data, sample_dataframe["x"])
        pd.testing.assert_series_equal(y_data, sample_dataframe["y"])
        assert color == "red"
        pd.testing.assert_series_equal(marker_data, sample_dataframe["group"])

    def test_spec_with_empty_dataframe(self):
        """Spec can be created with empty DataFrame."""
        empty_df = pd.DataFrame(columns=["x", "y"])
        spec = FigureSpec(
            data=empty_df,
            mappings={},  # no column references
            settings={},
            context={},
            template_name="test",
        )
        assert len(spec.data) == 0

    def test_spec_with_no_mappings(self, sample_dataframe):
        """Spec can be created with no mappings."""
        spec = FigureSpec(
            data=sample_dataframe,
            mappings={},
            settings={},
            context={},
            template_name="test",
        )
        assert spec.mappings == {}

    def test_spec_with_complex_settings(self, sample_dataframe, valid_mappings):
        """Spec can handle complex settings."""
        complex_settings = {
            "alpha": 0.8,
            "title": "Complex Plot",
            "figsize": (12, 8),
            "colors": ["red", "blue", "green"],
            "nested": {"key": "value"},
        }
        spec = FigureSpec(
            data=sample_dataframe,
            mappings=valid_mappings,
            settings=complex_settings,
            context={},
            template_name="test",
        )
        assert spec.settings == complex_settings
