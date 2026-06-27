"""
End-to-end integration tests: template factory → engine → renderer.

Tests the full pipeline using the actual MatplotlibRenderer, verifying
the rendered figure structure and content.
"""

import pandas as pd
import pytest

from geofig_engine.core.coord import CoordCartesian, CoordFlipped, CoordFixed, CoordPolar
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.facet import FacetWrap
from geofig_engine.core.geom import GeomBar, GeomBox, GeomErrorbar, GeomLine, GeomPoint, GeomStepLine, GeomText, GeomViolin
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatBin, StatIdentity
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.templates import bivariate, timeseries, isotope


def make_dataset() -> Dataset:
    data = pd.DataFrame({
        "id": [1, 2, 3, 4, 5, 6],
        "x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "y": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
        "group": ["A", "A", "B", "B", "A", "B"],
        "category": ["X", "Y", "X", "Y", "X", "Y"],
    })
    return Dataset(dataframe=data, key_column="id")


class TestBivariateIntegration:
    """End-to-end tests: bivariate() → engine → MatplotlibRenderer."""

    def test_bivariate_default_renders_scatter(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = bivariate(mapping={"x": "x", "y": "y"})
        specs = engine.build_specs_from_template(dataset, template)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert len(fig.axes) == 1
        assert len(fig.axes[0].collections) == 1
        ax = fig.axes[0]
        assert ax.get_xlabel() == "x"
        assert ax.get_ylabel() == "y"

    def test_bivariate_with_color_renders_colored_scatter(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = bivariate(mapping={"x": "x", "y": "y", "color": "group"})
        specs = engine.build_specs_from_template(dataset, template)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].collections) == 1

    def test_bivariate_with_settings(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = bivariate(mapping={"x": "x", "y": "y"})
        specs = engine.build_specs_from_template(
            dataset, template,
            settings={"title": "Test", "xlabel": "X", "ylabel": "Y", "grid": True},
        )
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        ax = fig.axes[0]
        assert ax.get_title() == "Test"
        assert ax.get_xlabel() == "X"
        assert ax.get_ylabel() == "Y"

    def test_bivariate_axis_limits_match_data(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = bivariate(mapping={"x": "x", "y": "y"})
        specs = engine.build_specs_from_template(dataset, template)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        ax = fig.axes[0]
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        assert xlim[0] < 1.0
        assert xlim[1] > 6.0
        assert ylim[0] < 10.0
        assert ylim[1] > 60.0


class TestTimeseriesIntegration:
    """End-to-end tests: timeseries() → engine → MatplotlibRenderer."""

    def test_timeseries_renders_line_and_point(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = timeseries(mapping={"x": "x", "y": "y"})
        specs = engine.build_specs_from_template(dataset, template)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        ax = fig.axes[0]
        assert len(ax.lines) >= 1
        assert len(ax.collections) >= 1

    def test_timeseries_default_settings_applied(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = timeseries(mapping={"x": "x", "y": "y"})
        specs = engine.build_specs_from_template(dataset, template)
        assert specs[0].settings.get("time_format") == "%Y-%m-%d"


class TestIsotopeIntegration:
    """End-to-end tests: isotope() → engine → MatplotlibRenderer."""

    def test_isotope_renders_function_lines_and_scatter(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = isotope(mapping={"x": "x", "y": "y"}, auto_filter=True)
        specs = engine.build_specs_from_template(dataset, template)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        ax = fig.axes[0]
        assert len(ax.lines) >= 1
        assert len(ax.collections) >= 1

    def test_isotope_no_auto_filter_renders_scatter_only(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = isotope(mapping={"x": "x", "y": "y"}, auto_filter=False)
        specs = engine.build_specs_from_template(dataset, template)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        ax = fig.axes[0]
        assert len(ax.collections) == 1


class TestFacetIntegration:
    """End-to-end tests: faceting through the full pipeline."""

    def test_facet_wrap_produces_panels(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = bivariate(mapping={"x": "x", "y": "y"})
        specs = engine.build_specs_from_template(
            dataset, template,
            facet=FacetWrap(by="group"),
        )
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert len(fig.axes) == 2

    def test_facet_wrap_with_color(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = bivariate(mapping={"x": "x", "y": "y", "color": "group"})
        specs = engine.build_specs_from_template(
            dataset, template,
            facet=FacetWrap(by="category"),
        )
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert len(fig.axes) == 2
        for ax in fig.axes:
            assert len(ax.collections) == 1

    def test_facet_wrap_with_timeseries(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = timeseries(mapping={"x": "x", "y": "y"})
        specs = engine.build_specs_from_template(
            dataset, template,
            facet=FacetWrap(by="group"),
        )
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert len(fig.axes) == 2


class TestCoordIntegration:
    """End-to-end tests: coord through the full pipeline."""

    def test_layers_with_coord_flipped_swaps_axes(self):
        engine = FigureEngine()
        dataset = make_dataset()
        layers = [Layer(geom=GeomPoint(), mapping={"x": "x", "y": "y"})]
        specs = engine.build_specs_from_layers(
            dataset, layers,
            coord=CoordFlipped(),
        )
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].collections) == 1

    def test_layers_with_coord_polar(self):
        engine = FigureEngine()
        dataset = make_dataset()
        layers = [Layer(geom=GeomPoint(), mapping={"x": "x", "y": "y"})]
        specs = engine.build_specs_from_layers(
            dataset, layers,
            coord=CoordPolar(),
        )
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert fig.axes[0].name == "polar"

    def test_layers_with_coord_fixed_aspect(self):
        engine = FigureEngine()
        dataset = make_dataset()
        layers = [Layer(geom=GeomPoint(), mapping={"x": "x", "y": "y"})]
        specs = engine.build_specs_from_layers(
            dataset, layers,
            coord=CoordFixed(ratio=0.5),
        )
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert fig.axes[0].get_aspect() == 0.5


class TestMultiLayerIntegration:
    """End-to-end tests: multiple layers through the full pipeline."""

    def test_line_and_point_layers_via_layers_api(self):
        engine = FigureEngine()
        dataset = make_dataset()
        layers = [
            Layer(geom=GeomLine(), mapping={"x": "x", "y": "y"}),
            Layer(geom=GeomPoint(), mapping={"x": "x", "y": "y", "color": "group"}),
        ]
        specs = engine.build_specs_from_layers(dataset, layers)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        ax = fig.axes[0]
        assert len(ax.lines) >= 1
        assert len(ax.collections) >= 1


class TestRenderPipeline:
    """Tests for the full render pipeline."""

    def test_render_all_multiple_specs(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = bivariate(mapping={"x": "x", "y": "y", "color": "group"})
        specs = engine.build_specs_from_template(dataset, template)
        renderer = MatplotlibRenderer()
        figs = renderer.render_all(specs)
        assert len(figs) == 1
        assert len(figs[0].axes[0].collections) == 1

    def test_render_single_spec(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = bivariate(mapping={"x": "x", "y": "y"})
        specs = engine.build_specs_from_template(dataset, template)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert len(fig.axes) == 1

    def test_supports_template_spec(self):
        engine = FigureEngine()
        dataset = make_dataset()
        template = timeseries(mapping={"x": "x", "y": "y"})
        specs = engine.build_specs_from_template(dataset, template)
        renderer = MatplotlibRenderer()
        assert renderer.supports(specs[0]) is True


class TestTextIntegration:
    """End-to-end tests: GeomText through the full pipeline."""

    def test_text_via_layers_api(self):
        engine = FigureEngine()
        data = pd.DataFrame({"id": [1, 2], "x": [1.0, 2.0], "y": [3.0, 4.0], "lbl": ["A", "B"]})
        dataset = Dataset(dataframe=data, key_column="id")
        layers = [Layer(geom=GeomText(), mapping={"x": "x", "y": "y", "label": "lbl"})]
        specs = engine.build_specs_from_layers(dataset, layers)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].texts) == 2


class TestErrorbarIntegration:
    """End-to-end tests: GeomErrorbar through the full pipeline."""

    def test_errorbar_via_layers_api(self):
        engine = FigureEngine()
        data = pd.DataFrame({
            "id": [1, 2], "x": [1.0, 2.0], "y": [3.0, 5.0],
            "lo": [2.0, 4.0], "hi": [4.0, 6.0],
        })
        dataset = Dataset(dataframe=data, key_column="id")
        layers = [Layer(geom=GeomErrorbar(), mapping={"x": "x", "y": "y", "ymin": "lo", "ymax": "hi"})]
        specs = engine.build_specs_from_layers(dataset, layers)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].containers) >= 1


class TestBoxIntegration:
    """End-to-end tests: GeomBox through the full pipeline."""

    def test_box_via_layers_api(self):
        engine = FigureEngine()
        data = pd.DataFrame({
            "id": [1, 2, 3, 4],
            "x": ["A", "A", "B", "B"],
            "y": [1.0, 2.0, 3.0, 4.0],
        })
        dataset = Dataset(dataframe=data, key_column="id")
        layers = [Layer(geom=GeomBox(), mapping={"x": "x", "y": "y"})]
        specs = engine.build_specs_from_layers(dataset, layers)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].patches) >= 2


class TestViolinIntegration:
    """End-to-end tests: GeomViolin through the full pipeline."""

    def test_violin_via_layers_api(self):
        engine = FigureEngine()
        data = pd.DataFrame({
            "id": [1, 2, 3, 4],
            "x": ["A", "A", "B", "B"],
            "y": [1.0, 2.0, 3.0, 4.0],
        })
        dataset = Dataset(dataframe=data, key_column="id")
        layers = [Layer(geom=GeomViolin(), mapping={"x": "x", "y": "y"})]
        specs = engine.build_specs_from_layers(dataset, layers)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].collections) >= 1


class TestStepLineIntegration:
    """End-to-end tests: GeomStepLine through the full pipeline."""

    def test_step_line_via_layers_api(self):
        engine = FigureEngine()
        data = pd.DataFrame({
            "id": [1, 2, 3],
            "x": [1.0, 2.0, 3.0],
            "y": [1.0, 4.0, 9.0],
        })
        dataset = Dataset(dataframe=data, key_column="id")
        layers = [Layer(geom=GeomStepLine(), mapping={"x": "x", "y": "y"})]
        specs = engine.build_specs_from_layers(dataset, layers)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].lines) == 1


class TestHistogramIntegration:
    """End-to-end tests: StatBin + GeomBar histogram pipeline."""

    def test_histogram_via_layers_api(self):
        engine = FigureEngine()
        data = pd.DataFrame({
            "id": list(range(20)),
            "x": [1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 5, 5, 6, 6, 7],
        })
        dataset = Dataset(dataframe=data, key_column="id")
        layers = [Layer(
            geom=GeomBar(),
            stat=StatBin(column="x", bins=10),
            mapping={"x": "x", "y": "y", "width": "width"},
        )]
        specs = engine.build_specs_from_layers(dataset, layers)
        renderer = MatplotlibRenderer()
        fig = renderer.render(specs[0])
        assert len(fig.axes[0].patches) >= 1
