"""
Tests for iterator module.
"""

import pytest
import pandas as pd

from geofig_engine.core.iterator import (
    ColumnSelector,
    IteratorContext,
    IteratorResult,
    expand,
    get_iterator_columns,
    generate_contexts,
    filter_by_context,
)
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.dimension_selector import DimensionSelector


@pytest.fixture
def sample_dataset():
    """Create a sample dataset for testing."""
    df = pd.DataFrame({
        "analyte": ["chem1", "chem2", "chem1", "chem2"],
        "group": ["A", "A", "B", "B"],
        "value": [1.0, 2.0, 3.0, 4.0],
    })
    dimensions = {
        "analyte": Dimension("analyte", {"analyte": True}),
        "group": Dimension("group", {"role": "group"}),
        "value": Dimension("value", {}),
    }
    return Dataset(df, "analyte", dimensions)


class TestIteratorContext:
    """Test IteratorContext dataclass."""

    def test_create_context_with_values(self):
        """Can create context with values."""
        ctx = IteratorContext({"analyte": "chem1", "group": "A"})
        assert ctx.values == {"analyte": "chem1", "group": "A"}

    def test_create_empty_context(self):
        """Can create empty context."""
        ctx = IteratorContext({})
        assert ctx.values == {}

    def test_get_existing_value(self):
        """get() returns existing value."""
        ctx = IteratorContext({"key": "value"})
        assert ctx.get("key") == "value"

    def test_get_missing_value_returns_default(self):
        """get() returns default for missing key."""
        ctx = IteratorContext({})
        assert ctx.get("missing") is None
        assert ctx.get("missing", "default") == "default"

    def test_frozen_dataclass(self):
        """IteratorContext is immutable."""
        ctx = IteratorContext({"key": "value"})
        with pytest.raises(AttributeError):
            ctx.values = {}

    def test_repr_empty_context(self):
        """repr() for empty context."""
        ctx = IteratorContext({})
        assert "empty" in repr(ctx).lower()

    def test_repr_with_values(self):
        """repr() shows values."""
        ctx = IteratorContext({"analyte": "chem1"})
        assert "chem1" in repr(ctx)


class TestIteratorResult:
    """Test IteratorResult dataclass."""

    def test_create_result(self, sample_dataset):
        """Can create IteratorResult."""
        ctx = IteratorContext({"analyte": "chem1"})
        result = IteratorResult(
            subset_df=sample_dataset.dataframe,
            context=ctx,
            iterator_key=("analyte",),
        )
        assert result.context == ctx
        assert result.iterator_key == ("analyte",)
        assert len(result.subset_df) > 0

    def test_frozen_dataclass(self, sample_dataset):
        """IteratorResult is immutable."""
        ctx = IteratorContext({})
        result = IteratorResult(
            subset_df=sample_dataset.dataframe,
            context=ctx,
            iterator_key=(),
        )
        with pytest.raises(AttributeError):
            result.context = None


