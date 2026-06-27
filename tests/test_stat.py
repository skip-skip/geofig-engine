import numpy as np
import pandas as pd
import pytest

from geofig_engine.core.stat import (
    Stat,
    StatIdentity,
    StatFn,
    StatBin,
    StatCount,
    StatSmooth,
    StatSum,
    StatPieLabels,
    StatRadar,
)


class TestStatBase:
    def test_requires_non_empty_name(self):
        with pytest.raises(ValueError, match="non-empty string"):
            Stat(name="")

    def test_requires_dict_params(self):
        with pytest.raises(TypeError, match="params must be a dict"):
            Stat(name="test", params="not a dict")

    def test_compute_not_implemented(self):
        stat = Stat(name="abstract")
        with pytest.raises(NotImplementedError):
            stat.compute(pd.DataFrame())


class TestStatIdentity:
    def test_name(self):
        assert StatIdentity().name == "identity"

    def test_returns_same_dataframe(self):
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        result = StatIdentity().compute(df)
        assert result is df


class TestStatFn:
    def test_name(self):
        assert StatFn().name == "fn"

    def test_with_func(self):
        df = pd.DataFrame({"x": [1, 2]})
        result = StatFn(func=lambda d: d.assign(y=d["x"] * 2)).compute(df)
        assert list(result["y"]) == [2, 4]

    def test_without_func_returns_data(self):
        df = pd.DataFrame({"x": [1]})
        result = StatFn().compute(df)
        assert result is df


class TestStatBin:
    def test_default_params(self):
        s = StatBin()
        assert s.params["bins"] == 10
        assert s.name == "bin"


class TestStatCount:
    def test_name(self):
        assert StatCount().name == "count"


class TestStatSmooth:
    def test_default_params(self):
        s = StatSmooth()
        assert s.params["method"] == "loess"
        assert s.params["span"] == 0.75


class TestStatSum:
    def test_sum_basic(self):
        df = pd.DataFrame({"cat": ["a", "a", "b"], "val": [1, 2, 5]})
        s = StatSum(column="val", group="cat")
        result = s.compute(df)
        assert "x" in result.columns
        assert "y" in result.columns
        assert "width" in result.columns
        assert "label" in result.columns
        assert result["label"].tolist() == ["b", "a"]
        assert result["y"].tolist() == [5, 3]

    def test_sum_angles_sum_to_2pi(self):
        df = pd.DataFrame({"cat": ["a", "b", "c"], "val": [1, 2, 3]})
        s = StatSum(column="val", group="cat")
        result = s.compute(df)
        assert abs(result["width"].sum() - 2 * np.pi) < 1e-10

    def test_sum_missing_column_returns_data(self):
        df = pd.DataFrame({"x": [1, 2]})
        s = StatSum(column="val", group="cat")
        result = s.compute(df)
        assert result is df


class TestStatPieLabels:
    def test_show_percent(self):
        df = pd.DataFrame({"cat": ["a", "b"], "val": [1, 3]})
        s = StatPieLabels(column="val", group="cat", show_percent=True, show_count=False)
        result = s.compute(df)
        assert "x" in result.columns
        assert "y" in result.columns
        assert "label_text" in result.columns
        assert "25.0%" in result["label_text"].iloc[0] or "75.0%" in result["label_text"].iloc[0]

    def test_show_count_and_percent(self):
        df = pd.DataFrame({"cat": ["a", "b"], "val": [1, 3]})
        s = StatPieLabels(column="val", group="cat", show_percent=True, show_count=True)
        result = s.compute(df)
        assert "(" in result["label_text"].iloc[0]

    def test_missing_column_returns_data(self):
        df = pd.DataFrame({"x": [1, 2]})
        s = StatPieLabels(column="val", group="cat")
        result = s.compute(df)
        assert result is df


class TestStatRadar:
    def test_radar_basic(self):
        df = pd.DataFrame({"x": ["A", "B", "C"], "y": [1, 2, 3]})
        s = StatRadar()
        result = s.compute(df)
        assert "x" in result.columns
        assert "y" in result.columns
        assert len(result) > 3

    def test_radar_closes_polygon(self):
        df = pd.DataFrame({"x": ["A", "B", "C"], "y": [1, 2, 3]})
        s = StatRadar()
        result = s.compute(df)
        assert result["x"].iloc[-1] == result["x"].iloc[0] + 2 * np.pi

    def test_normalises_to_zero_one(self):
        df = pd.DataFrame({"x": ["A", "B"], "y": [10, 20]})
        s = StatRadar()
        result = s.compute(df)
        assert result["y"].max() <= 1.0
        assert result["y"].min() >= 0.0

    def test_missing_column_returns_data(self):
        df = pd.DataFrame({"a": [1, 2]})
        s = StatRadar()
        result = s.compute(df)
        assert result is df
