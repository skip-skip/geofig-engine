"""
Phase 15 wp6 / 18.4 wp1-wp3: registry-templated rendering through ``render_template``.

Covers the pipeline builders plus the ten legacy keys. The eight
``FigureTemplate`` factories resolve to native ``*_builder`` functions;
``piper``/``stiff`` resolve to first-class ``SpecRecipe`` builders.
"""

import hashlib
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pytest
import pandas as pd

from geofig_engine import (
    TEMPLATES,
    build_template_specs,
    get_template,
    render_template,
)
from geofig_engine.core.spec import FigureSpec
from geofig_engine.engine.api import SpecRecipe, recipe_from
from geofig_engine.templates import (
    anp_agp,
    anp_agp_builder,
    histogram,
    histogram_builder,
    isotope,
    isotope_builder,
    nagph_nag,
    nagph_nag_builder,
    npr_nnp,
    npr_nnp_builder,
    pie,
    pie_builder,
    piper_builder,
    radar,
    radar_builder,
    stiff_builder,
    timeseries,
    timeseries_builder,
)


def make_df():
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "x": [1.0, 2.0, 3.0, 4.0],
            "y": [2.0, 3.0, 5.0, 7.0],
            "group": ["A", "A", "B", "B"],
            "cat": ["a", "b", "c", "d"],
            "val": [4.0, 5.0, 6.0, 7.0],
            # per-point label series used by the ternary ARD templates
            "x_label": ["a", "b", "c", "d"],
            "y_label": ["A", "B", "C", "D"],
        }
    )


def make_piper_df():
    return pd.DataFrame(
        {
            "Ca": [1.0, 2.0],
            "Mg": [0.5, 1.0],
            "Na+K": [0.3, 0.5],
            "HCO3": [2.0, 3.0],
            "SO4": [0.2, 0.4],
            "Cl": [0.1, 0.2],
            "group": ["A", "B"],
        }
    )


def make_stiff_df():
    return pd.DataFrame(
        {
            "ca": [50.0],
            "mg": [20.0],
            "na_k": [30.0],
            "cl": [40.0],
            "hco3": [10.0],
            "so4": [30.0],
        }
    )


def scatter_offsets(fig):
    """The x/y scatter offsets of a rendered bivariate figure."""
    return fig.axes[0].collections[0].get_offsets()


LEGACY_RENDER_CASES = [
    ("histogram", {"x": "x"}),
    ("pie", {"x": "cat", "y": "val"}),
    ("radar", {"x": "x", "y": "y"}),
    ("timeseries", {"x": "x", "y": "y"}),
    ("isotope", {"x": "x", "y": "y"}),
    ("npr_nnp", {"x": "x", "y": "y"}),
    ("anp_agp", {"x": "x", "y": "y"}),
    ("nagph_nag", {"x": "x", "y": "y"}),
]

SPEC_RECIPE_KEYS = ["piper", "stiff"]

NATIVE_BUILDERS = {
    "histogram": histogram_builder,
    "pie": pie_builder,
    "radar": radar_builder,
    "timeseries": timeseries_builder,
    "isotope": isotope_builder,
    "npr_nnp": npr_nnp_builder,
    "anp_agp": anp_agp_builder,
    "nagph_nag": nagph_nag_builder,
}

SPEC_RECIPE_BUILDERS = {
    "piper": piper_builder,
    "stiff": stiff_builder,
}

NATIVE_FACTORIES = {
    "histogram": histogram,
    "pie": pie,
    "radar": radar,
    "timeseries": timeseries,
    "isotope": isotope,
    "npr_nnp": npr_nnp,
    "anp_agp": anp_agp,
    "nagph_nag": nagph_nag,
}

ALL_SEEDED_BUILDERS = {**NATIVE_BUILDERS, **SPEC_RECIPE_BUILDERS}

ALL_RENDER_CASES = [
    (key, make_df, mapping) for key, mapping in LEGACY_RENDER_CASES
] + [
    ("piper", make_piper_df, None),
    ("stiff", make_stiff_df, None),
]


