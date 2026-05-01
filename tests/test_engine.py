"""
Tests for FigEngine orchestration.
"""

import pandas as pd

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.dimension_selector import DimensionSelector
from geofig_engine.core.iterator import ColumnSelector
from geofig_engine.engine import EngineConfig, FigureEngine
from geofig_engine.renderers.base import BaseRenderer
from geofig_engine.templates import BivariateTemplate


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


def test_build_specs_creates_single_spec():
    engine = FigureEngine()
    dataset = make_dataset()
    template = BivariateTemplate()

    specs = engine.build_specs(
        dataset=dataset,
        template=template,
        mappings={"x": ["x"], "y": ["y"]},
    )

    assert len(specs) == 1
    spec = specs[0]
    assert spec.template_name == "bivariate"
    assert spec.mappings["alpha"] == 0.8
    assert spec.settings["figsize"] == (10, 6)
    assert spec.mappings["x"] == ["x"]


def test_build_specs_with_iterator_returns_multiple_specs():
    engine = FigureEngine()
    dataset = make_dataset()
    template = BivariateTemplate()

    specs = engine.build_specs(
        dataset=dataset,
        template=template,
        mappings={"x": ["x"], "y": ["y"]},
        iterator_selectors={"group": ["group"]},
    )

    assert len(specs) == 2
    assert {tuple(spec.context.items())[0] for spec in specs} == {("group", "A"), ("group", "B")}


def test_build_specs_with_column_selector_and_placeholders():
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
    template = BivariateTemplate()

    specs = engine.build_specs(
        dataset=dataset,
        template=template,
        mappings={"x": "x", "y": "{y}", "color": "{color}"},
        iterator_selectors={
            "y": ColumnSelector(DimensionSelector({"type": "analyte"})),
            "color": ColumnSelector(["group"]),
        },
        settings={"xlabel": "x"},
    )

    assert len(specs) == 2
    assert {spec.context["y"] for spec in specs} == {"y1", "y2"}
    assert all(spec.context["color"] == "group" for spec in specs)
    assert all(spec.mappings["y"] in [["y1"], ["y2"]] for spec in specs)


def test_render_dispatches_to_renderer():
    engine = FigureEngine()
    dataset = make_dataset()
    template = BivariateTemplate()
    renderer = DummyRenderer()

    results = engine.render(
        dataset=dataset,
        template=template,
        mappings={"x": ["x"], "y": ["y"]},
        renderer=renderer,
    )

    assert results == ["rendered bivariate"]


def test_render_specs_uses_existing_specs():
    engine = FigureEngine()
    dataset = make_dataset()
    template = BivariateTemplate()
    renderer = DummyRenderer()

    specs = engine.build_specs(
        dataset=dataset,
        template=template,
        mappings={"x": ["x"], "y": ["y"]},
    )

    results = engine.render_specs(specs, renderer)
    assert results == ["rendered bivariate"]


def test_engine_respects_default_context_and_settings():
    config = EngineConfig(default_settings={"title": "Default Title"}, default_context={"source": "sensor"})
    engine = FigureEngine(config=config)
    dataset = make_dataset()
    template = BivariateTemplate()

    spec = engine.build_specs(
        dataset=dataset,
        template=template,
        mappings={"x": ["x"], "y": ["y"]},
    )[0]

    assert spec.settings["title"] == "Default Title"
    assert spec.context["source"] == "sensor"


def test_build_specs_applies_template_default_mappings():
    engine = FigureEngine()
    dataset = make_dataset()
    template = BivariateTemplate()

    spec = engine.build_specs(
        dataset=dataset,
        template=template,
        mappings={"x": ["x"], "y": ["y"]},
    )[0]

    assert spec.mappings["alpha"] == 0.8
    assert spec.settings["figsize"] == (10, 6)


def test_build_specs_mapping_overrides_template_defaults():
    engine = FigureEngine()
    dataset = make_dataset()
    template = BivariateTemplate()

    spec = engine.build_specs(
        dataset=dataset,
        template=template,
        mappings={"x": ["x"], "y": ["y"], "alpha": 0.3},
    )[0]

    assert spec.mappings["alpha"] == 0.3
