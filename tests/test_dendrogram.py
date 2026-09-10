"""
Phase 15 wp7: dendrogram registry template.

Covers the pure linkage->coordinate layout (hand-computed for a known
4-leaf matrix), registry resolution, mapping-free rendering via
``render_template``, the matplotlib/scipy-free spec build, malformed-input
errors, and the monotonicity warning.
"""

import builtins

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest
import pandas as pd

from geofig_engine import TEMPLATES, get_template, render_template
from geofig_engine.templates.dendrogram import (
    DENDROGRAM_DEFAULTS,
    StatDendrogram,
    _dendrogram_coords,
)

# Known 4-leaf linkage: rows are [left, right, distance, count], clusters
# get ids n, n+1, ... Hand-computed layout:
#   leaves 0..3 at x=0..3 (in-order); cluster 4=(0,1)@x=0.5 h=1;
#   cluster 5=(2,3)@x=2.5 h=2; cluster 6=(4,5)@x=1.5 h=3.
LINKAGE = np.array(
    [
        [0, 1, 1.0, 2],
        [2, 3, 2.0, 2],
        [4, 5, 3.0, 4],
    ],
    dtype=float,
)

LINKAGE_DF = pd.DataFrame(LINKAGE, columns=["left", "right", "distance", "count"])

EXPECTED_SEGMENTS = [
    (0.0, 0.0, 0.5, 1.0),   # merge 4: arm to leaf 0
    (0.5, 1.0, 1.0, 0.0),   # merge 4: arm to leaf 1
    (2.0, 0.0, 2.5, 2.0),   # merge 5: arm to leaf 2
    (2.5, 2.0, 3.0, 0.0),   # merge 5: arm to leaf 3
    (0.5, 1.0, 1.5, 3.0),   # merge 6: arm to cluster 4
    (1.5, 3.0, 2.5, 2.0),   # merge 6: arm to cluster 5
]


def rendered_line_segments(fig):
    """Count the discrete segments drawn by the broken dendrogram line."""
    ax = fig.axes[0]
    assert len(ax.lines) == 1
    xd = np.asarray(ax.lines[0].get_xdata(), dtype=float)
    finite = np.isfinite(xd)
    return int(np.count_nonzero(finite[1:] & finite[:-1]))


class TestDendrogramCoords:
    def test_known_linkage_hand_computed(self):
        coords = _dendrogram_coords(LINKAGE)
        assert coords["leaf_order"] == [0, 1, 2, 3]
        assert coords["leaf_x"].tolist() == [0.0, 1.0, 2.0, 3.0]
        assert coords["max_height"] == 3.0
        assert coords["segments"] == EXPECTED_SEGMENTS
        assert len(coords["segments"]) == 2 * (len(LINKAGE))  # 2*(n-1)

    def test_edge_count_is_two_per_merge(self):
        coords = _dendrogram_coords(LINKAGE)
        n_rows = LINKAGE.shape[0]
        assert len(coords["segments"]) == 2 * n_rows

    def test_malformed_shapes_raise(self):
        with pytest.raises(ValueError, match="2-D"):
            _dendrogram_coords(np.array([1.0, 2.0]))  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="4 columns"):
            _dendrogram_coords(np.zeros((3, 3)))
        with pytest.raises(ValueError, match="at least one merge"):
            _dendrogram_coords(np.zeros((0, 4)))
        with pytest.raises(ValueError, match="node ids"):
            bad = LINKAGE.copy()
            bad[0, 0] = 99
            _dendrogram_coords(bad)

    def test_nan_distances_raise(self):
        bad = LINKAGE.copy()
        bad[1, 2] = np.nan
        with pytest.raises(ValueError, match="finite"):
            _dendrogram_coords(bad)

    def test_non_monotone_distances_warn(self):
        bad = np.array([[0, 1, 3.0, 2], [2, 3, 1.0, 2]], dtype=float)
        with pytest.warns(UserWarning, match="monoton"):
            _dendrogram_coords(bad)


class TestStatDendrogram:
    def test_edges_mode_broken_line(self):
        out = StatDendrogram(mode="edges").compute(LINKAGE_DF)
        assert list(out.columns) == ["x", "y"]
        # 2 arms per merge, 3 entries per arm (x0, x1, NaN), trailing NaN dropped
        assert len(out) == 6 * len(LINKAGE) - 1
        assert out["x"].isna().sum() == 2 * len(LINKAGE) - 1

    def test_labels_mode(self):
        out = StatDendrogram(mode="labels").compute(LINKAGE_DF)
        assert list(out.columns) == ["x", "y", "label"]
        assert out["label"].tolist() == ["0", "1", "2", "3"]
        assert out["x"].tolist() == [0.0, 1.0, 2.0, 3.0]
        assert out["y"].tolist() == pytest.approx([-0.15] * 4)

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValueError, match="mode"):
            StatDendrogram(mode="nope")

    def test_missing_linkage_columns_raise(self):
        with pytest.raises(ValueError, match="4 columns"):
            StatDendrogram().compute(pd.DataFrame({"a": [1], "b": [2]}))


class TestDendrogramTemplate:
    def test_registered_and_resolvable(self):
        assert "dendrogram" in TEMPLATES
        assert callable(get_template("dendrogram"))

    def test_builder_returns_recipe_with_defaults(self):
        recipe = get_template("dendrogram")()
        assert recipe.name == "dendrogram"
        assert len(recipe.layers) == 2
        assert recipe.default_settings["ylabel"] == "Distance"
        assert recipe.default_settings == {**DENDROGRAM_DEFAULTS}

    def test_render_dataframe_without_mapping(self):
        figures = render_template(data=LINKAGE_DF, template="dendrogram")
        assert len(figures) == 1
        ax = figures[0].axes[0]
        assert rendered_line_segments(figures[0]) == 2 * (len(LINKAGE))
        # one text per leaf, at the leaf x positions
        texts = sorted(ax.texts, key=lambda t: t.get_position()[0])
        assert len(texts) == 4
        assert [t.get_text() for t in texts] == ["0", "1", "2", "3"]
        assert [t.get_position()[0] for t in texts] == [0.0, 1.0, 2.0, 3.0]

    def test_render_ndarray_positional_columns(self):
        figures = render_template(data=LINKAGE, template="dendrogram")
        assert len(figures) == 1
        assert rendered_line_segments(figures[0]) == 2 * (len(LINKAGE))
        assert len(figures[0].axes[0].texts) == 4


class TestSpecBuildIsScipyMatplotlibFree:
    def test_stat_compute_has_no_scipy_or_matplotlib(self, monkeypatch):
        real_import = builtins.__import__

        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"scipy", "matplotlib"}:
                raise AssertionError(f"{name} imported during spec build")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", guarded)

        from geofig_engine.core.facet import FacetNull
        from geofig_engine.engine.generator import FigureGenerator
        from geofig_engine.provider import DataFrameProvider

        recipe = get_template("dendrogram")()
        generator = FigureGenerator(
            provider=DataFrameProvider(LINKAGE_DF),
            layers=recipe.layers,
            coord=recipe.coord,
            facet=FacetNull(),
            settings=recipe.default_settings,
            iterators=[],
        )
        specs = generator.build_specs()
        assert len(specs) == 1
        assert len(specs[0].layers) == 2