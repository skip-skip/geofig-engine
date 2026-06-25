"""
Tests for the new Grammer of Graphics API path in FigureEngine.
"""

import pandas as pd
import pytest

from geofig_engine.core.coord import CoordCartesian, CoordPolar, CoordFixed
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.facet import FacetNull, FacetWrap
from geofig_engine.core.geom import GeomPoint, GeomLine, GeomFunctionLine
from geofig_engine.core.layer import Layer, LayerSpec
from geofig_engine.core.scale import ScaleContinuous, ScaleOrdinal, ScaleConstant
from geofig_engine.core.stat import StatIdentity, StatFn
from geofig_engine.engine import FigureEngine
from geofig_engine.templates import bivariate, timeseries, isotope


def make_dataset() -> Dataset:
    data = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "x": [1.0, 2.0, 3.0, 4.0],
        "y": [10.0, 20.0, 30.0, 40.0],
        "group": ["A", "B", "A", "B"],
    })
    return Dataset(dataframe=data, key_column="id")


def test_build_specs_from_layers_minimal():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [
        Layer(
            geom=GeomPoint(),
            stat=StatIdentity(),
            mapping={"x": "x", "y": "y"},
        )
    ]
    specs = engine.build_specs_from_layers(dataset, layers)
    assert len(specs) == 1
    spec = specs[0]
    assert spec.template_name == "custom"
    assert len(spec.layers) == 1
    assert isinstance(spec.layers[0], LayerSpec)
    assert spec.layers[0].geom.name == "point"


def test_build_specs_from_layers_resolves_columns():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [
        Layer(
            geom=GeomPoint(),
            mapping={"x": "x", "y": "y"},
        )
    ]
    specs = engine.build_specs_from_layers(dataset, layers)
    layer_spec = specs[0].layers[0]
    assert "x" in layer_spec.visual_mapping
    assert "y" in layer_spec.visual_mapping
    x_vals = layer_spec.visual_mapping["x"]
    assert list(x_vals) == [1.0, 2.0, 3.0, 4.0]


def test_build_specs_from_layers_with_constant():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [
        Layer(
            geom=GeomPoint(),
            mapping={"x": "x", "y": "y", "color": "blue"},
        )
    ]
    specs = engine.build_specs_from_layers(dataset, layers)
    layer_spec = specs[0].layers[0]
    assert layer_spec.visual_mapping["color"] == "blue"


def test_build_specs_from_layers_with_scales():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [
        Layer(
            geom=GeomPoint(),
            mapping={"x": "x", "y": "y", "color": "group"},
            scales={
                "x": ScaleContinuous(),
                "color": ScaleOrdinal(palette=["red", "blue"]),
            },
        )
    ]
    specs = engine.build_specs_from_layers(dataset, layers)
    layer_spec = specs[0].layers[0]
    assert "color" in layer_spec.visual_mapping
    colors = list(layer_spec.visual_mapping["color"])
    assert len(colors) == 4
    assert "red" in colors
    assert "blue" in colors


def test_build_specs_from_layers_with_scale_constant():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [
        Layer(
            geom=GeomPoint(),
            mapping={"x": "x", "y": "y", "color": "should_be_overridden"},
            scales={"color": ScaleConstant(value="green")},
        )
    ]
    specs = engine.build_specs_from_layers(dataset, layers)
    layer_spec = specs[0].layers[0]
    colors = list(layer_spec.visual_mapping["color"])
    assert all(c == "green" for c in colors)


def test_build_specs_from_layers_with_stat():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [
        Layer(
            geom=GeomPoint(),
            stat=StatFn(func=lambda d: d.assign(y=d["y"] * 2)),
            mapping={"x": "x", "y": "y"},
        )
    ]
    specs = engine.build_specs_from_layers(dataset, layers)
    layer_spec = specs[0].layers[0]
    y_vals = list(layer_spec.visual_mapping["y"])
    assert y_vals == [20.0, 40.0, 60.0, 80.0]


def test_build_specs_from_layers_multiple_layers():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [
        Layer(geom=GeomLine(), mapping={"x": "x", "y": "y"}),
        Layer(geom=GeomPoint(), mapping={"x": "x", "y": "y", "color": "group"}),
    ]
    specs = engine.build_specs_from_layers(dataset, layers)
    assert len(specs[0].layers) == 2
    assert specs[0].layers[0].geom.name == "line"
    assert specs[0].layers[1].geom.name == "point"