class TestExpand:
    """Test expand() function."""

    def test_expand_empty_selectors_returns_full_dataset(self, sample_dataset):
        """Empty selectors returns single result with full dataset."""
        results = expand(sample_dataset, {})
        assert len(results) == 1
        assert len(results[0].subset_df) == 4
        assert results[0].context.values == {}

    def test_expand_single_string_selector(self, sample_dataset):
        """Single string selector expands correctly."""
        results = expand(sample_dataset, {"analyte": "analyte"})
        assert len(results) == 2  # chem1, chem2
        values = [r.context.get("analyte") for r in results]
        assert set(values) == {"chem1", "chem2"}

    def test_expand_dimension_selector(self, sample_dataset):
        """DimensionSelector selector expands correctly."""
        selector = DimensionSelector({"analyte": True})
        results = expand(sample_dataset, {"analyte": selector})
        assert len(results) == 2
        values = [r.context.get("analyte") for r in results]
        assert set(values) == {"chem1", "chem2"}

    def test_expand_cartesian_product(self, sample_dataset):
        """Multiple selectors create Cartesian product."""
        results = expand(
            sample_dataset,
            {"analyte": "analyte", "group": "group"},
        )
        assert len(results) == 4  # 2 analytes × 2 groups
        combinations = [
            (r.context.get("analyte"), r.context.get("group"))
            for r in results
        ]
        assert set(combinations) == {
            ("chem1", "A"),
            ("chem1", "B"),
            ("chem2", "A"),
            ("chem2", "B"),
        }

    def test_expand_subset_accuracy(self, sample_dataset):
        """Each subset contains correct rows."""
        results = expand(
            sample_dataset,
            {"analyte": "analyte"},
        )
        for result in results:
            analyte = result.context.get("analyte")
            assert all(result.subset_df["analyte"] == analyte)

    def test_expand_deterministic_ordering(self, sample_dataset):
        """expand() returns results in deterministic order."""
        results1 = expand(sample_dataset, {"analyte": "analyte", "group": "group"})
        results2 = expand(sample_dataset, {"analyte": "analyte", "group": "group"})
        
        contexts1 = [r.context.values for r in results1]
        contexts2 = [r.context.values for r in results2]
        assert contexts1 == contexts2

    def test_expand_selector_order_independent(self, sample_dataset):
        """Selector insertion order does not affect expansion results."""
        results1 = expand(sample_dataset, {"group": "group", "analyte": "analyte"})
        results2 = expand(sample_dataset, {"analyte": "analyte", "group": "group"})

        assert [r.context.values for r in results1] == [r.context.values for r in results2]

    def test_expand_invalid_column_raises_key_error(self, sample_dataset):
        """Invalid column name raises KeyError."""
        with pytest.raises(KeyError):
            expand(sample_dataset, {"invalid": "nonexistent_column"})

    def test_expand_dimension_selector_no_match_raises_error(self, sample_dataset):
        """DimensionSelector with no matches raises ValueError."""
        selector = DimensionSelector({"nonexistent": True})
        with pytest.raises(ValueError):
            expand(sample_dataset, {"invalid": selector})

    def test_expand_column_selector_iterates_column_names(self, sample_dataset):
        """ColumnSelector iterates over column names rather than values."""
        selector = ColumnSelector(["analyte"])
        results = expand(sample_dataset, {"y": selector})

        assert len(results) == 1
        assert results[0].context.get("y") == "analyte"
        assert results[0].subset_df.equals(sample_dataset.dataframe)


class TestGetIteratorColumns:
    """Test get_iterator_columns() function."""

    def test_resolve_string_selector(self, sample_dataset):
        """String selector resolves to single column."""
        result = get_iterator_columns(sample_dataset, {"col": "analyte"})
        assert result == {"col": ["analyte"]}

    def test_resolve_list_selector(self, sample_dataset):
        """List selector resolves unchanged."""
        result = get_iterator_columns(
            sample_dataset,
            {"cols": ["analyte", "group"]},
        )
        assert result == {"cols": ["analyte", "group"]}

    def test_resolve_dimension_selector(self, sample_dataset):
        """DimensionSelector resolves to matching columns."""
        selector = DimensionSelector({"analyte": True})
        result = get_iterator_columns(sample_dataset, {"sel": selector})
        assert result == {"sel": ["analyte"]}

    def test_resolve_column_selector(self, sample_dataset):
        """ColumnSelector resolves explicit columns."""
        selector = ColumnSelector(["analyte", "group"])
        result = get_iterator_columns(sample_dataset, {"cols": selector})
        assert result == {"cols": ["analyte", "group"]}

    def test_resolve_multiple_selectors(self, sample_dataset):
        """Multiple selectors resolve correctly."""
        result = get_iterator_columns(
            sample_dataset,
            {
                "a": "analyte",
                "g": "group",
            },
        )
        assert result == {"a": ["analyte"], "g": ["group"]}

    def test_invalid_column_raises_key_error(self, sample_dataset):
        """Invalid column raises KeyError."""
        with pytest.raises(KeyError):
            get_iterator_columns(sample_dataset, {"invalid": "nonexistent"})

    def test_invalid_list_with_missing_column(self, sample_dataset):
        """List with missing columns raises KeyError."""
        with pytest.raises(KeyError):
            get_iterator_columns(
                sample_dataset,
                {"cols": ["analyte", "nonexistent"]},
            )


