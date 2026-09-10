"""
Phase 15 wp10: particle_overlay registry template.

Covers the spec-build stat (per-mode derivation: image anchor + array-cell
extraction with a clear error when the source image is absent, contour-ring
explosion with closed rings and NaN separators, canonical color/size columns
with NaN fallbacks, the QA caption content and top-left anchor, candidate
detection incl. the real ``ParticleImageModel`` aliases ``phase``/``area_px``
and the upstream ``source`` image alias), registry resolution + recipe shape,
mapping-free rendering via ``render_template`` (image inset, contour line,
classified points sized by area, QA caption), the real-model-shape render,
mapping-merge overrides, the "no blank figure" image-absent error, the
synthetic-image fixture (no cv2/skimage dependency), grouped legend sections,
and the matplotlib-free spec-build guard.
"""

import builtins

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest
import pandas as pd

from geofig_engine import TEMPLATES, get_template, render_template
from geofig_engine.core.coord import CoordCartesian
from geofig_engine.core.geom import (
    GeomBoundary,
    GeomImageInset,
    GeomPoint,
    GeomText,
)
from geofig_engine.engine.api import recipe_from
from geofig_engine.engine.generator import FigureGenerator
from geofig_engine.provider import DataFrameProvider
from geofig_engine.renderers.matplotlib.legend import LegendAccumulator
from geofig_engine.templates.particle_overlay import (
    PARTICLE_OVERLAY_DEFAULTS,
    StatParticleOverlay,
    particle_overlay_builder,
)

# ---------------------------------------------------------------------------
# Synthetic fixtures (no cv2/skimage)
# ---------------------------------------------------------------------------

# 64 x 48 gray gradient: the (downsampled) source image for every particle row.
_GRADIENT = np.tile(
    np.linspace(0, 255, 64, dtype=np.uint8), (48, 1)
)  # 48 rows (y), 64 cols (x)


def _ring(x_center: float, y_center: float, half: float = 3.0) -> tuple[list, list]:
    """Closed square ring around ``(x_center, y_center)`` (4 vertices)."""
    xs = [x_center - half, x_center + half, x_center + half, x_center - half]
    ys = [y_center - half, y_center - half, y_center + half, y_center + half]
    return xs, ys


_RING1 = _ring(16.0, 12.0)
_RING2 = _ring(32.0, 24.0)
_RING3 = _ring(48.0, 12.0)
_RING4 = _ring(24.0, 36.0)

# Duck-typed particles frame: centroids, class, area, QA columns, contour
# vertex lists, and the source-image array cell.
PARTICLES_DF = pd.DataFrame(
    {
        "particle_id": [1, 2, 3, 4],
        "x": [16.0, 32.0, 48.0, 24.0],
        "y": [12.0, 24.0, 12.0, 36.0],
        "class": [
            "late_brightness",
            "standard",
            "late_brightness",
            "standard",
        ],
        "area_px": [120.0, 300.0, 60.0, 180.0],
        "qa_flag": [False, False, True, False],
        "mean_intensity": [200.0, 150.0, 90.0, 170.0],
        "contour_x": [_RING1[0], _RING2[0], _RING3[0], _RING4[0]],
        "contour_y": [_RING1[1], _RING2[1], _RING3[1], _RING4[1]],
        "image": [_GRADIENT] * 4,
    }
)

# Real ParticleImageModel tables shape: `phase` (not `class`), `area_px`,
# `mean_intensity`, `solidity`, `qa_flag`, plus `excluded_fraction` (no
# qa_flag on this variant).
_RING_A = _ring(20.0, 15.0)
_RING_B = _ring(40.0, 30.0)
_RING_C = _ring(30.0, 25.0)
REAL_MODEL_DF = pd.DataFrame(
    {
        "particle_id": [1, 2, 3],
        "phase": ["late_brightness", "standard", "late_brightness"],
        "area_px": [150.0, 90.0, 240.0],
        "mean_intensity": [160.0, 120.0, 180.0],
        "solidity": [0.90, 0.80, 0.95],
        "excluded_fraction": [0.0, 0.0, 0.0],
        "x": [20.0, 40.0, 30.0],
        "y": [15.0, 30.0, 25.0],
        "contour_x": [_RING_A[0], _RING_B[0], _RING_C[0]],
        "contour_y": [_RING_A[1], _RING_B[1], _RING_C[1]],
        "image": [_GRADIENT] * 3,
    }
)


