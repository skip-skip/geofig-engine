"""
Tests for the simplified ``render_template`` entry point.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.engine import render_template
from geofig_engine.templates import bivariate, timeseries, isotope


@pytest.fixture
def sample_dataset():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "x": [1.0, 2.0, 3.0, 4.0],
        "y": [2.0, 3.0, 5.0, 7.0],
        "group": ["A", "A", "B", "B"],
    })
    return Dataset(dataframe=df, key_column="id")


@pytest.fixture
def sample_template():
    return bivariate(mapping={"x": "x", "y": "y"})


class TestRenderTemplate:
    def test_returns_specs_and_figures(self, sample_dataset, sample_template):
        specs, figures, legend_fig = render_template(
            dataset=sample_dataset,
            template=sample_template,
        )
        assert len(specs) == 1
        assert len(figures) == 1
        assert specs[0].template_name == "bivariate"
        import matplotlib.figure
        assert isinstance(legend_fig, matplotlib.figure.Figure)

    def test_with_iterator(self, sample_dataset, sample_template):
        iterator = DimensionIterator(
            channel="group",
            dimensions=["group"],
            mode=DimensionIterator.Mode.VALUE,
        )
        specs, figures, _ = render_template(
            dataset=sample_dataset,
            template=sample_template,
            iterators=iterator,
        )
        assert len(specs) == 2
        assert len(figures) == 2

    def test_with_settings(self, sample_dataset, sample_template):
        specs, _, _ = render_template(
            dataset=sample_dataset,
            template=sample_template,
            settings={"title": "Custom Title", "figsize": [8, 6]},
        )
        assert specs[0].settings.get("title") == "Custom Title"
        assert specs[0].settings.get("figsize") == [8, 6]

    def test_figures_are_matplotlib_figures(self, sample_dataset, sample_template):
        _, figures, legend_fig = render_template(
            dataset=sample_dataset,
            template=sample_template,
        )
        import matplotlib.figure
        assert isinstance(figures[0], matplotlib.figure.Figure)
        assert isinstance(legend_fig, matplotlib.figure.Figure)

    def test_unknown_renderer_raises(self, sample_dataset, sample_template):
        with pytest.raises(ValueError, match="Unsupported renderer"):
            render_template(
                dataset=sample_dataset,
                template=sample_template,
                renderer_name="plotly",
            )

    def test_savedir_includes_legend(self, sample_dataset, sample_template, tmp_path):
        _, _, _ = render_template(
            dataset=sample_dataset,
            template=sample_template,
            savedir=tmp_path,
        )
        pngs = list(tmp_path.glob("*.png"))
        assert "legend.png" in [p.name for p in pngs]

    def test_savedir_with_iterator_context(self, sample_dataset, sample_template, tmp_path):
        iterator = DimensionIterator(
            channel="group",
            dimensions=["group"],
            mode=DimensionIterator.Mode.VALUE,
        )
        _, _, _ = render_template(
            dataset=sample_dataset,
            template=sample_template,
            iterators=iterator,
            savedir=tmp_path,
        )
        pngs = list(tmp_path.glob("*.png"))
        # figures + 1 legend
        assert len(pngs) == 3
        filenames = [p.name for p in pngs]
        assert any("A" in f for f in filenames)
        assert any("B" in f for f in filenames)
        assert "legend.png" in filenames

    def test_empty_dataset_returns_empty(self):
        df = pd.DataFrame({"id": [], "x": [], "y": []})
        ds = Dataset(dataframe=df, key_column="id")
        template = bivariate(mapping={"x": "x", "y": "y"})
        specs, figures, _ = render_template(dataset=ds, template=template)
        assert len(specs) == 1
        assert len(figures) == 1

    def test_timeseries_template(self, sample_dataset):
        template = timeseries(mapping={"x": "x", "y": "y"})
        specs, _, _ = render_template(
            dataset=sample_dataset,
            template=template,
        )
        assert len(specs) == 1
        assert specs[0].template_name == "timeseries"

    def test_isotope_template(self, sample_dataset):
        template = isotope(mapping={"x": "x", "y": "y"})
        specs, _, _ = render_template(
            dataset=sample_dataset,
            template=template,
        )
        assert len(specs) == 1
        assert specs[0].template_name == "isotope"

    def test_legend_with_color_mapping(self, sample_dataset, tmp_path):
        template = bivariate(mapping={"x": "x", "y": "y", "color": "group"})
        _, _, legend_fig = render_template(
            dataset=sample_dataset,
            template=template,
            savedir=tmp_path,
        )
        import matplotlib.figure
        assert isinstance(legend_fig, matplotlib.figure.Figure)
        # Legend should have entries for groups A and B
        pngs = list(tmp_path.glob("*.png"))
        assert "legend.png" in [p.name for p in pngs]