class TestPipelineBuilders:
    def test_bivariate_key_renders_mapping_free(self):
        figures = render_template(data=make_df(), template="bivariate")
        assert len(figures) == 1
        offsets = scatter_offsets(figures[0])
        assert len(offsets) == 4
        assert math.isclose(sorted(offsets[:, 0])[0], 1.0)
        assert math.isclose(sorted(offsets[:, 1])[-1], 7.0)

    def test_bivariate_key_honors_mapping_override(self):
        figures = render_template(
            data=make_df(),
            template="bivariate",
            mapping={"x": "y", "y": "x"},
        )
        offsets = scatter_offsets(figures[0])
        # x-axis now holds the legacy y column values
        assert math.isclose(sorted(offsets[:, 0])[-1], 7.0)
        assert math.isclose(sorted(offsets[:, 1])[0], 1.0)

    def test_bivariate_key_honors_settings(self):
        figures = render_template(
            data=make_df(),
            template="bivariate",
            settings={"figsize": (6, 6)},
        )
        assert figures[0].get_size_inches().tolist() == [6.0, 6.0]

    def test_boxplot_with_points_key_renders_boxes_and_points(self):
        figures = render_template(
            data=make_df(),
            template="boxplot_with_points",
            mapping={"x": "x", "y": "y"},
        )
        assert len(figures) == 1
        # box rectangles (GeomBox) are drawn as ax patches
        assert len(figures[0].axes[0].patches) > 0
        # jittered points (GeomPoint overlay) are drawn as collections
        assert len(figures[0].axes[0].collections) > 0

    def test_boxplot_categorical_x_documents_jitter_limitation(self):
        # Pre-existing renderer limitation (handlers.py): jittered points
        # add floats to the x series, so a non-numeric x column raises.
        with pytest.raises(TypeError, match="concatenate"):
            render_template(
                data=make_df(),
                template="boxplot_with_points",
                mapping={"x": "group", "y": "x"},
            )

    def test_missing_required_channel_raises_informative(self):
        # Mapping overrides merge per channel key, so a channel is only ever
        # missing when the recipe itself omits it. Pin the informative
        # spec-build error on such a recipe.
        from geofig_engine.core.geom import GeomPoint
        from geofig_engine.core.layer import Layer
        from geofig_engine.templates.base import FigureTemplate

        template = FigureTemplate(
            layers=[Layer(geom=GeomPoint(), mapping={"color": "group"})]
        )
        with pytest.raises(ValueError, match="requires channel"):
            render_template(data=make_df(), template=template)


class TestLegacyRegistryKeys:
    def test_all_ten_legacy_keys_registered(self):
        keys = {
            "histogram",
            "pie",
            "radar",
            "timeseries",
            "isotope",
            "npr_nnp",
            "anp_agp",
            "nagph_nag",
            "piper",
            "stiff",
        }
        assert keys <= set(TEMPLATES)
        for key in keys:
            assert callable(get_template(key))

    @pytest.mark.parametrize("key,data_factory,mapping", ALL_RENDER_CASES)
    def test_seeded_key_renders_through_canonical_path(self, key, data_factory, mapping):
        assert get_template(key) is ALL_SEEDED_BUILDERS[key]
        figures = render_template(data=data_factory(), template=key, mapping=mapping)
        assert len(figures) == 1

    @pytest.mark.parametrize("key,data_factory,mapping", ALL_RENDER_CASES)
    def test_seeded_key_builds_specs_without_rendering(
        self, key, data_factory, mapping, monkeypatch
    ):
        import geofig_engine.renderers as renderers

        monkeypatch.setattr(
            renderers,
            "MatplotlibRenderer",
            lambda *args, **kwargs: pytest.fail("renderer must not be instantiated"),
        )

        specs = build_template_specs(
            data=data_factory(), template=key, mapping=mapping
        )

        assert specs
        assert all(isinstance(spec, FigureSpec) for spec in specs)

    @pytest.mark.parametrize("key,builder", NATIVE_BUILDERS.items())
    def test_factory_keys_seed_native_builders(self, key, builder):
        assert get_template(key) is builder

    def test_registry_seed_has_no_legacy_adapter(self):
        import inspect

        from geofig_engine.engine import api

        source = inspect.getsource(api)
        assert "legacy_adapter" not in source
        assert "not registry-adaptable" not in source

    @pytest.mark.parametrize("key,builder", SPEC_RECIPE_BUILDERS.items())
    def test_spec_recipe_keys_seed_native_builders(self, key, builder):
        assert get_template(key) is builder

    @pytest.mark.parametrize("key", SPEC_RECIPE_KEYS)
    def test_spec_recipe_key_returns_spec_recipe(self, key):
        recipe = get_template(key)()
        assert isinstance(recipe, SpecRecipe)
        assert recipe_from(recipe) is recipe

    def test_recipe_from_error_mentions_spec_recipe(self):
        with pytest.raises(TypeError, match="SpecRecipe"):
            recipe_from(object())

    @pytest.mark.parametrize("key,mapping", LEGACY_RENDER_CASES)
    def test_legacy_factory_renders_via_pipeline(self, key, mapping):
        figures = render_template(data=make_df(), template=key, mapping=mapping)
        assert len(figures) == 1

    @pytest.mark.parametrize("key,mapping", LEGACY_RENDER_CASES)
    def test_legacy_keys_honor_settings(self, key, mapping):
        figures = render_template(
            data=make_df(), template=key, mapping=mapping,
            settings={"title": "T"},
        )
        assert figures[0].axes[0].get_title() == "T"

    def test_histogram_settings_honor_bins(self):
        figures = render_template(
            data=make_df(), template="histogram", mapping={"x": "x"},
            settings={"bins": 5},
        )
        assert len(figures[0].axes[0].patches) == 5

    def test_histogram_mapping_bins_mapped_column(self):
        df = make_df()
        df["other_col"] = [10.0, 20.0, 30.0, 40.0]
        figures = render_template(
            data=df, template="histogram", mapping={"x": "other_col"},
            settings={"bins": 4},
        )
        centers = [
            patch.get_x() + patch.get_width() / 2
            for patch in figures[0].axes[0].patches
        ]
        assert min(centers) > 5.0
        assert max(centers) < 45.0

    def test_piper_key_renders_linked_spec(self):
        recipe = get_template("piper")()
        specs = recipe.build_specs(
            make_piper_df(), None, recipe.default_settings, None
        )
        assert len(specs) == 1
        assert len(specs[0].children) == 3

        figures = render_template(data=make_piper_df(), template="piper")
        assert len(figures) == 1
        assert len(figures[0].axes) == 1

    def test_stiff_key_renders_one_figure(self):
        figures = render_template(data=make_stiff_df(), template="stiff")
        assert len(figures) == 1
        assert len(figures[0].axes) == 1

    def test_spec_recipe_uses_savedir_persistence(self, tmp_path):
        render_template(data=make_stiff_df(), template="stiff", savedir=tmp_path)
        assert (tmp_path / "001.png").is_file()
        assert (tmp_path / "legend.png").is_file()

    def test_piper_settings_override_reaches_render(self):
        figures = render_template(
            data=make_piper_df(), template="piper", settings={"title": "Piper T"}
        )
        assert figures[0]._suptitle.get_text() == "Piper T"

    def test_stiff_settings_override_reaches_render(self):
        figures = render_template(
            data=make_stiff_df(),
            template="stiff",
            settings={"title": "Stiff T", "figsize": (7, 5)},
        )
        assert figures[0]._suptitle.get_text() == "Stiff T"
        assert figures[0].get_size_inches().tolist() == [7.0, 5.0]

    @pytest.mark.parametrize("key", SPEC_RECIPE_KEYS)
    def test_spec_recipes_reject_iterators(self, key):
        from geofig_engine.core.iterator import DimensionIterator

        iterator = DimensionIterator(channel="group", dimensions=["group"])
        with pytest.raises(ValueError, match="Unsupported combination"):
            render_template(data=make_df(), template=key, iterators=[iterator])

    @pytest.mark.parametrize("key", SPEC_RECIPE_KEYS)
    def test_spec_recipes_reject_facets(self, key):
        from geofig_engine.core.facet import Facet

        facet = Facet(name="group", by=("group",))
        with pytest.raises(ValueError, match="Unsupported combination"):
            render_template(data=make_df(), template=key, facet=facet)


