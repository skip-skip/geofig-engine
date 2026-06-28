"""
Tests for Phase 13 — annotation / reference layer system.

Covers GeomHSpan, GeomVSpan, GeomRect, GeomAbline, GeomText improvements,
and per-layer zorder control.
"""

import numpy as np
import pandas as pd
import pytest
from matplotlib.patches import Rectangle

from geofig_engine.core.coord import CoordPolar
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.geom import (
    Geom,
    GeomAbline,
    GeomHSpan,
    GeomRect,
    GeomText,
    GeomVSpan,
    Channel,
)
from geofig_engine.core.layer import Layer, LayerSpec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer


# ---------------------------------------------------------------------------
# Geom construction tests
# ---------------------------------------------------------------------------

class TestGeomHSpan:
    def test_defaults(self):
        g = GeomHSpan()
        assert g.name == "hspan"
        assert g.required_channels == ("ymin", "ymax")
        assert "color" in g.optional_channels
        assert "alpha" in g.optional_channels


class TestGeomVSpan:
    def test_defaults(self):
        g = GeomVSpan()
        assert g.name == "vspan"
        assert g.required_channels == ("xmin", "xmax")
        assert "color" in g.optional_channels
        assert "alpha" in g.optional_channels


class TestGeomRect:
    def test_defaults(self):
        g = GeomRect()
        assert g.name == "rect"
        assert g.required_channels == ("xmin", "xmax", "ymin", "ymax")
        assert "color" in g.optional_channels
        assert "alpha" in g.optional_channels


class TestGeomAbline:
    def test_slope_intercept(self):
        g = GeomAbline(slope=2.0, intercept=1.0)
        assert g.name == "abline"
        assert g.slope == 2.0
        assert g.intercept == 1.0
        assert g.x1 is None
        assert g.x2 is None

    def test_two_point(self):
        g = GeomAbline(x1=0, y1=0, x2=1, y2=2)
        assert g.slope is None
        assert g.x1 == 0
        assert g.y1 == 0
        assert g.x2 == 1
        assert g.y2 == 2

    def test_rejects_no_params(self):
        with pytest.raises(ValueError, match="provide either"):
            GeomAbline()

    def test_rejects_both_modes(self):
        with pytest.raises(ValueError, match="not both"):
            GeomAbline(slope=1.0, x1=0, y1=0, x2=1, y2=1)

    def test_no_required_channels(self):
        g = GeomAbline(slope=1.0, intercept=0.0)
        assert g.required_channels == ()
        assert "color" in g.optional_channels
        assert "style" in g.optional_channels


class TestGeomTextChannels:
    def test_has_angle_channel(self):
        g = GeomText()
        assert "angle" in g.optional_channels

    def test_has_bbox_channel(self):
        g = GeomText()
        assert "bbox" in g.optional_channels


# ---------------------------------------------------------------------------
# Channel enum tests
# ---------------------------------------------------------------------------

class TestChannelEnum:
    def test_xmin_and_xmax_exist(self):
        assert Channel.XMIN.value == "xmin"
        assert Channel.XMAX.value == "xmax"

    def test_angle_and_bbox_exist(self):
        assert Channel.ANGLE.value == "angle"
        assert Channel.BBOX.value == "bbox"


# ---------------------------------------------------------------------------
# Renderer integration tests (use actual MatplotlibRenderer)
# ---------------------------------------------------------------------------

def make_dataset() -> Dataset:
    df = pd.DataFrame({
        "x": [1.0, 2.0, 3.0, 4.0, 5.0],
        "y": [10.0, 20.0, 30.0, 40.0, 50.0],
    })
    return Dataset(dataframe=df, key_column="x")


def make_engine_and_renderer():
    engine = FigureEngine()
    renderer = MatplotlibRenderer()
    return engine, renderer


class TestRenderHSpan:
    def test_renders_horizontal_span(self):
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=GeomHSpan(),
            stat=StatIdentity(),
            mapping={"ymin": 15, "ymax": 25, "color": "red", "alpha": 0.3},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        fig = renderer.render(specs[0])
        ax = fig.axes[0]
        # axhspan adds a Polygon
        patches = [p for p in ax.patches if hasattr(p, "get_width")]
        assert len(ax.patches) > 0

    def test_missing_ymin_raises(self):
        layer = Layer(geom=GeomHSpan(), stat=StatIdentity(), mapping={"ymax": 10})
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        with pytest.raises(ValueError, match="requires ymin and ymax"):
            engine.build_specs_from_layers(dataset, [layer])
            renderer.render(engine.build_specs_from_layers(dataset, [layer])[0])


class TestRenderVSpan:
    def test_renders_vertical_span(self):
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=GeomVSpan(),
            stat=StatIdentity(),
            mapping={"xmin": 2, "xmax": 4, "color": "blue", "alpha": 0.2},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].patches) > 0


