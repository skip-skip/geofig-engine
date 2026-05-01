"""
Tests for FigEngine orchestration.
"""

import pandas as pd

from geofig_engine.core.dataset import Dataset
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
    assert spec.settings["alpha"] == 0.8
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