class TestLegacyVisualParity:
    """Rendered output of the legacy factories is unchanged on the new path."""

    @staticmethod
    def _png_hashes(directory: Path):
        hashes = {}
        for path in sorted(Path(directory).glob("*.png")):
            digest = hashlib.sha256()
            with open(path, "rb") as handle:
                digest.update(handle.read())
            hashes[path.name] = digest.hexdigest()
        return hashes

    @pytest.mark.parametrize("key,mapping", LEGACY_RENDER_CASES)
    def test_factory_key_output_unchanged_vs_legacy_path(self, key, mapping, tmp_path):
        from geofig_engine.core.dataset import Dataset
        from geofig_engine.engine.entry import render_template_legacy

        canonical_dir = tmp_path / f"{key}_canonical"
        legacy_dir = tmp_path / f"{key}_legacy"

        render_template(
            data=make_df(),
            template=key,
            mapping=mapping,
            savedir=str(canonical_dir),
        )
        with pytest.warns(DeprecationWarning, match="render_template_legacy"):
            render_template_legacy(
                dataset=Dataset(dataframe=make_df(), key_column="id"),
                template=NATIVE_FACTORIES[key](mapping=mapping),
                savedir=str(legacy_dir),
            )

        assert self._png_hashes(canonical_dir) == self._png_hashes(legacy_dir)

    def test_stiff_specs_render_deterministically(self, tmp_path):
        # The registry recipe reuses this same spec path; pin determinism so
        # renderer changes are caught.
        from io import BytesIO

        from geofig_engine.renderers import MatplotlibRenderer
        from geofig_engine.templates import plot_stiff

        renderer = MatplotlibRenderer()
        renders = []
        for _ in range(2):
            figures = renderer.render_all([plot_stiff(50, 20, 30, 40, 10, 30)])
            buffer = BytesIO()
            figures[0].savefig(buffer, format="png")
            renders.append(buffer.getvalue())
        assert renders[0] == renders[1]