class TestRenderRect:
    def test_renders_rectangle(self):
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=GeomRect(),
            stat=StatIdentity(),
            mapping={"xmin": 2, "xmax": 4, "ymin": 10, "ymax": 30, "color": "green", "alpha": 0.5},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].patches) > 0

    def test_rectangle_uses_patch(self):
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=GeomRect(),
            stat=StatIdentity(),
            mapping={"xmin": 1, "xmax": 3, "ymin": 10, "ymax": 40},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        fig = renderer.render(specs[0])
        found_rect = any(isinstance(p, Rectangle) for p in fig.axes[0].patches)
        assert found_rect

    def test_missing_channels_raises(self):
        layer = Layer(geom=GeomRect(), stat=StatIdentity(), mapping={"xmin": 1, "xmax": 3})
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        with pytest.raises(ValueError, match="requires xmin"):
            specs = engine.build_specs_from_layers(dataset, [layer])
            renderer.render(specs[0])


class TestRenderAbline:
    def test_slope_intercept_renders(self):
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=GeomAbline(slope=2.0, intercept=5.0),
            stat=StatIdentity(),
            mapping={"color": "black", "style": "--"},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        fig = renderer.render(specs[0])
        ax = fig.axes[0]
        assert len(ax.lines) > 0

    def test_two_point_renders(self):
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=GeomAbline(x1=0, y1=0, x2=5, y2=25),
            stat=StatIdentity(),
            mapping={"color": "red"},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].lines) > 0

    def test_width_and_alpha(self):
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=GeomAbline(slope=1.0, intercept=0.0),
            stat=StatIdentity(),
            mapping={"width": 3, "alpha": 0.5},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].lines) > 0


class TestTextImprovements:
    def test_angle_channel_rotates_text(self):
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=GeomText(),
            stat=StatIdentity(),
            mapping={"x": "x", "y": "y", "label": "x", "angle": 45},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        fig = renderer.render(specs[0])
        texts = fig.axes[0].texts
        assert len(texts) > 0

    def test_bbox_channel_adds_box(self):
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        bbox_val = {"facecolor": "yellow", "alpha": 0.5, "pad": 5}
        layer = Layer(
            geom=GeomText(),
            stat=StatIdentity(),
            mapping={"x": "x", "y": "y", "label": "x", "bbox": bbox_val},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        fig = renderer.render(specs[0])
        texts = fig.axes[0].texts
        assert len(texts) > 0

    def test_measure_text_px(self):
        from geofig_engine.renderers.matplotlib.handlers import _measure_text_px
        w, h = _measure_text_px("Hello", 12)
        assert w > 0
        assert h > 0

    def test_measure_text_px_with_rotation(self):
        from geofig_engine.renderers.matplotlib.handlers import _measure_text_px
        w, h = _measure_text_px("Test", 10, rotation=90)
        assert w > 0
        assert h > 0


# ---------------------------------------------------------------------------
# Zorder tests
# ---------------------------------------------------------------------------

class TestLayerZorder:
    def test_layer_accepts_zorder(self):
        layer = Layer(
            geom=GeomHSpan(),
            stat=StatIdentity(),
            mapping={"ymin": 0, "ymax": 10},
            zorder=0,
        )
        assert layer.zorder == 0

    def test_layer_defaults_to_none(self):
        layer = Layer(
            geom=GeomHSpan(),
            stat=StatIdentity(),
            mapping={"ymin": 0, "ymax": 10},
        )
        assert layer.zorder is None

    def test_layer_rejects_non_int_zorder(self):
        with pytest.raises(TypeError):
            Layer(
                geom=GeomHSpan(),
                stat=StatIdentity(),
                mapping={"ymin": 0, "ymax": 10},
                zorder="foo",
            )


class TestLayerSpecZorder:
    def test_spec_preserves_zorder_from_layer(self):
        engine, _ = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=GeomHSpan(),
            stat=StatIdentity(),
            mapping={"ymin": 0, "ymax": 10},
            zorder=5,
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        assert specs[0].layers[0].zorder == 5

    def test_spec_defaults_to_none(self):
        engine, _ = make_engine_and_renderer()
        dataset = make_dataset()
        layer = Layer(
            geom=GeomHSpan(),
            stat=StatIdentity(),
            mapping={"ymin": 0, "ymax": 10},
        )
        specs = engine.build_specs_from_layers(dataset, [layer])
        assert specs[0].layers[0].zorder is None


class TestRenderZorder:
    def test_explicit_zorder_background(self):
        """Annotation with zorder=0 should render behind data layers (zorder=10)."""
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        layers = [
            Layer(
                geom=GeomHSpan(),
                stat=StatIdentity(),
                mapping={"ymin": 15, "ymax": 25, "color": "red", "alpha": 0.3},
                zorder=0,
            ),
            Layer(
                geom=GeomText(),
                stat=StatIdentity(),
                mapping={"x": "x", "y": "y", "label": "x"},
            ),
        ]
        specs = engine.build_specs_from_layers(dataset, layers)
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].patches) > 0
        assert len(fig.axes[0].texts) > 0

    def test_mixed_zorder(self):
        """Multiple annotation layers with explicit zorders render in correct order."""
        engine, renderer = make_engine_and_renderer()
        dataset = make_dataset()
        layers = [
            Layer(
                geom=GeomHSpan(),
                stat=StatIdentity(),
                mapping={"ymin": 0, "ymax": 10, "color": "red", "alpha": 0.2},
                zorder=1,
            ),
            Layer(
                geom=GeomVSpan(),
                stat=StatIdentity(),
                mapping={"xmin": 2, "xmax": 4, "color": "blue", "alpha": 0.2},
                zorder=2,
            ),
        ]
        specs = engine.build_specs_from_layers(dataset, layers)
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].patches) >= 2


# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------

class TestAnnotationSerialization:
    def test_geom_hspan_roundtrip(self):
        from geofig_engine.serialize.converters import geom_to_dict, geom_from_dict
        g = GeomHSpan()
        d = geom_to_dict(g)
        assert d["type"] == "hspan"
        g2 = geom_from_dict(d)
        assert isinstance(g2, GeomHSpan)

    def test_geom_vspan_roundtrip(self):
        from geofig_engine.serialize.converters import geom_to_dict, geom_from_dict
        g = GeomVSpan()
        d = geom_to_dict(g)
        assert d["type"] == "vspan"
        g2 = geom_from_dict(d)
        assert isinstance(g2, GeomVSpan)

    def test_geom_rect_roundtrip(self):
        from geofig_engine.serialize.converters import geom_to_dict, geom_from_dict
        g = GeomRect()
        d = geom_to_dict(g)
        assert d["type"] == "rect"
        g2 = geom_from_dict(d)
        assert isinstance(g2, GeomRect)

    def test_geom_abline_slope_roundtrip(self):
        from geofig_engine.serialize.converters import geom_to_dict, geom_from_dict
        g = GeomAbline(slope=2.0, intercept=1.0)
        d = geom_to_dict(g)
        assert d["type"] == "abline"
        assert d["slope"] == 2.0
        assert d["intercept"] == 1.0
        g2 = geom_from_dict(d)
        assert isinstance(g2, GeomAbline)
        assert g2.slope == 2.0
        assert g2.intercept == 1.0

    def test_geom_abline_two_point_roundtrip(self):
        from geofig_engine.serialize.converters import geom_to_dict, geom_from_dict
        g = GeomAbline(x1=0, y1=0, x2=1, y2=2)
        d = geom_to_dict(g)
        assert d["type"] == "abline"
        assert d["x1"] == 0
        g2 = geom_from_dict(d)
        assert isinstance(g2, GeomAbline)
        assert g2.x1 == 0
        assert g2.y1 == 0
        assert g2.x2 == 1
        assert g2.y2 == 2

    def test_zorder_roundtrip(self):
        from geofig_engine.serialize.converters import layer_spec_to_dict, layer_spec_from_dict
        from geofig_engine.core.geom import GeomHSpan
        from geofig_engine.core.stat import StatIdentity
        ls = LayerSpec(
            geom=GeomHSpan(),
            stat=StatIdentity(),
            visual_mapping={},
            zorder=5,
        )
        d = layer_spec_to_dict(ls)
        assert d["zorder"] == 5
        ls2 = layer_spec_from_dict(d)
        assert ls2.zorder == 5

    def test_zorder_none_omitted_from_serialization(self):
        from geofig_engine.serialize.converters import layer_spec_to_dict
        from geofig_engine.core.geom import GeomHSpan
        from geofig_engine.core.stat import StatIdentity
        ls = LayerSpec(
            geom=GeomHSpan(),
            stat=StatIdentity(),
            visual_mapping={},
        )
        d = layer_spec_to_dict(ls)
        assert "zorder" not in d


# ---------------------------------------------------------------------------
# Coord transform preserves zorder
# ---------------------------------------------------------------------------

class TestCoordTransformPreservesZorder:
    def test_polar_coord_preserves_zorder(self):
        engine, renderer = make_engine_and_renderer()
        df = pd.DataFrame({"cat": ["A", "B", "C"], "val": [1.0, 2.0, 3.0]})
        dataset = Dataset(dataframe=df, key_column="cat")
        layer = Layer(
            geom=GeomText(),
            stat=StatIdentity(),
            mapping={"x": "cat", "y": "val", "label": "cat"},
            zorder=42,
        )
        specs = engine.build_specs_from_layers(
            dataset, [layer],
            coord=CoordPolar(),
        )
        spec = specs[0]
        # After coord transform, zorder should still be 42
        assert spec.layers[0].zorder == 42
