"""
Tests for FigEngine renderers.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pytest

from geofig_engine.core.coord import CoordCartesian, CoordFlipped, CoordFixed, CoordPolar
from geofig_engine.core.facet import FacetGrid, FacetNull, FacetWrap
from geofig_engine.core.geom import Geom, GeomArea, GeomBar, GeomBox, GeomErrorbar, GeomFunctionLine, GeomLine, GeomPoint, GeomRibbon, GeomStepLine, GeomText, GeomViolin
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.spec import FigureSpec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.renderers import BaseRenderer, MatplotlibRenderer


class DummyRenderer(BaseRenderer):
    def render(self, spec: FigureSpec) -> str:
        return f"rendered {spec.template_name}"


def test_base_renderer_render_all():
    renderer = DummyRenderer()
    spec_a = FigureSpec(
        data=pd.DataFrame({"x": [1], "y": [2]}),
        mappings={"x": ["x"], "y": ["y"]},
        settings={},
        context={},
        template_name="a",
    )
    spec_b = FigureSpec(
        data=pd.DataFrame({"x": [3], "y": [4]}),
        mappings={"x": ["x"], "y": ["y"]},
        settings={},
        context={},
        template_name="b",
    )

    results = renderer.render_all([spec_a, spec_b])

    assert results == ["rendered a", "rendered b"]


class TestMatplotlibRendererLayerSpec:
    def test_supports_layer_spec_layers(self):
        renderer = MatplotlibRenderer()
        spec = FigureSpec(
            data=pd.DataFrame({"x": [1, 2], "y": [3, 4]}),
            mappings={},
            settings={},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": pd.Series([1, 2]), "y": pd.Series([3, 4])},
                ),
            ],
        )
        assert renderer.supports(spec) is True

    def test_supports_unknown_geom_returns_false(self):
        renderer = MatplotlibRenderer()
        spec = FigureSpec(
            data=pd.DataFrame(),
            mappings={},
            settings={},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=Geom(name="unknown_geom", required_channels=("x",)),
                    stat=StatIdentity(),
                    visual_mapping={},
                ),
            ],
        )
        assert renderer.supports(spec) is False

    def test_render_point(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"], "color": "red"},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].collections) == 1

    def test_render_line(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomLine(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].lines) == 1

    def test_render_function_line(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [0, 1, 2]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomFunctionLine(func="2 * x + 1"),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].lines) == 1

    def test_unsupported_geom_not_supported(self):
        renderer = MatplotlibRenderer()
        spec = FigureSpec(
            data=pd.DataFrame(),
            mappings={},
            settings={},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=Geom(name="unknown_geom", required_channels=("x",)),
                    stat=StatIdentity(),
                    visual_mapping={},
                ),
            ],
        )
        assert renderer.supports(spec) is False

    def test_render_point_categorical_color(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({
            "x": [1, 2, 3, 4],
            "y": [5, 6, 7, 8],
            "group": ["A", "A", "B", "B"],
        })
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"], "color": data["group"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].collections) == 1

    def test_render_point_missing_channel_raises(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"]},
                ),
            ],
        )
        with pytest.raises(ValueError, match="requires both x and y"):
            renderer.render(spec)


    def test_render_bar(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": ["A", "B", "C"], "y": [3, 5, 2]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomBar(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].containers) == 1

    def test_render_bar_missing_channel_raises(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomBar(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"]},
                ),
            ],
        )
        with pytest.raises(ValueError, match="requires both x and y"):
            renderer.render(spec)

    def test_render_bar_with_color(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": ["A", "B"], "y": [3, 5], "g": ["red", "blue"]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomBar(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"], "color": data["g"]},
                ),
            ],
        )
        fig = renderer.render(spec)

    def test_render_bar_with_width(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": ["A", "B"], "y": [3, 5]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomBar(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"], "width": pd.Series([0.5, 0.5])},
                ),
            ],
        )
        fig = renderer.render(spec)

    def test_render_area(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3], "y": [3, 5, 2]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomArea(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].collections) == 1

    def test_render_area_missing_channel_raises(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomArea(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"]},
                ),
            ],
        )
        with pytest.raises(ValueError, match="requires both x and y"):
            renderer.render(spec)

    def test_render_area_with_color(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3], "y": [3, 5, 2]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomArea(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"], "color": "steelblue"},
                ),
            ],
        )
        fig = renderer.render(spec)

    def test_render_ribbon(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3], "ymin": [2, 3, 1], "ymax": [4, 6, 3]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomRibbon(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "ymin": data["ymin"], "ymax": data["ymax"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].collections) == 1

    def test_render_ribbon_missing_channel_raises(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomRibbon(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"]},
                ),
            ],
        )
        with pytest.raises(ValueError, match="requires x, ymin, and ymax"):
            renderer.render(spec)

    def test_render_ribbon_with_color(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3], "ymin": [2, 3, 1], "ymax": [4, 6, 3]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomRibbon(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "ymin": data["ymin"], "ymax": data["ymax"], "color": "firebrick"},
                ),
            ],
        )
        fig = renderer.render(spec)


    def test_render_text(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2], "y": [3, 4], "lbl": ["A", "B"]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomText(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"], "label": data["lbl"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].texts) == 2
        assert fig.axes[0].texts[0].get_text() == "A"
        assert fig.axes[0].texts[1].get_text() == "B"

    def test_render_text_missing_channel_raises(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomText(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        with pytest.raises(ValueError, match="requires x, y, and label"):
            renderer.render(spec)

    def test_render_text_with_color(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2], "y": [3, 4], "lbl": ["A", "B"]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomText(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"], "label": data["lbl"], "color": "red"},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert fig.axes[0].texts[0].get_color() == "red"

    def test_render_errorbar(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2], "y": [3, 5], "lo": [2, 4], "hi": [4, 6]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomErrorbar(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"], "ymin": data["lo"], "ymax": data["hi"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].containers) >= 1

    def test_render_errorbar_missing_channel_raises(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2], "y": [3, 5]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomErrorbar(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        with pytest.raises(ValueError, match="requires x, y, ymin, and ymax"):
            renderer.render(spec)

    def test_render_errorbar_with_color(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2], "y": [3, 5], "lo": [2, 4], "hi": [4, 6]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomErrorbar(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"], "ymin": data["lo"], "ymax": data["hi"], "color": "blue"},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].containers) >= 1

    def test_render_box(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": ["A", "A", "B", "B"], "y": [1, 2, 3, 4]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomBox(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)

    def test_render_box_missing_channel_raises(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomBox(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"]},
                ),
            ],
        )
        with pytest.raises(ValueError, match="requires both x and y"):
            renderer.render(spec)

    def test_render_box_with_show_n(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": ["A", "A", "A", "B", "B", "B"], "y": [1, 2, 3, 4, 5, 6]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomBox(show_n=True),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].texts) == 2

    def test_render_point_with_jitter(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3, 4], "y": [1.0, 2.0, 3.0, 4.0]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(jitter=0.1),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].collections) >= 1

    def test_render_point_with_dodge_and_jitter(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({
            "x": ["A", "A", "B", "B"],
            "y": [1.0, 2.0, 3.0, 4.0],
            "g": ["X", "Y", "X", "Y"],
        })
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(jitter=0.05, dodge=0.8),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"], "color": data["g"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].collections) >= 1

    def test_render_violin(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": ["A", "A", "B", "B"], "y": [1, 2, 3, 4]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomViolin(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)

    def test_render_violin_missing_channel_raises(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomViolin(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"]},
                ),
            ],
        )
        with pytest.raises(ValueError, match="requires both x and y"):
            renderer.render(spec)

    def test_render_step_line(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomStepLine(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].lines) == 1

    def test_render_step_line_missing_channel_raises(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomStepLine(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"]},
                ),
            ],
        )
        with pytest.raises(ValueError, match="requires both x and y"):
            renderer.render(spec)

    def test_render_histogram(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 1, 2, 2, 2, 3]})
        from geofig_engine.core.stat import StatBin
        stat = StatBin(column="x", bins=3)
        stat_data = stat.compute(data)
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomBar(),
                    stat=stat,
                    visual_mapping={"x": stat_data["x"], "y": stat_data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes[0].patches) >= 1

class TestMatplotlibRendererCoord:
    def test_coord_polar(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            coord=CoordPolar(),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert fig.axes[0].name == "polar"

    def test_coord_flipped_swaps_labels(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3), "xlabel": "X", "ylabel": "Y"},
            context={},
            template_name="custom",
            coord=CoordFlipped(),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert fig.axes[0].get_xlabel() == "Y"
        assert fig.axes[0].get_ylabel() == "X"

    def test_coord_fixed_sets_aspect(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (4, 3)},
            context={},
            template_name="custom",
            coord=CoordFixed(ratio=2.0),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert fig.axes[0].get_aspect() == 2.0

    def test_supports_polar_coord(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={},
            context={},
            template_name="custom",
            coord=CoordPolar(),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": pd.Series([1, 2]), "y": pd.Series([3, 4])},
                ),
            ],
        )
        assert renderer.supports(spec) is True


class TestMatplotlibRendererFacet:
    def test_facet_wrap_point(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3, 4], "y": [5, 6, 7, 8], "g": ["A", "A", "B", "B"]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (6, 3)},
            context={},
            template_name="custom",
            facet=FacetWrap(by="g"),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes) == 2

    def test_facet_grid_point(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({
            "x": [1, 2, 3, 4],
            "y": [5, 6, 7, 8],
            "row": ["A", "A", "B", "B"],
            "col": ["X", "Y", "X", "Y"],
        })
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (6, 3)},
            context={},
            template_name="custom",
            facet=FacetGrid(row="row", col="col"),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes) == 4

    def test_facet_wrap_bar(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": ["a", "b", "c", "d"], "y": [3, 5, 2, 4], "g": ["A", "A", "B", "B"]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (6, 3)},
            context={},
            template_name="custom",
            facet=FacetWrap(by="g"),
            layers=[
                LayerSpec(
                    geom=GeomBar(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes) == 2

    def test_facet_wrap_line(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3, 4], "y": [5, 6, 7, 8], "g": ["A", "A", "B", "B"]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (6, 3)},
            context={},
            template_name="custom",
            facet=FacetWrap(by="g"),
            layers=[
                LayerSpec(
                    geom=GeomLine(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes) == 2

    def test_facet_wrap_with_function_line(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [0, 1, 2], "y": [1, 3, 5], "g": ["A", "A", "B"]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (6, 3)},
            context={},
            template_name="custom",
            facet=FacetWrap(by="g"),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
                LayerSpec(
                    geom=GeomFunctionLine(func="2*x + 1"),
                    stat=StatIdentity(),
                    visual_mapping={"color": "red", "label": "ref"},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes) == 2

    def test_facet_wrap_panel_data(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3, 4], "y": [5, 6, 7, 8], "g": ["A", "A", "B", "B"]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (6, 3)},
            context={},
            template_name="custom",
            facet=FacetWrap(by="g"),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes) == 2
        # Panel A should have 2 points, panel B should have 2 points
        for ax in fig.axes:
            n_pts = sum(len(coll.get_offsets()) for coll in ax.collections)
            assert n_pts == 2

    def test_facet_wrap_fixed_scales(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 100], "y": [50, 5], "g": ["A", "B"]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (6, 3)},
            context={},
            template_name="custom",
            facet=FacetWrap(by="g", scales="fixed"),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        xlims = [ax.get_xlim() for ax in fig.axes]
        ylims = [ax.get_ylim() for ax in fig.axes]
        assert xlims[0] == xlims[1]
        assert ylims[0] == ylims[1]

    def test_facet_wrap_free_scales(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 100], "y": [50, 5], "g": ["A", "B"]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (6, 3)},
            context={},
            template_name="custom",
            facet=FacetWrap(by="g", scales="free"),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        xlims = [ax.get_xlim() for ax in fig.axes]
        ylims = [ax.get_ylim() for ax in fig.axes]
        assert xlims[0] != xlims[1]
        assert ylims[0] != ylims[1]

    def test_facet_single_panel(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6], "g": ["A", "A", "A"]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (6, 3)},
            context={},
            template_name="custom",
            facet=FacetWrap(by="g"),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes) == 1

    def test_facet_grid_panel_labels(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({
            "x": [1, 2, 3, 4],
            "y": [5, 6, 7, 8],
            "row": ["A", "A", "B", "B"],
            "col": ["X", "Y", "X", "Y"],
        })
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (6, 3)},
            context={},
            template_name="custom",
            facet=FacetGrid(row="row", col="col"),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        assert len(fig.axes) == 4

    def test_facet_supports(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({"x": [1, 2], "y": [3, 4], "g": ["A", "B"]})
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={},
            context={},
            template_name="custom",
            facet=FacetWrap(by="g"),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": pd.Series([1, 2]), "y": pd.Series([3, 4])},
                ),
            ],
        )
        assert renderer.supports(spec) is True

    def test_facet_shared_x_suppresses_inner_ticks_2x2(self):
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({
            "x": [1, 2, 3, 4], "y": [5, 6, 7, 8],
            "row": ["A", "A", "B", "B"], "col": ["X", "Y", "X", "Y"],
        })
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={"figsize": (6, 3)},
            context={},
            template_name="custom",
            facet=FacetGrid(row="row", col="col"),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        fig = renderer.render(spec)
        # 2x2 grid: [0,0]=top-left, [0,1]=top-right, [1,0]=bottom-left, [1,1]=bottom-right
        # With sharex=True, sharey=True:
        # bottom row (indices 2,3) show x-labels; left column (indices 0,2) show y-labels
        # top row (indices 0,1) hide x-labels; right column (indices 1,3) hide y-labels
        for idx, ax in enumerate(fig.axes):
            xtl = [t.get_text() for t in ax.get_xticklabels() if t.get_text()]
            ytl = [t.get_text() for t in ax.get_yticklabels() if t.get_text()]
            if idx in (2, 3):  # bottom row
                assert len(xtl) > 0, f"axis[{idx}] should have x-labels (bottom row)"
            else:
                assert len(xtl) == 0, f"axis[{idx}] should NOT have x-labels (top row)"
            if idx in (0, 2):  # left column
                assert len(ytl) > 0, f"axis[{idx}] should have y-labels (left column)"
            else:
                assert len(ytl) == 0, f"axis[{idx}] should NOT have y-labels (right column)"
        plt.close(fig)
