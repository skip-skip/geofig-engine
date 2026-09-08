"""Tests for GeomPolygon (Phase 14.59 WP3).

Covers the closed-filled-polygon geom: model validation, rendering via ax.fill,
outline/fill styling, GeomArea regression, and serialization round-trips.
"""

import numpy as np
import pandas as pd
import pytest
from matplotlib.patches import Polygon as MplPolygon

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.geom import GeomArea, GeomPolygon
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatIdentity
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.serialize.converters import geom_from_dict, geom_to_dict
from geofig_engine.serialize import spec_from_json, spec_to_json


def make_dataset() -> Dataset:
    df = pd.DataFrame({
        "x": [1.0, 2.0, 3.0, 4.0, 5.0],
        "y": [10.0, 20.0, 30.0, 40.0, 50.0],
    })
    return Dataset(dataframe=df, key_column="x")


def make_engine_and_renderer():
    return FigureEngine(), MatplotlibRenderer()


class TestGeomPolygonModel:
    def test_channels(self):
        geom = GeomPolygon()
        assert geom.name == "polygon"
        assert geom.required_channels == ("x", "y")
        assert set(geom.optional_channels) == {"color", "alpha"}

    def test_default_outline_params(self):
        geom = GeomPolygon()
        assert geom.edgecolor == "black"
        assert geom.edgealpha is None
        assert geom.edgewidth == 0.5
        assert geom.edgestyle == "-"

    def test_custom_outline_params(self):
        geom = GeomPolygon(
            edgecolor="red", edgealpha=0.2, edgewidth=2.0, edgestyle="dashed"
        )
        assert geom.edgecolor == "red"
        assert geom.edgealpha == 0.2
        assert geom.edgewidth == 2.0
        assert geom.edgestyle == "dashed"

    def test_all_valid_edge_styles(self):
        for style in ("solid", "dashed", "dashdot", "dotted", "-", "--", "-.", ":"):
            assert GeomPolygon(edgestyle=style).edgestyle == style

    def test_invalid_edgestyle_raises(self):
        with pytest.raises(ValueError, match="edgestyle"):
            GeomPolygon(edgestyle="fancy")

    def test_invalid_outline_params_raise(self):
        for kwargs in (
            {"edgecolor": ""},
            {"edgecolor": 5},
            {"edgealpha": "low"},
            {"edgealpha": True},
            {"edgewidth": 0},
            {"edgewidth": -1},
            {"edgewidth": "thick"},
        ):
            with pytest.raises(ValueError):
                GeomPolygon(**kwargs)


