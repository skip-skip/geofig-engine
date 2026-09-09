"""Tests for the stiff-as-cartesian template (Phase 14.59 WP6).

Covers the spec-level contract of ``plot_stiff``: cartesian coord, symmetric
ab-ticks ruler, named cation/anion rows, raw signed meq/L polygon data,
decorative layers, serialization, and a render smoke test.
"""

import numpy as np
import pandas as pd
import pytest

import matplotlib
matplotlib.use("Agg")
from matplotlib.patches import Polygon as MplPolygon

from geofig_engine.core.axis import parse_axis_settings
from geofig_engine.core.coord import CoordCartesian
from geofig_engine.core.geom import GeomLine, GeomPolygon
from geofig_engine.core.spec import FigureSpec
from geofig_engine.renderers.matplotlib.renderer import _nice_tick_max
from geofig_engine.serialize import spec_from_json, spec_to_json
from geofig_engine.templates import plot_stiff

CATIONS = {0: "Mg\u00b2\u207a", 1: "Ca\u00b2\u207a", 2: "Na\u207a+K\u207a"}
ANIONS = {0: "SO\u2084\u00b2\u207b", 1: "HCO\u2083\u207b", 2: "Cl\u207b"}


class TestNiceTickMax:
    def test_typical_meq(self):
        assert _nice_tick_max(15) == 20

    def test_large_saline(self):
        assert _nice_tick_max(580) == 1000

    def test_small_fresh(self):
        assert _nice_tick_max(3) == 5

    def test_minimum_value(self):
        assert _nice_tick_max(1) == 1


class TestStiffSpecContract:
    _SAMPLE = dict(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3)

    def _spec(self, **kw):
        return plot_stiff(**{**self._SAMPLE, **kw})

    def test_returns_figure_spec_with_unchanged_template_name(self):
        spec = self._spec()
        assert isinstance(spec, FigureSpec)
        assert spec.template_name == "stiff"

    def test_coord_is_cartesian(self):
        spec = self._spec()
        assert isinstance(spec.coord, CoordCartesian)
        assert spec.coord.name == "cartesian"

    def test_symmetric_xlim_about_zero(self):
        spec = self._spec()
        xlo, xhi = spec.settings["xlim"]
        assert xlo == pytest.approx(-xhi)
        assert xlo < 0.0 < xhi

    def test_x_ruler_uses_half_tick_max(self):
        spec = self._spec()
        tick_max = _nice_tick_max(max(self._SAMPLE.values()))
        assert spec.settings["xlim"] == (-1.5 * tick_max, 1.5 * tick_max)
        assert spec.settings["tick_step"] == pytest.approx(tick_max / 2.0)
        assert spec.settings["abs_ticks"] is True
        assert spec.settings["xlabel"] == "meq/L"

    def test_row_grid_off(self):
        spec = self._spec()
        assert spec.settings["grid"] is False

    def test_ylim_room_above_and_below_rows(self):
        assert self._spec().settings["ylim"] == (-0.55, 2.5)

    def test_cation_labels_declared_on_left_y(self):
        spec = self._spec()
        assert spec.settings["y_tick_labels"] == CATIONS

    def test_anion_labels_declared_on_secondary_y(self):
        spec = self._spec()
        assert spec.settings["secondary_y"]["tick_labels"] == ANIONS

    def test_secondary_y_range_matches_ylim_for_row_alignment(self):
        spec = self._spec()
        assert spec.settings["secondary_y"]["range"] == list(spec.settings["ylim"])


class TestPlotStiffLayersAndData:
    def test_figsize_honored(self):
        spec = plot_stiff(ca=1, mg=1, na_k=1, cl=1, hco3=1, so4=1, figsize=(8, 8))
        assert spec.settings["figsize"] == (8, 8)

    def test_title_lands_in_settings(self):
        spec = plot_stiff(ca=1, mg=1, na_k=1, cl=1, hco3=1, so4=1, title="Test")
        assert spec.settings["title"] == "Test"

    def test_polygon_raw_signed_meq_coordinates(self):
        spec = plot_stiff(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3)
        x = spec.data["x"].tolist()
        y = spec.data["y"].tolist()
        assert len(x) == len(y) == 7
        # Cations on the left are negative (-na_k, -ca, -mg) at y = 2, 1, 0.
        assert x[:3] == [-8, -10, -5]
        assert y[:3] == [2, 1, 0]
        # Anions on the right are positive (+cl, +hco3, +so4) at y = 0, 1, 2.
        assert x[3:6] == [12, 15, 3]
        assert y[3:6] == [0, 1, 2]
        # Closing back to the first vertex (-na_k, y=2).
        assert x[6] == -8 and y[6] == 2

    def test_polygon_vertices_signed_by_side(self):
        spec = plot_stiff(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3)
        x = spec.data["x"].tolist()
        assert all(v < 0 for v in x[:3])
        assert all(v > 0 for v in x[3:6])

    def test_layers_are_polygon_and_clipped_dashed_center(self):
        spec = plot_stiff(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3)
        assert [layer.geom.name for layer in spec.layers] == ["polygon", "line"]
        polygon = spec.layers[0].geom
        assert isinstance(polygon, GeomPolygon)
        assert polygon.edgecolor == "black"
        assert polygon.edgewidth == 1.5
        assert spec.layers[0].visual_mapping["color"] == "lightblue"
        divider = spec.layers[1]
        assert isinstance(divider.geom, GeomLine)
        assert divider.visual_mapping["x"] == [0, 0]
        # The segment spans exactly the frame box so it never leaks past the
        # axis bounds into the caption strip or above the box.
        assert divider.visual_mapping["y"] == list(spec.settings["ylim"])
        assert divider.visual_mapping["style"] == "dashed"

    def test_serialization_roundtrip_preserves_data_and_settings(self):
        spec = plot_stiff(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3, title="Well 1")
        restored = spec_from_json(spec_to_json(spec))
        assert restored.template_name == "stiff"
        pd.testing.assert_frame_equal(restored.data, spec.data)
        assert restored.settings["title"] == "Well 1"
        assert restored.settings["xlabel"] == "meq/L"
        assert isinstance(restored.coord, CoordCartesian)
        axis = parse_axis_settings(restored.settings, restored.coord)
        source = parse_axis_settings(spec.settings, spec.coord)
        assert axis.xlim == source.xlim
        assert axis.tick_step == source.tick_step
        assert axis.abs_ticks is True
        # JSON normalizes dict keys to strings; compare after casting back.
        cation_labels = {int(k): v for k, v in restored.settings["y_tick_labels"].items()}
        assert cation_labels == CATIONS
        anion_labels = {
            int(k): v
            for k, v in restored.settings["secondary_y"]["tick_labels"].items()
        }
        assert anion_labels == ANIONS

    def test_serialization_roundtrip_preserves_layers(self):
        spec = plot_stiff(ca=1, mg=1, na_k=1, cl=8, hco3=1, so4=1)
        restored = spec_from_json(spec_to_json(spec))
        assert [layer.geom.name for layer in restored.layers] == ["polygon", "line"]
        assert isinstance(restored.layers[0].geom, GeomPolygon)


