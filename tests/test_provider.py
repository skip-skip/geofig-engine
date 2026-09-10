"""
Tests for the DataProvider contract (Phase 15 — interoperability M1).

Covers:
- DataProvider Protocol (runtime-checkable isinstance)
- DataFrameProvider (resolve, subset, expand, unique_values, dimensions)
- DatasetProvider (dimension labels via dimensions())
- No geodata / geochemmodel imports in the provider module
- Minimal duck-typed third-party provider passing through the Protocol
"""

import sys

import pytest
import pandas as pd

from geofig_engine.provider import (
    DataProvider,
    DataFrameProvider,
    DatasetProvider,
    _resolve_columns,
    _subset_frame,
    _expand_frame,
)
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.iterator import DimensionIterator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_df():
    return pd.DataFrame(
        {
            "analyte": ["Fe", "Mn", "Fe", "Mn"],
            "waste_type": ["FB", "FB", "RC", "RC"],
            "value": [1.0, 2.0, 3.0, 4.0],
        }
    )


@pytest.fixture
def provider(simple_df):
    return DataFrameProvider(simple_df)


@pytest.fixture
def sample_dataset():
    dims = {
        "analyte": Dimension("analyte", {"analyte": True, "role": "column"}),
        "waste_type": Dimension("waste_type", {"role": "group"}),
        "value": Dimension("value", {}),
    }
    df = pd.DataFrame(
        {
            "analyte": ["Fe", "Mn", "Fe", "Mn"],
            "waste_type": ["FB", "FB", "RC", "RC"],
            "value": [1.0, 2.0, 3.0, 4.0],
        }
    )
    return Dataset(df, "analyte", dims)


@pytest.fixture
def ds_provider(sample_dataset):
    return DatasetProvider(sample_dataset)


# ---------------------------------------------------------------------------
# 1. Runtime-checkable isinstance
# ---------------------------------------------------------------------------

class TestProtocolCheck:
    def test_dataframe_provider_is_data_provider(self, provider):
        """isinstance(frame_provider, DataProvider) holds (runtime-checkable)."""
        assert isinstance(provider, DataProvider)

    def test_dataset_provider_is_data_provider(self, ds_provider):
        assert isinstance(ds_provider, DataProvider)

    def test_plain_object_is_not_data_provider(self):
        class NotAProvider:
            pass

        assert not isinstance(NotAProvider(), DataProvider)


# ---------------------------------------------------------------------------
# 2. resolve — column name → [name]; unknown → KeyError
# ---------------------------------------------------------------------------

class TestResolve:
    def test_resolve_single_column(self, provider):
        assert provider.resolve("analyte") == ["analyte"]

    def test_resolve_returns_list(self, provider):
        result = provider.resolve("value")
        assert result == ["value"]
        assert isinstance(result, list)

    def test_resolve_unknown_column_raises_key_error(self, provider):
        with pytest.raises(KeyError):
            provider.resolve("nonexistent")

    def test_resolve_tuple_form(self, provider):
        assert provider.resolve(("column", "analyte")) == ["analyte"]

    def test_resolve_list_of_columns(self, provider):
        assert provider.resolve(["analyte", "value"]) == ["analyte", "value"]


# ---------------------------------------------------------------------------
# 3. subset — filters, returns new provider, input unchanged
# ---------------------------------------------------------------------------

class TestSubset:
    def test_subset_filters_by_exact_match(self, provider, simple_df):
        result = provider.subset(waste_type="FB")
        assert isinstance(result, DataFrameProvider)
        assert list(result.columns) == list(simple_df.columns)
        result_df = result._dataframe
        assert len(result_df) == 2
        assert all(result_df["waste_type"] == "FB")

    def test_subset_by_list(self, provider):
        result = provider.subset(waste_type=["FB", "RC"])
        assert isinstance(result, DataFrameProvider)
        assert len(result._dataframe) == 4

    def test_subset_columns_restriction(self, provider, simple_df):
        result = provider.subset(columns=["analyte", "value"], waste_type="FB")
        assert list(result.columns) == ["analyte", "value"]
        assert len(result._dataframe) == 2

    def test_subset_returns_new_provider(self, provider):
        result = provider.subset(waste_type="FB")
        assert result is not provider

    def test_subset_does_not_mutate_input(self, provider, simple_df):
        original_len = len(provider._dataframe)
        _ = provider.subset(waste_type="FB")
        assert len(provider._dataframe) == original_len
        assert list(provider._dataframe.columns) == list(simple_df.columns)

    def test_subset_multiple_filters(self, provider):
        result = provider.subset(analyte="Fe", waste_type="FB")
        assert len(result._dataframe) == 1
        assert result._dataframe.iloc[0]["value"] == 1.0


