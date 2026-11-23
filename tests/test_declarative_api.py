"""
Focused tests for the Phase 15 declarative ``render_template`` (engine/api.py).

Covers the canonical entry surface:
- data coercion: DataProvider pass-through, DataFrame wrap, ndarray wrap
- template resolution: registry key (recipe defaults, no mapping) vs
  FigureTemplate / recipe adaptation
- mapping / coord / settings overrides merged over recipe defaults
- unknown template key → KeyError listing available keys
- missing required channels → informative error at spec-build time
- savedir persistence (legacy naming + legend.png); list[Figure] return
- no geodata / geochemmodel import in engine/api.py
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import pytest

from geofig_engine import build_template_specs as root_build_template_specs
from geofig_engine.engine import api as api_module
from geofig_engine.engine.api import (
    TEMPLATES,
    TemplateRecipe,
    build_template_specs,
    get_template,
    recipe_from,
    register_template,
    render_template,
)
from geofig_engine.core.coord import CoordCartesian, CoordPolar
from geofig_engine.core.facet import FacetGrid, FacetWrap
from geofig_engine.core.geom import GeomPoint, GeomSitePoint, GeomText
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatIdentity
from geofig_engine.engine.generator import resolve_layer_sources
from geofig_engine.provider import DataFrameProvider
from geofig_engine.templates import bivariate


def make_df():
    return pd.DataFrame({
        "id": [1, 2, 3, 4],
        "x": [1.0, 2.0, 3.0, 4.0],
        "y": [2.0, 3.0, 5.0, 7.0],
        "group": ["A", "A", "B", "B"],
    })


@pytest.fixture(autouse=True)
def _isolate_registry():
    """Preserve/restore the global registry around each test."""
    saved = dict(TEMPLATES)
    TEMPLATES.clear()
    yield
    TEMPLATES.clear()
    TEMPLATES.update(saved)


def register_bivariate_with_defaults():
    """Thin adapter over the legacy factory — complete recipe defaults.

    Mirrors the support-branch adapters that ``15_wp6`` ships; keeps this
    ticket's tests focused on the entry-point plumbing.
    """

    def builder(mapping=None, settings=None, **_):
        return bivariate(mapping=mapping or {"x": "x", "y": "y"})

    register_template("bivariate", builder)
    return builder


def point_layer(mapping=None):
    return Layer(
        geom=GeomPoint(),
        stat=StatIdentity(),
        mapping=mapping if mapping is not None else {"x": "x", "y": "y"},
    )


def scatter_offsets(fig):
    """The x/y scatter offsets of a rendered bivariate figure."""
    return fig.axes[0].collections[0].get_offsets()


class TestDataInputs:
    def test_dataframe_is_wrapped_and_renders(self):
        figures = render_template(
            data=make_df(),
            template=bivariate(mapping={"x": "x", "y": "y"}),
        )
        assert len(figures) == 1

    def test_provider_data_with_figure_template(self):
        figures = render_template(
            data=DataFrameProvider(make_df()),
            template=bivariate(mapping={"x": "x", "y": "y"}),
        )
        assert len(figures) == 1

    def test_ndarray_wrapped_with_positional_columns(self):
        arr = np.array(
            [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]],
            dtype=float,
        )
        figures = render_template(
            data=arr,
            template=bivariate(mapping={"x": "0", "y": "1"}),
        )
        assert len(figures) == 1
        offsets = scatter_offsets(figures[0])
        assert np.allclose(sorted(offsets[:, 0]), [1.0, 3.0, 5.0, 7.0])
        assert np.allclose(sorted(offsets[:, 1]), [2.0, 4.0, 6.0, 8.0])

    def test_rejects_unsupported_data_type(self):
        with pytest.raises(TypeError, match="data must be"):
            render_template(data="not data", template=bivariate())


class TestTemplateResolution:
    def test_registry_key_renders_with_recipe_defaults(self):
        register_bivariate_with_defaults()
        # no mapping → recipe defaults apply
        figures = render_template(data=make_df(), template="bivariate")
        assert len(figures) == 1
        offsets = scatter_offsets(figures[0])
        assert np.allclose(sorted(offsets[:, 0]), [1.0, 2.0, 3.0, 4.0])
        assert np.allclose(sorted(offsets[:, 1]), [2.0, 3.0, 5.0, 7.0])

    def test_unknown_key_raises_keyerror_listing_keys(self):
        register_template("known", lambda **_: TemplateRecipe(name="known", layers=[point_layer()]))
        with pytest.raises(KeyError) as excinfo:
            render_template(data=make_df(), template="nope")
        message = str(excinfo.value)
        assert "nope" in message
        assert "known" in message

    def test_recipe_object_passes_through(self):
        recipe = TemplateRecipe(name="direct", layers=[point_layer()])
        figures = render_template(data=make_df(), template=recipe)
        assert len(figures) == 1

    def test_string_key_builder_receives_mapping_and_settings(self):
        calls = {}

        def recording(mapping=None, settings=None, **_):
            calls["mapping"] = mapping
            calls["settings"] = settings
            return TemplateRecipe(
                name="recording",
                layers=[point_layer(mapping={"x": "x", "y": "y"})],
                mapping_consumed=True,
            )

        register_template("recording", recording)
        render_template(
            data=make_df(),
            template="recording",
            mapping={"x": "y"},
            settings={"title": "T"},
        )
        assert calls["mapping"] == {"x": "y"}
        assert calls["settings"] == {"title": "T"}


class TestOverrides:
    def test_mapping_overrides_recipe_layers(self):
        register_template(
            "mapped",
            lambda **_: TemplateRecipe(name="mapped", layers=[point_layer()]),
        )
        # swap x/y via the user mapping — proves per-layer override
        figures = render_template(
            data=make_df(),
            template="mapped",
            mapping={"x": "y", "y": "x"},
        )
        offsets = scatter_offsets(figures[0])
        assert np.allclose(sorted(offsets[:, 0]), [2.0, 3.0, 5.0, 7.0])
        assert np.allclose(sorted(offsets[:, 1]), [1.0, 2.0, 3.0, 4.0])

    def test_mapping_merges_onto_recipe(self):
        # partial override: color added, recipe x/y retained
        figures = render_template(
            data=make_df(),
            template=bivariate(mapping={"x": "x", "y": "y"}),
            mapping={"color": "group"},
        )
        offsets = scatter_offsets(figures[0])
        assert np.allclose(sorted(offsets[:, 0]), [1.0, 2.0, 3.0, 4.0])
        assert np.allclose(sorted(offsets[:, 1]), [2.0, 3.0, 5.0, 7.0])

    def test_coord_overrides_recipe(self):
        figures = render_template(
            data=make_df(),
            template=bivariate(mapping={"x": "x", "y": "y"}),
            coord=CoordPolar(),
        )
        assert figures[0].axes[0].name == "polar"

    def test_settings_merge_recipe_defaults_then_user(self):
        register_template(
            "settings_demo",
            lambda **_: TemplateRecipe(
                name="settings_demo",
                layers=[point_layer()],
                default_settings={"title": "from recipe"},
            ),
        )
        # recipe default applies with no user settings
        figures = render_template(data=make_df(), template="settings_demo")
        assert figures[0].axes[0].get_title() == "from recipe"
        # user settings win over recipe defaults
        figures = render_template(
            data=make_df(),
            template="settings_demo",
            settings={"title": "from user"},
        )
        assert figures[0].axes[0].get_title() == "from user"


class TestPointSize:
    def test_point_size_setting_scales_point_markers(self):
        figures = render_template(
            data=make_df(),
            template=bivariate(mapping={"x": "x", "y": "y"}),
            settings={"point_size": 45},
        )
        sizes = figures[0].axes[0].collections[0].get_sizes()
        assert np.allclose(sizes, 45.0)

    def test_point_size_unset_keeps_handler_default(self):
        figures = render_template(
            data=make_df(),
            template=bivariate(mapping={"x": "x", "y": "y"}),
        )
        sizes = figures[0].axes[0].collections[0].get_sizes()
        assert np.allclose(sizes, 20.0)

    def test_site_point_geom_receives_point_size(self):
        layer = Layer(
            geom=GeomSitePoint(),
            stat=StatIdentity(),
            mapping={"x": "x", "y": "y"},
        )
        specs = resolve_layer_sources(
            [layer],
            frame=make_df(),
            resolve=lambda source: source,
            point_size=90,
        )
        assert specs[0].visual_mapping["size"] == 90

    def test_point_size_skips_text_geom_font_size(self):
        layer = Layer(
            geom=GeomText(),
            stat=StatIdentity(),
            mapping={"x": "x", "y": "y", "label": "id"},
        )
        specs = resolve_layer_sources(
            [layer],
            frame=make_df(),
            resolve=lambda source: source,
            point_size=45,
        )
        assert "size" not in specs[0].visual_mapping

    def test_point_size_resolves_from_iterator_context(self):
        df = pd.DataFrame({
            "x": [1.0, 2.0, 3.0, 4.0],
            "y": [2.0, 3.0, 5.0, 7.0],
            "marker_size": [10.0, 20.0, 10.0, 20.0],
        })
        figures = render_template(
            data=df,
            template=bivariate(mapping={"x": "x", "y": "y"}),
            settings={"point_size": "{marker_size}"},
            iterators=[DimensionIterator(
                channel="marker_size",
                dimensions=["marker_size"],
                mode=DimensionIterator.Mode.VALUE,
            )],
        )
        assert len(figures) == 2
        for figure, expected in zip(figures, (10.0, 20.0)):
            assert np.allclose(
                figure.axes[0].collections[0].get_sizes(), expected
            )

    @pytest.mark.parametrize("bad", [0, -1, "large", True])
    def test_point_size_rejects_invalid_values(self, bad):
        with pytest.raises(ValueError, match="point_size"):
            render_template(
                data=make_df(),
                template=bivariate(mapping={"x": "x", "y": "y"}),
                settings={"point_size": bad},
            )


class TestNativeTickFont:
    def test_fontsize_knob_bumps_native_tick_labels(self):
        figures = render_template(
            data=make_df(),
            template=bivariate(mapping={"x": "x", "y": "y"}),
            settings={"fontsize": 12},
        )
        ax = figures[0].axes[0]
        assert ax.get_xticklabels()[0].get_fontsize() == 12
        assert ax.get_yticklabels()[0].get_fontsize() == 12

    def test_tick_fontsize_wins_over_generic_fontsize(self):
        figures = render_template(
            data=make_df(),
            template=bivariate(mapping={"x": "x", "y": "y"}),
            settings={"fontsize": 12, "tick_fontsize": 9},
        )
        ax = figures[0].axes[0]
        assert ax.get_xticklabels()[0].get_fontsize() == 9
        assert ax.get_yticklabels()[0].get_fontsize() == 9

    def test_unset_knob_keeps_rcparam_default(self):
        import matplotlib.pyplot as plt

        figures = render_template(
            data=make_df(),
            template=bivariate(mapping={"x": "x", "y": "y"}),
        )
        ax = figures[0].axes[0]
        assert ax.get_xticklabels()[0].get_fontsize() == plt.rcParams["font.size"]


class TestErrors:
    def test_missing_required_channel_raises_informative(self):
        template = bivariate(mapping={"x": "x"})  # missing y
        with pytest.raises(ValueError) as excinfo:
            render_template(data=make_df(), template=template)
        message = str(excinfo.value)
        assert "point" in message
        assert "y" in message
        assert "requires" in message


class TestSavedir:
    def test_savedir_writes_figures_and_legend(self, tmp_path):
        figures = render_template(
            data=make_df(),
            template=bivariate(mapping={"x": "x", "y": "y", "color": "group"}),
            savedir=tmp_path,
        )
        assert len(figures) == 1
        pngs = sorted(p.name for p in tmp_path.glob("*.png"))
        assert pngs == ["001.png", "legend.png"]

    def test_savedir_naming_with_facet_and_legend(self, tmp_path):
        figures = render_template(
            data=make_df(),
            template=bivariate(mapping={"x": "x", "y": "y", "color": "group"}),
            facet=FacetWrap(by="group"),
            savedir=tmp_path,
        )
        # facet keys stay out of iterator_key → plain zero-padded names
        assert len(figures) == 1
        pngs = sorted(p.name for p in tmp_path.glob("*.png"))
        assert pngs == ["001.png", "legend.png"]


class TestFacet:
    """Facet = panels within one figure (Phase 18.1 contract)."""

    def test_facet_wrap_single_multi_panel_figure(self):
        figures = render_template(
            data=make_df(),
            template=bivariate(mapping={"x": "x", "y": "y"}),
            facet=FacetWrap(by="group"),
        )
        assert len(figures) == 1
        assert len(figures[0].axes) == 2
        assert {ax.get_title() for ax in figures[0].axes} == {"group=A", "group=B"}

    def test_facet_grid_single_figure_layout(self):
        df = pd.DataFrame({
            "x": [1.0, 2.0, 3.0, 4.0, 5.0],
            "y": [2.0, 3.0, 5.0, 7.0, 1.0],
            "row": ["R1", "R1", "R1", "R2", "R2"],
            "col": ["C1", "C2", "C1", "C1", "C1"],  # R2 x C2 absent
        })
        figures = render_template(
            data=df,
            template=bivariate(mapping={"x": "x", "y": "y"}),
            facet=FacetGrid(row="row", col="col"),
        )
        assert len(figures) == 1
        axes = figures[0].axes
        assert len(axes) == 4  # full 2x2 grid layout
        # missing combo keeps a hidden axis, not an empty figure
        assert not axes[3].get_visible()
        # leading-edge labels: col across the top row, row down the left column
        assert axes[0].get_title() == "C1"
        assert axes[1].get_title() == "C2"
        assert axes[0].get_ylabel() == "R1"
        assert axes[2].get_ylabel() == "R2"

    def test_facet_with_iterators_composes(self):
        df = pd.DataFrame({
            "x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            "y": [2.0, 3.0, 5.0, 7.0, 1.0, 4.0, 6.0, 9.0],
            "group": ["A", "A", "B", "B", "A", "A", "B", "B"],
            "cat": ["a", "a", "a", "a", "b", "b", "b", "b"],
        })
        figures = render_template(
            data=df,
            template=bivariate(mapping={"x": "x", "y": "y"}),
            facet=FacetWrap(by="group"),
            iterators=[DimensionIterator(
                channel="cat",
                dimensions=["cat"],
                mode=DimensionIterator.Mode.VALUE,
            )],
        )
        # one figure per iterator value, each carrying the full facet grid
        assert len(figures) == 2
        for fig in figures:
            assert len(fig.axes) == 2
            assert {ax.get_title() for ax in fig.axes} == {"group=A", "group=B"}

    def test_facet_empty_data_returns_one_figure(self):
        df = pd.DataFrame({"x": [], "y": [], "group": []})
        figures = render_template(
            data=df,
            template=bivariate(mapping={"x": "x", "y": "y"}),
            facet=FacetWrap(by="group"),
        )
        assert len(figures) == 1


class TestBuildTemplateSpecsExport:
    def test_root_export_matches_api_function(self):
        assert root_build_template_specs is build_template_specs

    def test_render_template_has_no_duplicated_spec_building_wiring(self):
        import inspect

        source = inspect.getsource(api_module.render_template)
        assert "specs = build_template_specs(" in source
        assert "provider = _wrap_data(" not in source
        assert "generator = FigureGenerator(" not in source

    def test_render_template_delegates_and_returns_figures_only(self, monkeypatch):
        import matplotlib.figure

        from geofig_engine.core.spec import FigureSpec

        frame = make_df()
        template = bivariate(mapping={"x": "x", "y": "y"})
        specs = build_template_specs(frame, template)
        captured = {}

        def fake_build(**kwargs):
            captured.update(kwargs)
            return specs

        monkeypatch.setattr(api_module, "build_template_specs", fake_build)

        figures = render_template(
            data=frame, template=template, settings={"title": "T"}
        )

        assert captured["data"] is frame
        assert captured["template"] is template
        assert captured["settings"] == {"title": "T"}
        assert len(figures) == len(specs)
        assert all(isinstance(fig, matplotlib.figure.Figure) for fig in figures)
        assert not any(isinstance(fig, FigureSpec) for fig in figures)


class TestNoUpstreamImports:
    def test_engine_api_has_no_geodata_import(self):
        mod = sys.modules.get("geofig_engine.engine.api")
        if mod is None:
            pytest.skip("engine.api module not loaded")
        source_file = mod.__file__
        assert source_file is not None
        with open(source_file) as f:
            source = f.read()
        assert "import geodata" not in source
        assert "from geodata" not in source
        assert "import geochemmodel" not in source
        assert "from geochemmodel" not in source