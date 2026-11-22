"""
Phase 15 wp6 / 18.4 wp1: registry-templated rendering through ``render_template``.

Covers the pipeline builders plus the ten legacy keys. The eight
``FigureTemplate`` factories now resolve to native ``*_builder`` functions;
``piper``/``stiff`` keep resolvable placeholders until 18.4 wp2 replaces them
with first-class spec recipes.
"""

import hashlib
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pytest
import pandas as pd

from geofig_engine import TEMPLATES, get_template, render_template
from geofig_engine.templates import (
    anp_agp_builder,
    histogram_builder,
    isotope_builder,
    nagph_nag_builder,
    npr_nnp_builder,
    pie_builder,
    radar_builder,
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

SPEC_BUILDER_KEYS = ["piper", "stiff"]

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

    @pytest.mark.parametrize("key,builder", NATIVE_BUILDERS.items())
    def test_factory_keys_seed_native_builders(self, key, builder):
        assert get_template(key) is builder

    def test_registry_seed_has_no_legacy_adapter(self):
        import inspect

        from geofig_engine.engine import api

        assert "legacy_adapter" not in inspect.getsource(api)

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

    @pytest.mark.parametrize("key", SPEC_BUILDER_KEYS)
    def test_spec_builder_keys_raise_with_guidance(self, key):
        with pytest.raises(TypeError, match="not registry-adaptable"):
            render_template(data=make_df(), template=key)


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

    def test_histogram_output_unchanged_vs_legacy_path(self, tmp_path):
        canonical_dir = tmp_path / "canon"
        legacy_dir = tmp_path / "legacy"

        render_template(
            data=make_df(),
            template="histogram",
            mapping={"x": "x"},
            savedir=str(canonical_dir),
        )

        from geofig_engine.core.dataset import Dataset
        from geofig_engine.engine.entry import render_template_legacy
        from geofig_engine.templates import histogram

        dataset = Dataset(dataframe=make_df(), key_column="id")
        with pytest.warns(DeprecationWarning, match="render_template_legacy"):
            render_template_legacy(
                dataset=dataset,
                template=histogram(mapping={"x": "x"}),
                savedir=str(legacy_dir),
            )

        assert self._png_hashes(canonical_dir) == self._png_hashes(legacy_dir)

    def test_stiff_specs_render_deterministically(self, tmp_path):
        # stiff/piper are spec builders the recipe pipeline cannot express;
        # their spec-based output is untouched by this ticket, so parity holds
        # by construction. Pin determinism so renderer changes are caught.
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