class TestGenerateContexts:
    """Test generate_contexts() function."""

    def test_generate_single_column_contexts(self, sample_dataset):
        """Single column generates one context per unique value."""
        iterator_columns = {"analyte": ["analyte"]}
        contexts = generate_contexts(sample_dataset, iterator_columns)
        assert len(contexts) == 2
        values = [c.get("analyte") for c in contexts]
        assert set(values) == {"chem1", "chem2"}

    def test_generate_cartesian_product(self, sample_dataset):
        """Multiple columns generate Cartesian product."""
        iterator_columns = {
            "analyte": ["analyte"],
            "group": ["group"],
        }
        contexts = generate_contexts(sample_dataset, iterator_columns)
        assert len(contexts) == 4
        combinations = [
            (c.get("analyte"), c.get("group"))
            for c in contexts
        ]
        assert set(combinations) == {
            ("chem1", "A"),
            ("chem1", "B"),
            ("chem2", "A"),
            ("chem2", "B"),
        }

    def test_generate_deterministic_ordering(self, sample_dataset):
        """Contexts are generated in sorted order."""
        iterator_columns = {
            "analyte": ["analyte"],
            "group": ["group"],
        }
        contexts1 = generate_contexts(sample_dataset, iterator_columns)
        contexts2 = generate_contexts(sample_dataset, iterator_columns)
        
        values1 = [c.values for c in contexts1]
        values2 = [c.values for c in contexts2]
        assert values1 == values2


class TestFilterByContext:
    """Test filter_by_context() function."""

    def test_filter_single_column(self, sample_dataset):
        """Filter by single column value."""
        ctx = IteratorContext({"analyte": "chem1"})
        filtered = filter_by_context(
            sample_dataset.dataframe,
            ctx,
            [["analyte"]],
        )
        assert len(filtered) == 2
        assert all(filtered["analyte"] == "chem1")

    def test_filter_multiple_columns(self, sample_dataset):
        """Filter by multiple column values."""
        ctx = IteratorContext({"analyte": "chem1", "group": "A"})
        filtered = filter_by_context(
            sample_dataset.dataframe,
            ctx,
            [["analyte"], ["group"]],
        )
        assert len(filtered) == 1
        assert filtered["analyte"].iloc[0] == "chem1"
        assert filtered["group"].iloc[0] == "A"

    def test_filter_preserves_all_columns(self, sample_dataset):
        """Filtering preserves all original columns."""
        ctx = IteratorContext({"analyte": "chem1"})
        filtered = filter_by_context(
            sample_dataset.dataframe,
            ctx,
            [["analyte"]],
        )
        assert set(filtered.columns) == {"analyte", "group", "value"}


class TestDatasetPreservation:
    """Test that original dataset is never mutated."""

    def test_expand_does_not_mutate_dataset(self, sample_dataset):
        """expand() doesn't mutate original dataset."""
        original_shape = sample_dataset.dataframe.shape
        original_columns = list(sample_dataset.dataframe.columns)
        
        expand(
            sample_dataset,
            {"analyte": "analyte", "group": "group"},
        )
        
        assert sample_dataset.dataframe.shape == original_shape
        assert list(sample_dataset.dataframe.columns) == original_columns

    def test_expand_result_subsets_are_views(self, sample_dataset):
        """Result subsets are independent of original."""
        results = expand(sample_dataset, {"analyte": "analyte"})
        
        for result in results:
            # Subsets should have subset of rows
            assert len(result.subset_df) <= len(sample_dataset.dataframe)


class TestIntegration:
    """Integration tests."""

    def test_expand_with_multiple_value_columns(self):
        """Works with multiple columns with same values."""
        df = pd.DataFrame({
            "group_a": ["X", "Y", "X"],
            "group_b": ["X", "Y", "X"],
            "value": [1, 2, 3],
        })
        dimensions = {
            "group_a": Dimension("group_a", {}),
            "group_b": Dimension("group_b", {}),
            "value": Dimension("value", {}),
        }
        dataset = Dataset(df, "group_a", dimensions)
        
        results = expand(
            dataset,
            {"groups": ["group_a", "group_b"]},
        )
        # Should have X and Y from both columns
        assert len(results) == 2

    def test_full_workflow(self, sample_dataset):
        """Full expansion workflow."""
        # Define what to iterate over
        selectors = {
            "analyte": DimensionSelector({"analyte": True}),
            "group": "group",
        }
        
        # Expand
        results = expand(sample_dataset, selectors)
        
        # Verify
        assert len(results) == 4
        for result in results:
            # Each has correct context
            assert result.context.get("analyte") in {"chem1", "chem2"}
            assert result.context.get("group") in {"A", "B"}
            # Each has correct subset
            analyte = result.context.get("analyte")
            group = result.context.get("group")
            assert all(result.subset_df["analyte"] == analyte)
            assert all(result.subset_df["group"] == group)