class TestStatParticleOverlay:
    def test_image_mode_returns_anchor_and_array(self):
        out = StatParticleOverlay(mode="image").compute(PARTICLES_DF)
        assert list(out.columns) == ["x", "y", "image"]
        assert len(out) == 1
        # anchor = centroid mean; the array cell is the source image
        assert out["x"].iloc[0] == pytest.approx(30.0)
        assert out["y"].iloc[0] == pytest.approx(21.0)
        assert isinstance(out["image"].iloc[0], np.ndarray)
        assert out["image"].iloc[0].shape == (48, 64)

    def test_image_mode_first_non_null_cell(self):
        frame = PARTICLES_DF.iloc[:2].copy()
        frame.loc[frame.index[0], "image"] = None
        out = StatParticleOverlay(mode="image").compute(frame)
        assert np.array_equal(out["image"].iloc[0], _GRADIENT)

    def test_image_mode_missing_column_raises_clear_error(self):
        frame = PARTICLES_DF.drop(columns=["image"])
        with pytest.raises(ValueError, match="image"):
            StatParticleOverlay(mode="image").compute(frame)

    def test_image_mode_all_null_cells_raises(self):
        frame = PARTICLES_DF.iloc[:2].copy()
        frame["image"] = [None, None]
        with pytest.raises(ValueError, match="image"):
            StatParticleOverlay(mode="image").compute(frame)

    def test_image_alias_source_detected(self):
        # Upstream VisualizationEncoding binds the image channel to the
        # "source" artifact, so the column may arrive named "source".
        frame = PARTICLES_DF.rename(columns={"image": "source"})
        out = StatParticleOverlay(mode="image").compute(frame)
        assert np.array_equal(out["image"].iloc[0], _GRADIENT)

    def test_points_mode_canonical_columns_and_passthrough(self):
        out = StatParticleOverlay(mode="points").compute(PARTICLES_DF)
        assert {"x", "y", "color", "size"} <= set(out.columns)
        # full-frame passthrough: override providers can remap onto originals
        assert {"particle_id", "area_px", "mean_intensity"} <= set(out.columns)
        assert out["x"].tolist() == [16.0, 32.0, 48.0, 24.0]
        assert out["y"].tolist() == [12.0, 24.0, 12.0, 36.0]
        assert out["color"].tolist() == [
            "late_brightness", "standard", "late_brightness", "standard",
        ]
        assert out["size"].tolist() == [120.0, 300.0, 60.0, 180.0]
        # index-aligned with the provider frame (legend accumulation)
        assert out.index.tolist() == PARTICLES_DF.index.tolist()

    def test_points_mode_phase_alias_and_nan_fallbacks(self):
        frame = pd.DataFrame(
            {
                "x": [1.0, 2.0],
                "y": [3.0, 4.0],
                "phase": ["A", None],
                "area_px": [10.0, np.nan],
            }
        )
        out = StatParticleOverlay(mode="points").compute(frame)
        assert out["color"].tolist() == ["A", "Particles"]
        assert out["size"].tolist() == [10.0, 20.0]

    def test_points_mode_neutral_color_without_class_column(self):
        frame = PARTICLES_DF.drop(columns=["class", "area_px"]).copy()
        out = StatParticleOverlay(mode="points").compute(frame)
        assert out["color"].tolist() == ["Particles"] * 4
        assert out["size"].tolist() == [20.0] * 4

    def test_points_mode_missing_coordinates_raise(self):
        with pytest.raises(ValueError, match="centroid"):
            StatParticleOverlay(mode="points").compute(
                pd.DataFrame({"a": [1], "b": [2], "class": ["A"]})
            )

    def test_points_mode_explicit_override_wins(self):
        frame = PARTICLES_DF.rename(columns={"x": "my_x", "y": "my_y"})
        out = StatParticleOverlay(
            mode="points", x_source="my_x", y_source="my_y"
        ).compute(frame)
        assert out["x"].tolist() == [16.0, 32.0, 48.0, 24.0]

    def test_contours_explodes_closed_rings_with_nan_separators(self):
        out = StatParticleOverlay(mode="contours").compute(PARTICLES_DF)
        assert list(out.columns) == ["x", "y"]
        # 4 rings x 5 vertices (closed) + 3 NaN separators, trailing dropped
        assert len(out) == 4 * 5 + 3
        assert out["x"].isna().sum() == 3
        xs = out["x"].tolist()
        assert xs[0] == 13.0  # ring 1 first vertex
        assert xs[4] == 13.0  # ring 1 closure repeats the first vertex
        # each ring is closed (first == last non-NaN of its run)
        for start in (0, 6, 12, 18):
            assert xs[start] == xs[start + 4]

    def test_contours_skips_missing_and_degenerate_rings(self):
        frame = pd.DataFrame(
            {
                "x": [1.0, 2.0, 3.0],
                "y": [1.0, 2.0, 3.0],
                "contour_x": [None, [0.0, 1.0], [5.0, 7.0, 7.0, 5.0]],
                "contour_y": [None, [0.0, 1.0], [5.0, 5.0, 7.0, 7.0]],
            }
        )
        out = StatParticleOverlay(mode="contours").compute(frame)
        # only the 4-vertex ring survives, closed -> 5 points, no separator
        assert out["x"].tolist() == [5.0, 7.0, 7.0, 5.0, 5.0]
        assert not out["x"].isna().any()

    def test_contours_empty_without_contour_columns(self):
        frame = PARTICLES_DF.drop(columns=["contour_x", "contour_y"])
        out = StatParticleOverlay(mode="contours").compute(frame)
        assert list(out.columns) == ["x", "y"]
        assert len(out) == 0

    def test_contours_explicit_column_override(self):
        frame = PARTICLES_DF.rename(
            columns={"contour_x": "cx_ring", "contour_y": "cy_ring"}
        )
        out = StatParticleOverlay(
            mode="contours",
            contour_x_source="cx_ring",
            contour_y_source="cy_ring",
        ).compute(frame)
        assert len(out) == 4 * 5 + 3

    def test_contours_missing_explicit_column_raises(self):
        with pytest.raises(ValueError, match="contour column 'cx' not found"):
            StatParticleOverlay(
                mode="contours", contour_x_source="cx"
            ).compute(PARTICLES_DF)

    def test_qa_caption_content_and_anchor(self):
        out = StatParticleOverlay(mode="qa").compute(PARTICLES_DF)
        assert list(out.columns) == ["x", "y", "label", "size"]
        label = out["label"].iloc[0]
        assert "n=4 particles" in label
        assert "mean area 165 px²" in label
        assert "mean intensity 152.5" in label
        assert "excluded 25%" in label  # qa_flag => excluded-fraction branch
        assert out["size"].tolist() == [9.0]
        # top-left of the centroid extent: x_min + 3% span, y_max - 5% span
        assert out["x"].iloc[0] == pytest.approx(16.0 + 0.03 * 32.0)
        assert out["y"].iloc[0] == pytest.approx(36.0 - 0.05 * 24.0)

    def test_qa_uses_excluded_fraction_when_no_flag(self):
        out = StatParticleOverlay(mode="qa").compute(REAL_MODEL_DF)
        label = out["label"].iloc[0]
        assert "n=3 particles" in label
        assert "excluded 0%" in label
        assert "mean area 160 px²" in label

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValueError, match="mode"):
            StatParticleOverlay(mode="nope")