class TestStiffRenderSmoke:
    def _render(self):
        from geofig_engine.renderers import MatplotlibRenderer

        renderer = MatplotlibRenderer()
        spec = plot_stiff(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3, title="Smoke")
        assert renderer.supports(spec) is True
        return renderer.render(spec), spec

    def test_single_axes_with_filled_polygon(self):
        fig, _ = self._render()
        assert len(fig.axes) == 1
        ax = fig.axes[0]
        assert any(isinstance(p, MplPolygon) for p in ax.patches)

    def test_cation_and_anion_labels_render(self):
        fig, _ = self._render()
        texts = [t.get_text() for t in fig.axes[0].texts]
        for label in (*CATIONS.values(), *ANIONS.values()):
            assert label in texts

    def test_meq_caption_renders(self):
        fig, _ = self._render()
        texts = {t.get_text() for t in fig.axes[0].texts}
        assert "meq/L" in texts

    def test_abs_x_tick_labels(self):
        fig, _ = self._render()
        ticks = {
            t.get_text()
            for t in fig.axes[0].texts
            if t.get_text().isdigit() and np.asarray(t.get_position())[1] < 0
        }
        assert ticks == {"0", "10", "20"}

    def test_x_labels_and_caption_within_viewport(self):
        """Regression: the x-scale and meq/L caption must not clip off-canvas."""
        fig, _ = self._render()
        ax = fig.axes[0]
        ymin = ax.get_ylim()[0]
        labels = {t.get_text(): t for t in ax.texts}
        for text in (labels.get("meq/L"), labels.get("10"), labels.get("20")):
            assert text is not None
            assert text.get_position()[1] >= ymin - 1e-9

    def test_no_interior_grid_or_mid_line(self):
        fig, _ = self._render()
        ax = fig.axes[0]
        assert not any(line.get_linestyle() == ":" for line in ax.lines)

    def test_x_axis_majorticks_at_interval_numbers(self):
        fig, spec = self._render()
        ax = fig.axes[0]
        ylo, yhi = spec.settings["ylim"]
        length = spec.settings["majortick_length"]
        nubs = {}
        for line in ax.lines:
            xs = np.asarray(line.get_xdata())
            ys = np.asarray(line.get_ydata())
            if len(xs) == 2 and np.allclose(xs, xs[0]) and abs(ys[1] - ys[0]) == pytest.approx(length):
                nubs[round(float(xs[0]), 6)] = line
        for tx in (-20, -10, 0, 10, 20):
            assert tx in nubs, f"missing majortick at x={tx}"
            line = nubs[tx]
            ys = np.asarray(line.get_ydata())
            # majortick_offset 0 -> entirely exterior, below the frame edge.
            assert float(min(ys)) == pytest.approx(ylo - length, abs=1e-9)
            assert float(max(ys)) == pytest.approx(ylo, abs=1e-9)
            assert line.get_linewidth() == pytest.approx(
                spec.settings.get("majortick_width", 1.0)
            )
            assert line.get_color() == spec.settings.get("majortick_color", "black")

    def test_title_renders_as_suptitle(self):
        fig, _ = self._render()
        assert fig._suptitle.get_text() == "Smoke"

    def test_y_limits_are_not_collapsed_by_equal_aspect(self):
        """Regression: the wide stiff frame must not squash the y range."""
        fig, _ = self._render()
        ax = fig.axes[0]
        y0, y1 = ax.get_ylim()
        assert y1 - y0 < 8  # aspect-equal would expand this to ~50+
        assert ax.get_aspect() != 1