class TestRenderPolygon:
    def _render(self, geom=GeomPolygon(), mapping=None):
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=geom,
            stat=StatIdentity(),
            mapping=mapping if mapping is not None else {"x": "x", "y": "y"},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        return renderer.render(specs[0])

    def test_renders_closed_filled_polygon(self):
        fig = self._render()
        ax = fig.axes[0]
        assert len(ax.patches) == 1
        polygon = ax.patches[0]
        assert isinstance(polygon, MplPolygon)
        path = polygon.get_path()
        assert len(path.vertices) >= 5  # data (5) + auto-close duplicate
        assert path.vertices[0].tolist() == path.vertices[-1].tolist()

    def test_auto_closes_open_loop(self):
        # Explicitly non-closed vertices (last != first) still close the loop.
        fig = self._render(mapping={"x": "x", "y": "y"})
        ax = fig.axes[0]
        path = ax.patches[0].get_path()
        assert path.vertices[0].tolist() == path.vertices[-1].tolist()

    def test_fill_color_and_alpha_honored(self):
        fig = self._render(mapping={"x": "x", "y": "y", "color": "steelblue", "alpha": 0.5})
        ax = fig.axes[0]
        polygon = ax.patches[0]
        assert polygon.get_alpha() == 0.5
        # facecolor carries the fill alpha (matplotlib folds alpha into rgba).
        face = polygon.get_facecolor()
        assert face[:3] == pytest.approx([0.2745, 0.5098, 0.7059], abs=1e-4)
        assert face[3] == pytest.approx(0.5)

    def test_outline_color_width_style_applied(self):
        geom = GeomPolygon(edgecolor="red", edgewidth=2.5, edgestyle=":")
        fig = self._render(geom=geom, mapping={"x": "x", "y": "y"})
        ax = fig.axes[0]
        polygon = ax.patches[0]
        assert polygon.get_edgecolor()[:3] == pytest.approx([1.0, 0.0, 0.0])
        assert polygon.get_linewidth() == 2.5
        assert polygon.get_linestyle() == ":"

    def test_edgealpha_applied_to_outline(self):
        geom = GeomPolygon(edgealpha=0.25)
        fig = self._render(geom=geom, mapping={"x": "x", "y": "y"})
        ax = fig.axes[0]
        rgba = ax.patches[0].get_edgecolor()
        assert rgba[:3] == pytest.approx([0.0, 0.0, 0.0])
        assert rgba[3] == pytest.approx(0.25)

    def test_default_outline_is_black_solid_half_width(self):
        fig = self._render()
        ax = fig.axes[0]
        polygon = ax.patches[0]
        assert polygon.get_edgecolor()[:3] == pytest.approx([0.0, 0.0, 0.0])
        assert polygon.get_linewidth() == 0.5
        assert polygon.get_linestyle() == "-"

    def test_missing_channels_raises(self):
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=GeomPolygon(),
            stat=StatIdentity(),
            mapping={"x": "x"},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        with pytest.raises(ValueError, match="requires both x and y"):
            renderer.render(specs[0])

    def test_short_series_skips(self):
        engine, renderer = make_engine_and_renderer()
        df = pd.DataFrame({"x": [1.0, 2.0], "y": [1.0, 2.0]})
        dataset = Dataset(dataframe=df, key_column="x")
        layer = Layer(
            geom=GeomPolygon(),
            stat=StatIdentity(),
            mapping={"x": "x", "y": "y"},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].patches) == 0


class TestGeomAreaRegression:
    def test_area_still_renders(self):
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=GeomArea(),
            stat=StatIdentity(),
            mapping={"x": "x", "y": "y", "color": "gray"},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].collections) == 1

    def test_area_geom_unchanged(self):
        area = GeomArea()
        assert area.name == "area"
        assert area.required_channels == ("x", "y")


class TestGeomPolygonSerialization:
    def test_defaults_dict(self):
        assert geom_to_dict(GeomPolygon()) == {"type": "polygon"}

    def test_nondefaults_dict(self):
        d = geom_to_dict(
            GeomPolygon(edgecolor="red", edgealpha=0.2, edgewidth=2.0, edgestyle="--")
        )
        assert d == {
            "type": "polygon",
            "edgecolor": "red",
            "edgealpha": 0.2,
            "edgewidth": 2.0,
            "edgestyle": "--",
        }

    def test_from_dict_defaults(self):
        assert geom_from_dict({"type": "polygon"}) == GeomPolygon()

    def test_from_dict_nondefaults(self):
        restored = geom_from_dict(
            {
                "type": "polygon",
                "edgecolor": "red",
                "edgealpha": 0.2,
                "edgewidth": 2.0,
                "edgestyle": "--",
            }
        )
        assert restored == GeomPolygon(edgecolor="red", edgealpha=0.2, edgewidth=2.0, edgestyle="--")

    def test_json_round_trip_preserves_outline_params(self):
        engine, _ = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=GeomPolygon(edgecolor="blue", edgealpha=0.4, edgewidth=1.5, edgestyle="dotted"),
            stat=StatIdentity(),
            mapping={"x": "x", "y": "y"},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        restored = spec_from_json(spec_to_json(specs[0]))
        restored = restored
        geom = restored.layers[0].geom
        assert isinstance(geom, GeomPolygon)
        assert geom.edgecolor == "blue"
        assert geom.edgealpha == 0.4
        assert geom.edgewidth == 1.5
        assert geom.edgestyle == "dotted"