class TestParticleOverlayTemplate:
    def test_registered_and_resolvable(self):
        assert "particle_overlay" in TEMPLATES
        assert callable(get_template("particle_overlay"))

    def test_builder_returns_recipe_with_defaults(self):
        recipe = get_template("particle_overlay")()
        assert recipe.name == "particle_overlay"
        assert len(recipe.layers) == 4
        assert [layer.zorder for layer in recipe.layers] == [1, 2, 3, 4]
        assert isinstance(recipe.coord, CoordCartesian)
        assert recipe.default_settings == {**PARTICLE_OVERLAY_DEFAULTS}
        assert isinstance(recipe.layers[0].geom, GeomImageInset)
        assert isinstance(recipe.layers[1].geom, GeomBoundary)
        assert recipe.layers[1].geom.edgecolor == "white"
        assert isinstance(recipe.layers[2].geom, GeomPoint)
        assert isinstance(recipe.layers[3].geom, GeomText)
        # string-bound channel mappings (override-able per layer)
        assert recipe.layers[0].mapping == {"x": "x", "y": "y", "image": "image"}
        assert recipe.layers[2].mapping == {
            "x": "x", "y": "y", "color": "color", "size": "size",
        }

    def test_builder_settings_propagate(self):
        recipe = particle_overlay_builder(
            settings={"inset_zoom": 3.5, "qa_fontsize": 11.0}
        )
        assert recipe.layers[0].geom.zoom == 3.5
        assert recipe.layers[3].stat.qa_fontsize == 11.0

    def test_builder_direct_mapping_pins_stat_sources(self):
        recipe = particle_overlay_builder(
            mapping={
                "x": "cx",
                "y": "cy",
                "class": "phase",
                "area": "area_px",
                "image": "source",
                "contour_x": "cx_ring",
                "contour_y": "cy_ring",
            }
        )
        points_stat = recipe.layers[2].stat
        assert points_stat.x_source == "cx"
        assert points_stat.y_source == "cy"
        assert points_stat.class_source == "phase"
        assert points_stat.area_source == "area_px"
        assert recipe.layers[0].stat.image_source == "source"
        assert recipe.layers[1].stat.contour_x_source == "cx_ring"
        assert recipe.layers[1].stat.contour_y_source == "cy_ring"