# ---------------------------------------------------------------------------
# 4. expand — None → single (frame, {}); iterators → one per combo
# ---------------------------------------------------------------------------

class TestExpand:
    def test_expand_none_returns_single_tuple(self, provider):
        result = provider.expand()
        assert len(result) == 1
        frame, ctx = result[0]
        assert isinstance(frame, pd.DataFrame)
        assert ctx == {}

    def test_expand_empty_list_returns_single(self, provider):
        result = provider.expand(iterators=[])
        assert len(result) == 1
        _, ctx = result[0]
        assert ctx == {}

    def test_expand_with_value_iterator(self, provider):
        it = DimensionIterator(
            channel="waste",
            dimensions=["waste_type"],
            mode=DimensionIterator.Mode.VALUE,
        )
        result = provider.expand(iterators=[it])
        # waste_type has 2 unique values: FB, RC
        assert len(result) == 2
        contexts = [ctx for _, ctx in result]
        assert {"waste": "FB"} in contexts
        assert {"waste": "RC"} in contexts
        # Each subset should have 2 rows
        for frame, _ in result:
            assert len(frame) == 2

    def test_expand_with_dimension_iterator(self, provider):
        # A DIMENSION-mode iterator iterates over the selected *column names*
        # (one context per column), not over unique values.
        it = DimensionIterator(
            channel="analyte_ch",
            dimensions=["analyte"],
            mode=DimensionIterator.Mode.DIMENSION,
        )
        result = provider.expand(iterators=[it])
        contexts = [ctx for _, ctx in result]
        assert {"analyte_ch": "analyte"} in contexts
        # Dimension iterators do not filter rows, so each frame should
        # have the full data set (4 rows).
        for frame, _ in result:
            assert len(frame) == 4

    def test_expand_with_multicolumn_dimension_iterator(self, provider):
        it = DimensionIterator(
            channel="ch",
            dimensions=["analyte", "value"],
            mode=DimensionIterator.Mode.DIMENSION,
        )
        result = provider.expand(iterators=[it])
        contexts = [ctx for _, ctx in result]
        assert {"ch": "analyte"} in contexts
        assert {"ch": "value"} in contexts
        assert len(result) == 2


# ---------------------------------------------------------------------------
# 5. unique_values / dimensions
# ---------------------------------------------------------------------------

class TestUniqueValues:
    def test_unique_values_sorted(self, provider):
        result = provider.unique_values("waste_type")
        assert result == ["FB", "RC"]

    def test_unique_values_numeric(self, provider):
        result = provider.unique_values("value")
        assert result == [1.0, 2.0, 3.0, 4.0]

    def test_unique_values_unknown_column_raises(self, provider):
        with pytest.raises(KeyError):
            provider.unique_values("nonexistent")

    def test_unique_values_no_nans(self):
        df = pd.DataFrame({"a": [1, None, 2, None, 3]})
        p = DataFrameProvider(df)
        assert p.unique_values("a") == [1.0, 2.0, 3.0]


class TestDimensions:
    def test_dataframe_provider_dimensions_returns_empty(self, provider):
        assert provider.dimensions("analyte") == {}

    def test_dataset_provider_dimensions_returns_labels(self, ds_provider):
        labels = ds_provider.dimensions("analyte")
        assert labels == {"analyte": True, "role": "column"}

    def test_dataset_provider_dimensions_unknown_column(self, ds_provider):
        assert ds_provider.dimensions("nonexistent") == {}

    def test_dataset_provider_dimensions_empty_labels(self, ds_provider):
        assert ds_provider.dimensions("value") == {}


# ---------------------------------------------------------------------------
# 6. DatasetProvider exposes Dataset dimension labels
# ---------------------------------------------------------------------------

