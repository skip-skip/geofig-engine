import pandas as pd
import pytest

from geofig_engine.core.stat import (
    Stat,
    StatIdentity,
    StatFn,
    StatBin,
    StatCount,
    StatSmooth,
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
