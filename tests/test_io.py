import math

import numpy as np
import pandas as pd
import pytest

from geofig_engine.io import haversine, path_distance, gen_markers, gen_markers_series, Pipeline, PipelineStep
from geofig_engine.io.markers import gen_markers_cross_grouping, DEFAULT_MARKERS, DEFAULT_PALETTE


class TestHaversine:
    def test_known_distance(self):
        d = haversine(0, 0, 0, 1)
        assert abs(d - 111.195) < 0.1

    def test_same_point_returns_zero(self):
        d = haversine(-73.9, 40.7, -73.9, 40.7)
        assert abs(d) < 1e-6

    def test_antipodal(self):
        d = haversine(0, 0, 180, 0)
        assert abs(d - 20015) < 10

    def test_series_input(self):
        lon = pd.Series([0.0, 0.0])
        lat = pd.Series([0.0, 1.0])
        d = haversine(lon.iloc[0], lat.iloc[0], lon.iloc[1], lat.iloc[1])
        assert abs(d - 111.195) < 0.1


class TestPathDistance:
    def test_single_point_zero(self):
        d = path_distance(pd.Series([0.0]), pd.Series([0.0]))
        assert d.iloc[0] == 0.0

    def test_two_points(self):
        d = path_distance(pd.Series([0.0, 0.0]), pd.Series([0.0, 1.0]))
        assert abs(d.iloc[1] - 111.195) < 0.1
        assert d.iloc[0] == 0.0

    def test_cumulative_false(self):
        d = path_distance(pd.Series([0.0, 0.0, 0.0]), pd.Series([0.0, 1.0, 2.0]), cumulative=False)
        assert abs(d.iloc[1] - 111.195) < 0.1
        assert abs(d.iloc[2] - 111.195) < 0.1
        assert d.iloc[0] == 0.0

    def test_cumulative_true(self):
        d = path_distance(pd.Series([0.0, 0.0, 0.0]), pd.Series([0.0, 1.0, 2.0]), cumulative=True)
        assert abs(d.iloc[2] - 2 * 111.195) < 0.2
        assert d.iloc[0] == 0.0


class TestGenMarkers:
    def test_returns_dict(self):
        result = gen_markers(["A", "B", "C"])
        assert isinstance(result, dict)
        assert set(result.keys()) == {"A", "B", "C"}

    def test_each_entry_has_marker_and_color(self):
        result = gen_markers(["A", "B"])
        for v in ("A", "B"):
            assert "marker" in result[v]
            assert "color" in result[v]

    def test_cycles(self):
        result = gen_markers(["x", "y"], markers=("o",), palette=("#a", "#b"))
        assert result["x"]["marker"] == "o"
        assert result["x"]["color"] == "#a"
        assert result["y"]["marker"] == "o"
        assert result["y"]["color"] == "#b"


class TestGenMarkersSeries:
    def test_returns_series(self):
        s = pd.Series(["A", "B"], name="g")
        result = gen_markers_series(s)
        assert isinstance(result, pd.Series)
        assert result.name == "g"
        assert len(result) == 2


class TestGenMarkersCrossGrouping:
    def test_returns_nested_dict(self):
        result = gen_markers_cross_grouping(["a", "b"], ["x", "y"])
        assert result["a"]["x"]["marker"]
        assert result["a"]["x"]["color"]
        assert result["b"]["y"]["marker"]

    def test_all_entries_have_marker_and_color(self):
        result = gen_markers_cross_grouping(["a", "b"], ["x", "y"])
        for g1 in ("a", "b"):
            for g2 in ("x", "y"):
                assert "marker" in result[g1][g2]
                assert "color" in result[g1][g2]

    def test_distinct_combinations(self):
        result = gen_markers_cross_grouping(["a", "b"], ["x", "y"])
        combos = {(result[g1][g2]["marker"], result[g1][g2]["color"]) for g1 in ("a", "b") for g2 in ("x", "y")}
        assert len(combos) == 4


class TestPipeline:
    def test_empty_pipeline_returns_unchanged(self):
        p = Pipeline()
        df = pd.DataFrame({"x": [1, 2, 3]})
        result = p.run(df)
        assert result is df

    def test_single_step(self):
        p = Pipeline()
        p.add("double", lambda d, **kw: d * 2)
        df = pd.DataFrame({"x": [1, 2]})
        result = p.run(df)
        assert result["x"].tolist() == [2, 4]

    def test_multiple_steps_chain(self):
        p = Pipeline()
        p.add("add_one", lambda d, **kw: d + 1)
        p.add("double", lambda d, **kw: d * 2)
        df = pd.DataFrame({"x": [1, 2]})
        result = p.run(df)
        assert result["x"].tolist() == [4, 6]

    def test_steps_property(self):
        p = Pipeline()
        p.add("step1", lambda d, **kw: d)
        p.add("step2", lambda d, **kw: d)
        assert len(p.steps) == 2
        assert p.steps[0].name == "step1"
        assert p.steps[1].name == "step2"

    def test_constructor_accepts_steps(self):
        step = PipelineStep(name="init", func=lambda d, **kw: d)
        p = Pipeline(steps=[step])
        assert len(p.steps) == 1

    def test_kwargs_passed_to_func(self):
        def multiply(df, **kw):
            return df * kw["factor"]
        p = Pipeline()
        p.add("mult", multiply, factor=3)
        df = pd.DataFrame({"x": [1, 2]})
        result = p.run(df)
        assert result["x"].tolist() == [3, 6]


class TestConstants:
    def test_default_markers(self):
        assert len(DEFAULT_MARKERS) == 12
        assert "o" in DEFAULT_MARKERS

    def test_default_palette(self):
        assert len(DEFAULT_PALETTE) == 10
        assert DEFAULT_PALETTE[0] == "#1f77b4"

    def test_io_exports(self):
        from geofig_engine.io import __all__
        assert "haversine" in __all__
        assert "path_distance" in __all__
        assert "gen_markers" in __all__
        assert "gen_markers_series" in __all__
        assert "Pipeline" in __all__
        assert "PipelineStep" in __all__
