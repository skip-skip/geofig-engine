import pandas as pd
import pytest

from geofig_engine.core.facet import Facet, FacetNull, FacetWrap, FacetGrid
from geofig_engine.core.dataset import Dataset


SIMPLE_DATA = pd.DataFrame({
    "x": [1, 2, 3, 4],
    "y": [5, 6, 7, 8],
    "group": ["A", "A", "B", "B"],
    "type": ["X", "Y", "X", "Y"],
})


def make_dataset(df: pd.DataFrame = SIMPLE_DATA) -> Dataset:
    return Dataset(dataframe=df, key_column="x")


class TestFacetBase:
    def test_requires_non_empty_name(self):
        with pytest.raises(ValueError, match="non-empty string"):
            Facet(name="")

    def test_invalid_scales_raises(self):
        with pytest.raises(ValueError, match="Invalid scales"):
            Facet(name="test", scales="invalid")

    def test_valid_scales(self):
        for scales in ("fixed", "free", "free_x", "free_y"):
            f = Facet(name="test", scales=scales)
            assert f.scales == scales


class TestFacetNull:
    def test_name(self):
        assert FacetNull().name == "null"

    def test_split_returns_single_unchanged(self):
        dataset = make_dataset()
        results = FacetNull().split(dataset)
        assert len(results) == 1
        df, ctx = results[0]
        assert len(df) == 4
        assert ctx == {}


class TestFacetWrap:
    def test_name(self):
        f = FacetWrap(by="group")
        assert f.name == "wrap"

    def test_accepts_string_by(self):
        f = FacetWrap(by="group")
        assert f.by == ("group",)

    def test_accepts_sequence_by(self):
        f = FacetWrap(by=("group", "type"))
        assert f.by == ("group", "type")

    def test_split_by_single_column(self):
        dataset = make_dataset()
        results = FacetWrap(by="group").split(dataset)
        assert len(results) == 2
        groups = set()
        for df, ctx in results:
            groups.add(ctx["group"])
            assert list(df["group"].unique()) == [ctx["group"]]
        assert groups == {"A", "B"}

    def test_split_with_empty_by(self):
        dataset = make_dataset()
        results = FacetWrap(by=()).split(dataset)
        assert len(results) == 1
        assert len(results[0][0]) == 4

    def test_ncol_nrow_default(self):
        f = FacetWrap(by="group")
        assert f.params["ncol"] == 0
        assert f.params["nrow"] == 0


class TestFacetGrid:
    def test_name(self):
        f = FacetGrid(row="group", col="type")
        assert f.name == "grid"

    def test_split_returns_all_combinations(self):
        dataset = make_dataset()
        results = FacetGrid(row="group", col="type").split(dataset)
        assert len(results) == 4
        combos = {(r["group"], r["type"]) for _, r in results}
        assert combos == {("A", "X"), ("A", "Y"), ("B", "X"), ("B", "Y")}

    def test_params(self):
        f = FacetGrid(row="group", col="type")
        assert f.params["row"] == "group"
        assert f.params["col"] == "type"