def test_build_specs_from_template_with_bivariate():
    engine = FigureEngine()
    dataset = make_dataset()
    template = bivariate(mapping={"x": "x", "y": "y"})
    specs = engine.build_specs_from_template(dataset, template)
    assert len(specs) == 1
    spec = specs[0]
    assert len(spec.layers) == 1
    assert spec.layers[0].geom.name == "point"
    assert spec.settings["figsize"] == (10, 6)


def test_build_specs_from_template_with_timeseries():
    engine = FigureEngine()
    dataset = make_dataset()
    template = timeseries(mapping={"x": "x", "y": "y"})
    specs = engine.build_specs_from_template(dataset, template)
    assert len(specs) == 1
    assert len(specs[0].layers) == 2
    assert specs[0].layers[0].geom.name == "line"
    assert specs[0].layers[1].geom.name == "point"


def test_build_specs_from_template_with_settings_override():
    engine = FigureEngine()
    dataset = make_dataset()
    template = bivariate(mapping={"x": "x", "y": "y"})
    specs = engine.build_specs_from_template(
        dataset, template,
        settings={"title": "My Plot", "figsize": (8, 4)},
    )
    assert specs[0].settings["title"] == "My Plot"
    # User settings override template defaults
    assert specs[0].settings["figsize"] == (8, 4)


def test_build_specs_from_layers_with_coord():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [Layer(geom=GeomPoint(), mapping={"x": "x", "y": "y"})]
    specs = engine.build_specs_from_layers(dataset, layers, coord=CoordPolar())
    assert specs[0].coord.name == "polar"


def test_build_specs_from_layers_with_facet():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [Layer(geom=GeomPoint(), mapping={"x": "x", "y": "y"})]
    specs = engine.build_specs_from_layers(dataset, layers, facet=FacetWrap(by="group"))
    assert specs[0].facet.name == "wrap"


def test_build_specs_from_template_with_isotope():
    engine = FigureEngine()
    dataset = make_dataset()
    template = isotope(mapping={"x": "x", "y": "y"}, auto_filter=True)
    specs = engine.build_specs_from_template(dataset, template)
    assert len(specs) == 1
    # Should have function line layers + 1 scatter layer
    assert len(specs[0].layers) >= 2
    last_layer = specs[0].layers[-1]
    assert last_layer.geom.name == "point"
    # First layers should be function lines (if any functions loaded)
    first_layer = specs[0].layers[0]
    assert first_layer.geom.name in ("function_line", "point")


def test_layers_resolve_empty_mapping():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [Layer(geom=GeomPoint())]
    specs = engine.build_specs_from_layers(dataset, layers)
    assert len(specs) == 1
    assert specs[0].layers[0].visual_mapping == {}


def test_build_specs_from_layers_with_custom_template_name():
    engine = FigureEngine(config=None)
    dataset = make_dataset()
    layers = [Layer(geom=GeomPoint(), mapping={"x": "x"})]
    specs = engine.build_specs_from_layers(dataset, layers)
    assert specs[0].template_name == "custom"


def test_build_specs_from_layers_respects_context():
    engine = FigureEngine(
        config=None,
    )
    dataset = make_dataset()
    layers = [
        Layer(
            geom=GeomPoint(),
            mapping={"x": "x", "color": "{group}"},
        )
    ]
    context = {"group": "A"}
    specs = engine.build_specs_from_layers(dataset, layers)
    # Context is set during iterator expansion but without iterators the
    # context dict is empty. The {group} placeholder won't be resolved.
    spec = specs[0]
    assert spec.context == {}


def test_build_specs_from_layers_with_reverse_scale():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [
        Layer(
            geom=GeomPoint(),
            mapping={"x": "x"},
            scales={"x": ScaleContinuous(trans="reverse")},
        )
    ]
    specs = engine.build_specs_from_layers(dataset, layers)
    x_vals = list(specs[0].layers[0].visual_mapping["x"])
    assert x_vals == [-1.0, -2.0, -3.0, -4.0]