class TestDatasetProvider:
    def test_from_dataset(self, sample_dataset):
        dp = DatasetProvider(sample_dataset)
        assert isinstance(dp, DataProvider)
        assert dp.columns == list(sample_dataset.dataframe.columns)

    def test_dimensions_round_trip(self, sample_dataset):
        dp = DatasetProvider(sample_dataset)
        labels = dp.dimensions("analyte")
        assert isinstance(labels, dict)
        assert labels["analyte"] is True
        assert labels["role"] == "column"

    def test_resolve_with_dimension_metadata(self, ds_provider):
        """Attribute-based selector resolves via dimension metadata."""
        result = ds_provider.resolve({"analyte": True})
        assert result == ["analyte"]

    def test_subset_preserves_dimensions(self, ds_provider):
        result = ds_provider.subset(waste_type="FB")
        assert isinstance(result, DatasetProvider)
        # Dimensions should be carried over
        labels = result.dimensions("analyte")
        assert labels == {"analyte": True, "role": "column"}


# ---------------------------------------------------------------------------
# 7. No geodata / geochemmodel imports in the provider module
# ---------------------------------------------------------------------------

class TestNoUpstreamImports:
    def test_provider_module_has_no_geodata_import(self):
        """geofig_engine.provider must not import geodata/geochemmodel."""
        mod = sys.modules.get("geofig_engine.provider")
        if mod is None:
            pytest.skip("provider module not loaded")
        source_file = mod.__file__
        assert source_file is not None
        with open(source_file) as f:
            source = f.read()
        # Only forbid actual import statements, not docstring mentions.
        assert "import geodata" not in source
        assert "from geodata" not in source
        assert "import geochemmodel" not in source
        assert "from geochemmodel" not in source

    def test_top_level_import_succeeds(self):
        """from geofig_engine.provider import DataProvider succeeds."""
        from geofig_engine.provider import DataProvider as DP  # noqa: F401
        assert DP is DataProvider


# ---------------------------------------------------------------------------
# 8. Duck-typed third-party provider (no subclassing)
# ---------------------------------------------------------------------------

class DuckProvider:
    """Minimal duck-typed provider that satisfies the Protocol without
    inheriting from DataProvider."""

    def __init__(self, dataframe: pd.DataFrame):
        self._df = dataframe.copy()

    @property
    def columns(self) -> list[str]:
        return list(self._df.columns)

    def resolve(self, selector) -> list[str]:
        if isinstance(selector, str):
            if selector not in self._df.columns:
                raise KeyError(f"Column '{selector}' not found")
            return [selector]
        raise TypeError(f"Unsupported selector: {selector!r}")

    def expand(self, iterators=None):
        return [(self._df, {})]

    def subset(self, *, columns=None, **filters):
        mask = pd.Series(True, index=self._df.index)
        for name, value in filters.items():
            mask &= self._df[name].eq(value)
        result_df = self._df.loc[mask].copy()
        if columns is not None:
            if isinstance(columns, str):
                columns = [columns]
            result_df = result_df[list(columns)]
        return DuckProvider(result_df)

    def unique_values(self, column: str):
        return sorted(self._df[column].dropna().unique().tolist())

    def dimensions(self, column: str) -> dict:
        return {}


class TestDuckTypedProvider:
    def test_duck_provider_passes_protocol_check(self):
        """A duck-typed third-party provider passes isinstance."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        duck = DuckProvider(df)
        assert isinstance(duck, DataProvider)

    def test_duck_provider_resolve(self):
        df = pd.DataFrame({"a": [1], "b": [2]})
        duck = DuckProvider(df)
        assert duck.resolve("a") == ["a"]

    def test_duck_provider_expand(self):
        df = pd.DataFrame({"a": [1], "b": [2]})
        duck = DuckProvider(df)
        result = duck.expand()
        assert len(result) == 1
        assert result[0][1] == {}

    def test_duck_provider_unique_values(self):
        df = pd.DataFrame({"x": [1, 2, 2, 3]})
        duck = DuckProvider(df)
        assert duck.unique_values("x") == [1, 2, 3]

    def test_duck_provider_subset(self):
        df = pd.DataFrame({"x": [1, 2], "y": ["a", "b"]})
        duck = DuckProvider(df)
        sub = duck.subset(y="a")
        assert len(sub._df) == 1
        assert sub._df.iloc[0]["x"] == 1