class TestParticleOverlayRender:
    def test_no_mapping_renders_full_stack(self):
        # AC1: source image, particle contours, classified points, QA caption
        figures = render_template(data=PARTICLES_DF, template="particle_overlay")
        assert len(figures) == 1
        ax = figures[0].axes[0]
        # image inset: one OffsetImage/AnnotationBbox artist
        assert len(ax.artists) == 1
        # contours: one broken polyline with NaN separators
        assert len(ax.lines) == 1
        xd = np.asarray(ax.lines[0].get_xdata(), dtype=float)
        assert xd[0] == xd[4]  # first ring closed
        assert np.isnan(xd).sum() == 3  # separators between the 4 rings
        # points: one per particle, colored by class, sized by area
        assert len(ax.collections) == 1
        offsets = ax.collections[0].get_offsets()
        assert len(offsets) == 4
        sizes = sorted(ax.collections[0].get_sizes().tolist())
        assert sizes == [60.0, 120.0, 180.0, 300.0]
        colors = ax.collections[0].get_facecolors()
        assert np.allclose(colors[0], colors[2])  # late_brightness
        assert np.allclose(colors[1], colors[3])  # standard
        assert not np.allclose(colors[0], colors[1])
        # QA caption text
        assert any("n=4 particles" in t.get_text() for t in ax.texts)

    def test_render_real_model_shape(self):
        # AC2: real ParticleImageModel tables shape — phase alias, area_px,
        # contour vertices, centroid, qa_flag/excluded_fraction columns.
        figures = render_template(data=REAL_MODEL_DF, template="particle_overlay")
        assert len(figures) == 1
        ax = figures[0].axes[0]
        assert len(ax.artists) == 1
        assert len(ax.lines) == 1
        colors = ax.collections[0].get_facecolors()
        assert np.allclose(colors[0], colors[2])  # late_brightness
        assert not np.allclose(colors[0], colors[1])
        sizes = sorted(ax.collections[0].get_sizes().tolist())
        assert sizes == [90.0, 150.0, 240.0]
        assert any("n=3 particles" in t.get_text() for t in ax.texts)

    def test_mapping_override_merges_on_top_of_defaults(self):
        # AC3: mapping overrides accepted — a class column outside the
        # candidate names is honored through the per-layer channel override
        # (render_template maps channels: the color channel remaps onto the
        # "cls" column, which the points stat passthrough preserves).
        frame = PARTICLES_DF.rename(columns={"class": "cls"})
        figures = render_template(
            data=frame,
            template="particle_overlay",
            mapping={"color": "cls"},
        )
        colors = figures[0].axes[0].collections[0].get_facecolors()
        assert np.allclose(colors[0], colors[2])  # late_brightness
        assert np.allclose(colors[1], colors[3])  # standard
        assert not np.allclose(colors[0], colors[1])

    def test_contours_optional(self):
        frame = PARTICLES_DF.drop(columns=["contour_x", "contour_y"])
        figures = render_template(data=frame, template="particle_overlay")
        ax = figures[0].axes[0]
        assert len(ax.lines) == 0  # no contour columns -> nothing drawn
        assert len(ax.collections[0].get_offsets()) == 4

    def test_image_absent_raises_clear_error(self):
        # AC6: no blank figure — a missing image column is a clear error.
        frame = PARTICLES_DF.drop(columns=["image"])
        with pytest.raises(ValueError, match="image"):
            render_template(data=frame, template="particle_overlay")

    def test_grouped_legend_sections(self):
        # Single "Particles" section: entries per distinct class, colors from
        # the resolved color series (size/QA/image channels are not legend
        # channels, so no extra sections accumulate).
        recipe = recipe_from(get_template("particle_overlay")())
        generator = FigureGenerator(
            provider=DataFrameProvider(PARTICLES_DF),
            layers=recipe.layers,
            coord=recipe.coord,
            settings=recipe.default_settings,
        )
        accumulator = LegendAccumulator()
        for spec in generator.build_specs():
            accumulator.add_from_spec(spec)

        assert len(accumulator.groups) == 1
        group = accumulator.groups[0]
        assert group.column == "color"
        assert {entry.label for entry in group.entries} == {
            "late_brightness",
            "standard",
        }
        assert len({entry.color for entry in group.entries}) == 2


class TestSpecBuildIsMatplotlibFree:
    def test_spec_build_has_no_matplotlib_or_scipy(self, monkeypatch):
        # AC4: mock-import guard, like dendrogram.
        real_import = builtins.__import__

        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"scipy", "matplotlib"}:
                raise AssertionError(f"{name} imported during spec build")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", guarded)

        from geofig_engine.core.facet import FacetNull
        from geofig_engine.engine.generator import FigureGenerator
        from geofig_engine.provider import DataFrameProvider

        recipe = get_template("particle_overlay")()
        generator = FigureGenerator(
            provider=DataFrameProvider(PARTICLES_DF),
            layers=recipe.layers,
            coord=recipe.coord,
            facet=FacetNull(),
            settings=recipe.default_settings,
            iterators=[],
        )
        specs = generator.build_specs()
        assert len(specs) == 1
        assert len(specs[0].layers) == 4