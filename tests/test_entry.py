"""
Tests for the canonical ``render_template`` entry point (Phase 15).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.facet import FacetWrap
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.engine import render_template
from geofig_engine.templates import bivariate, timeseries, isotope


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "id": [1, 2, 3, 4],
        "x": [1.0, 2.0, 3.0, 4.0],
        "y": [2.0, 3.0, 5.0, 7.0],
        "group": ["A", "A", "B", "B"],
    })


@pytest.fixture
def sample_template():
    return bivariate(mapping={"x": "x", "y": "y"})


class TestRenderTemplate:
    def test_returns_list_of_figures(self, sample_df, sample_template):
        import matplotlib.figure

        figures = render_template(data=sample_df, template=sample_template)
        assert isinstance(figures, list)
        assert len(figures) == 1
        assert isinstance(figures[0], matplotlib.figure.Figure)

    def test_with_iterator(self, sample_df, sample_template):
        iterator = DimensionIterator(
            channel="group",
            dimensions=["group"],
            mode=DimensionIterator.Mode.VALUE,
        )
        figures = render_template(
            data=sample_df,
            template=sample_template,
            iterators=iterator,
        )
        assert len(figures) == 2

    def test_with_settings(self, sample_df, sample_template):
        figures = render_template(
            data=sample_df,
            template=sample_template,
            settings={"title": "Custom Title", "figsize": [8, 6]},
        )
        assert figures[0].axes[0].get_title() == "Custom Title"

    def test_figures_are_matplotlib_figures(self, sample_df, sample_template):
        import matplotlib.figure

        figures = render_template(data=sample_df, template=sample_template)
        assert isinstance(figures[0], matplotlib.figure.Figure)

    def test_unknown_renderer_raises(self, sample_df, sample_template):
        with pytest.raises(ValueError, match="Unsupported renderer"):
            render_template(
                data=sample_df,
                template=sample_template,
                renderer_name="plotly",
            )

    def test_savedir_includes_legend(self, sample_df, sample_template, tmp_path):
        render_template(
            data=sample_df,
            template=sample_template,
            savedir=tmp_path,
        )
        pngs = list(tmp_path.glob("*.png"))
        assert "legend.png" in [p.name for p in pngs]

    def test_savedir_with_iterator_context(self, sample_df, sample_template, tmp_path):
        iterator = DimensionIterator(
            channel="group",
            dimensions=["group"],
            mode=DimensionIterator.Mode.VALUE,
        )
        render_template(
            data=sample_df,
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

    def test_empty_dataset_returns_one_figure(self):
        df = pd.DataFrame({"id": [], "x": [], "y": []})
        template = bivariate(mapping={"x": "x", "y": "y"})
        figures = render_template(data=df, template=template)
        assert len(figures) == 1

    def test_timeseries_template(self, sample_df):
        template = timeseries(mapping={"x": "x", "y": "y"})
        figures = render_template(data=sample_df, template=template)
        assert len(figures) == 1

    def test_isotope_template(self, sample_df):
        template = isotope(mapping={"x": "x", "y": "y"})
        figures = render_template(data=sample_df, template=template)
        assert len(figures) == 1

    def test_with_facet_renders_multi_panel_figure(self, sample_df, sample_template, tmp_path):
        figures = render_template(
            data=sample_df,
            template=sample_template,
            facet=FacetWrap(by="group"),
        )
        # one figure whose panels split the facet groups
        assert len(figures) == 1
        assert len(figures[0].axes) == 2
        # savedir naming uses iterator keys only (facet keys stay out)
        render_template(
            data=sample_df,
            template=sample_template,
            facet=FacetWrap(by="group"),
            savedir=tmp_path,
        )
        filenames = [p.name for p in tmp_path.glob("*.png")]
        assert "001.png" in filenames
        assert "legend.png" in filenames

    def test_legend_with_color_mapping(self, sample_df, tmp_path):
        template = bivariate(mapping={"x": "x", "y": "y", "color": "group"})
        figures = render_template(
            data=sample_df,
            template=template,
            savedir=tmp_path,
        )
        import matplotlib.figure

        assert isinstance(figures[0], matplotlib.figure.Figure)
        # Legend should have entries for groups A and B
        pngs = list(tmp_path.glob("*.png"))
        assert "legend.png" in [p.name for p in pngs]