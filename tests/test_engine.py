"""
Tests for FigEngine orchestration.
"""

import pandas as pd

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.dimension_selector import DimensionSelector, ColumnSelector
from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatIdentity
from geofig_engine.engine import EngineConfig, FigureEngine
from geofig_engine.renderers.base import BaseRenderer
from geofig_engine.templates import bivariate


class DummyRenderer(BaseRenderer):
    def render(self, spec):
        return f"rendered {spec.template_name}"


def make_dataset() -> Dataset:
    data = pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "x": [1, 2, 3, 4],
            "y": [10, 20, 30, 40],
            "group": ["A", "B", "A", "B"],
        }
    )
    return Dataset(dataframe=data, key_column="id")


def test_build_specs_from_layers_creates_single_spec():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [Layer(geom=GeomPoint(), stat=StatIdentity(), mapping={"x": "x", "y": "y"})]

    specs = engine.build_specs_from_layers(dataset=dataset, layers=layers)
    assert len(specs) == 1
    spec = specs[0]
    assert spec.template_name == "custom"
    assert len(spec.layers) == 1
    assert spec.layers[0].geom.name == "point"


def test_build_specs_from_layers_with_iterator_returns_multiple_specs():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [Layer(geom=GeomPoint(), stat=StatIdentity(), mapping={"x": "x", "y": "y"})]
    iterator = DimensionIterator(channel="group", dimensions=["group"], 
                                 mode=DimensionIterator.Mode.VALUE)

    specs = engine.build_specs_from_layers(
        dataset=dataset,
        layers=layers,
        iterators=iterator,
    )

    assert len(specs) == 2
    assert {tuple(spec.context.items())[0] for spec in specs} == {("group", "A"), ("group", "B")}


def test_build_specs_from_template():
    engine = FigureEngine()
    dataset = make_dataset()
    template = bivariate(mapping={"x": "x", "y": "y"})

    specs = engine.build_specs_from_template(dataset=dataset, template=template)
    assert len(specs) == 1
    spec = specs[0]
    assert spec.settings["figsize"] == (10, 6)


def test_render_dispatches_to_renderer():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [Layer(geom=GeomPoint(), stat=StatIdentity(), mapping={"x": "x", "y": "y"})]
    renderer = DummyRenderer()

    specs = engine.build_specs_from_layers(dataset=dataset, layers=layers)
    results = engine.render_specs(specs, renderer)

    assert results == ["rendered custom"]


def test_render_specs_uses_existing_specs():
    engine = FigureEngine()
    dataset = make_dataset()
    layers = [Layer(geom=GeomPoint(), stat=StatIdentity(), mapping={"x": "x", "y": "y"})]
    renderer = DummyRenderer()

    specs = engine.build_specs_from_layers(
        dataset=dataset,
        layers=layers,
    )

    results = engine.render_specs(specs, renderer)
    assert results == ["rendered custom"]


def test_engine_respects_default_context_and_settings():
    config = EngineConfig(default_settings={"title": "Default Title"}, default_context={"source": "sensor"})
    engine = FigureEngine(config=config)
    dataset = make_dataset()
    layers = [Layer(geom=GeomPoint(), stat=StatIdentity(), mapping={"x": "x", "y": "y"})]

    spec = engine.build_specs_from_layers(
        dataset=dataset,
        layers=layers,
        settings={"xlabel": "X Axis"},
    )[0]

    assert spec.settings["title"] == "Default Title"
    assert spec.settings["xlabel"] == "X Axis"
    assert spec.context["source"] == "sensor"


def test_build_specs_from_layers_with_column_selector_and_placeholders():
    engine = FigureEngine()
    data = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "x": [1, 2, 3],
            "y1": [1, 2, 3],
            "y2": [3, 2, 1],
            "group": ["A", "A", "B"],
        }
    )
    dimensions = {
        "x": Dimension("x", {}),
        "y1": Dimension("y1", {"type": "analyte"}),
        "y2": Dimension("y2", {"type": "analyte"}),
        "group": Dimension("group", {}),
    }
    dataset = Dataset(dataframe=data, key_column="id", dimensions=dimensions)
    layers = [Layer(geom=GeomPoint(), stat=StatIdentity(), mapping={"x": "x", "y": "{y}", "color": "{color}"})]
    iterators = [
        DimensionIterator(
            channel="y",
            dimensions={"type": "analyte"},
            mode=DimensionIterator.Mode.DIMENSION,
        ),
        DimensionIterator(
            channel="color",
            dimensions=["group"],
            mode=DimensionIterator.Mode.DIMENSION,
        ),
    ]

    specs = engine.build_specs_from_layers(
        dataset=dataset,
        layers=layers,
        iterators=iterators,
        settings={"xlabel": "x"},
    )
    assert len(specs) == 2
    assert {spec.context["y"] for spec in specs} == {"y1", "y2"}
    assert all(spec.context["color"] == "group" for spec in specs)
