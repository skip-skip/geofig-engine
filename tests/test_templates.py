"""
Tests for FigEngine template classes.
"""

import pytest
import pandas as pd

from geofig_engine.templates import (
    FigureTemplate,
    bivariate,
    timeseries,
    isotope,
    pie,
    radar,
)
from geofig_engine.core.geom import GeomPoint, GeomLine, GeomFunctionLine, GeomBar, GeomArea, GeomText
from geofig_engine.core.layer import Layer
from geofig_engine.core.coord import CoordPolar
from geofig_engine.core.stat import StatIdentity, StatSum, StatRadar
from geofig_engine.core.scale import ScaleContinuous, ScaleOrdinal
from geofig_engine.core.stat import StatIdentity


class TestFigureTemplate:
    def test_requires_at_least_one_layer(self):
        with pytest.raises(ValueError, match="at least one Layer"):
            FigureTemplate(layers=[])

    def test_requires_layer_instances(self):
        with pytest.raises(TypeError, match="Layer instances"):
            FigureTemplate(layers=["not_a_layer"])

    def test_defaults(self):
        template = FigureTemplate(layers=[Layer(geom=GeomPoint())])
        assert len(template.layers) == 1
        assert template.default_settings == {}
        assert template.coord.name == "cartesian"

    def test_custom_settings_and_coord(self):
        from geofig_engine.core.coord import CoordPolar
        template = FigureTemplate(
            layers=[Layer(geom=GeomPoint())],
            default_settings={"figsize": (8, 8)},
            coord=CoordPolar(),
        )
        assert template.default_settings["figsize"] == (8, 8)
        assert template.coord.name == "polar"


class TestBivariateFactory:
    def test_returns_template_with_geom_point(self):
        template = bivariate()
        assert isinstance(template, FigureTemplate)
        assert len(template.layers) == 1
        assert isinstance(template.layers[0].geom, GeomPoint)
        assert isinstance(template.layers[0].stat, StatIdentity)

    def test_with_mapping(self):
        mapping = {"x": "chem1", "y": "chem2", "color": "group"}
        template = bivariate(mapping=mapping)
        assert template.layers[0].mapping["x"] == "chem1"
        assert template.layers[0].mapping["color"] == "group"

    def test_with_scales(self):
        scales = {"x": ScaleContinuous(), "color": ScaleOrdinal(palette=["red", "blue"])}
        template = bivariate(scales=scales)
        assert template.layers[0].scales["x"].name == "continuous"

    def test_default_settings(self):
        template = bivariate()
        assert template.default_settings["figsize"] == (10, 6)
        assert template.default_settings["grid"] is True


class TestTimeseriesFactory:
    def test_returns_two_layers(self):
        template = timeseries()
        assert len(template.layers) == 2

    def test_first_layer_is_line(self):
        template = timeseries()
        assert isinstance(template.layers[0].geom, GeomLine)
        assert isinstance(template.layers[0].stat, StatIdentity)

    def test_second_layer_is_point(self):
        template = timeseries()
        assert isinstance(template.layers[1].geom, GeomPoint)
        assert isinstance(template.layers[1].stat, StatIdentity)

    def test_mapping_shared_across_layers(self):
        mapping = {"x": "date", "y": "value"}
        template = timeseries(mapping=mapping)
        for layer in template.layers:
            assert layer.mapping["x"] == "date"

    def test_default_settings(self):
        template = timeseries()
        assert "time_format" in template.default_settings


class TestIsotopeFactory:
    def test_default_returns_point_layer(self):
        template = isotope()
        assert isinstance(template.layers[-1].geom, GeomPoint)

    def test_with_mapping(self):
        mapping = {"x": "d18O", "y": "dD"}
        template = isotope(mapping=mapping)
        assert template.layers[-1].mapping["x"] == "d18O"

    def test_auto_filter_loads_function_layers(self):
        pytest.importorskip("geofig_engine.data")
        template = isotope(auto_filter=True)
        assert len(template.layers) >= 2
        for layer in template.layers[:-1]:
            assert isinstance(layer.geom, GeomFunctionLine)
        assert isinstance(template.layers[-1].geom, GeomPoint)

    def test_default_settings(self):
        template = isotope()
        assert template.default_settings["figsize"] == (10, 6)


class TestPieTemplate:
    def test_requires_x_and_y(self):
        with pytest.raises(ValueError, match="requires 'x'"):
            pie(mapping={"x": "cat"})
        with pytest.raises(ValueError, match="requires 'x'"):
            pie(mapping={"y": "val"})

    def test_layers_include_bar(self):
        t = pie(mapping={"x": "cat", "y": "val"})
        assert len(t.layers) == 1
        assert isinstance(t.layers[0].geom, GeomBar)
        assert isinstance(t.layers[0].stat, StatSum)

    def test_bar_layer_has_label_in_mapping(self):
        t = pie(mapping={"x": "cat", "y": "val"})
        assert "label" in t.layers[0].mapping
        assert t.layers[0].mapping["label"] == "label"

    def test_coord_is_polar(self):
        t = pie(mapping={"x": "cat", "y": "val"})
        assert isinstance(t.coord, CoordPolar)
        assert t.coord.theta == "x"

    def test_default_settings(self):
        t = pie(mapping={"x": "cat", "y": "val"})
        assert t.default_settings["figsize"] == (8, 8)
        assert t.default_settings.get("polar_tick_labels") is True


class TestRadarTemplate:
    def test_requires_x_and_y(self):
        with pytest.raises(ValueError, match="requires 'x'"):
            radar(mapping={"x": "axis"})
        with pytest.raises(ValueError, match="requires 'x'"):
            radar(mapping={"y": "val"})

    def test_layers_include_line_and_area(self):
        t = radar(mapping={"x": "axis", "y": "val"})
        assert any(isinstance(l.geom, GeomArea) for l in t.layers)
        assert any(isinstance(l.geom, GeomLine) for l in t.layers)

    def test_fill_false_omits_area(self):
        t = radar(mapping={"x": "axis", "y": "val"}, fill=False)
        assert not any(isinstance(l.geom, GeomArea) for l in t.layers)
        assert any(isinstance(l.geom, GeomLine) for l in t.layers)

    def test_coord_is_polar(self):
        t = radar(mapping={"x": "axis", "y": "val"})
        assert isinstance(t.coord, CoordPolar)
        assert t.coord.theta == "x"

    def test_default_settings(self):
        t = radar(mapping={"x": "axis", "y": "val"})
        assert t.default_settings["figsize"] == (8, 8)
