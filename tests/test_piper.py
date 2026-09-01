"""Tests for Piper diagram — declarative linked-axes spec (Phase 14.51)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import matplotlib
matplotlib.use("Agg")

from geofig_engine.core.coord import CoordCartesian, PiperCoord, TernaryCoord
from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.spec import FigureSpec
from geofig_engine.templates import build_piper_specs
from geofig_engine.serialize import coord_to_dict, coord_from_dict


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_DATA = pd.DataFrame({
    "Ca": [1.0, 2.0], "Mg": [0.5, 1.0], "Na+K": [0.3, 0.5],
    "HCO3": [2.0, 3.0], "SO4": [0.2, 0.4], "Cl": [0.1, 0.2],
})


# ---------------------------------------------------------------------------
# PiperCoord (still importable, deprecated)
# ---------------------------------------------------------------------------


class TestPiperCoord:
    def test_defaults(self):
        c = PiperCoord()
        assert c.name == "piper"
        assert c.params["left_tri"] == ["Ca", "Mg", "Na+K"]
        assert c.params["right_tri"] == ["HCO3", "SO4", "Cl"]

    def test_custom_columns(self):
        c = PiperCoord(
            left_tri=("Na", "K", "Ca"),
            right_tri=("Cl", "SO4", "HCO3"),
        )
        assert c.params["left_tri"] == ["Na", "K", "Ca"]
        assert c.params["right_tri"] == ["Cl", "SO4", "HCO3"]

    def test_serialization_roundtrip(self):
        c = PiperCoord(
            left_tri=("Ca", "Mg", "Na+K"),
            right_tri=("HCO3", "SO4", "Cl"),
        )
        d = coord_to_dict(c)
        restored = coord_from_dict(d)
        assert isinstance(restored, PiperCoord)
        assert restored.params["left_tri"] == ["Ca", "Mg", "Na+K"]
        assert restored.params["right_tri"] == ["HCO3", "SO4", "Cl"]


# ---------------------------------------------------------------------------
# build_piper_specs — declarative linked-axes structure
# ---------------------------------------------------------------------------


class TestBuildPiperSpecs:
    def test_returns_list_of_specs(self):
        specs = build_piper_specs(_DATA)
        assert len(specs) == 1

    def test_spec_has_children_not_piper_coord(self):
        specs = build_piper_specs(_DATA)
        spec = specs[0]
        assert not isinstance(spec.coord, PiperCoord)
        assert isinstance(spec.coord, CoordCartesian)
        assert len(spec.children) == 3

    def test_child_names_and_types(self):
        specs = build_piper_specs(_DATA)
        spec = specs[0]
        # Children are unnamed FigureSpecs; check coords
        coords = [type(c.coord).__name__ for c in spec.children]
        assert coords == ["TernaryCoord", "TernaryCoord", "CoordCartesian"]

    def test_left_child_has_ternary_coord_and_transform(self):
        specs = build_piper_specs(_DATA)
        left = specs[0].children[0]
        assert isinstance(left.coord, TernaryCoord)
        assert left.coord.handedness == "left"
        assert left.coord.channels == ("Mg", "Ca", "Na+K")
        assert left.transform.ops == (("scale", (0.5, 0.5)),)

    def test_right_child_has_ternary_coord_and_transform(self):
        specs = build_piper_specs(_DATA)
        right = specs[0].children[1]
        assert isinstance(right.coord, TernaryCoord)
        assert right.coord.handedness == "right"
        assert right.coord.channels == ("SO4", "Cl", "HCO3")
        assert right.transform.ops == (
            ("scale", (-0.5, 0.5)),
            ("translate", (1.2, 0.0)),
        )

    def test_diamond_child_is_cartesian(self):
        specs = build_piper_specs(_DATA)
        dia = specs[0].children[2]
        assert isinstance(dia.coord, CoordCartesian)
        m = dia.transform.matrix()
        # translate=(0.6, 0.1), rotate=45, scale=(sqrt2/400, sqrt6/400)
        assert m[0, 2] == pytest.approx(0.6)
        assert m[1, 2] == pytest.approx(0.1)
        assert dia.transform.ops[0] == ("rotate", 45.0)

    def test_children_have_layers(self):
        specs = build_piper_specs(_DATA)
        for child in specs[0].children:
            assert len(child.layers) == 1
            assert isinstance(child.layers[0].geom, GeomPoint)

    def test_left_child_has_ion_channels(self):
        specs = build_piper_specs(_DATA)
        left = specs[0].children[0]
        vm = left.layers[0].visual_mapping
        for ch in ("Ca", "Mg", "Na+K"):
            assert ch in vm

    def test_diamond_child_has_xy(self):
        specs = build_piper_specs(_DATA)
        dia = specs[0].children[2]
        vm = dia.layers[0].visual_mapping
        assert "x" in vm
        assert "y" in vm

    def test_children_have_settings(self):
        specs = build_piper_specs(_DATA)
        # Per-panel titles were dropped; left/right opt into ternary axis arrows.
        left = specs[0].children[0]
        right = specs[0].children[1]
        assert left.settings == {"axis_arrows": True}
        assert right.settings == {"axis_arrows": True}
        dia = specs[0].children[2]
        # Diamond primary axes are declared normalized (0 .. 100) and reversed via
        # explicit flags, so their arrows point inward toward the triangle's
        # shared base region (arrows always point toward increasing data).
        assert dia.settings["xlim"] == (0, 100)
        assert dia.settings["ylim"] == (0, 100)
        assert dia.settings["x_reversed"] is True
        assert dia.settings["y_reversed"] is True
        assert dia.settings["grid_step"] == 20
        # The diamond opts into cartesian axis arrows (all four edges).
        assert dia.settings.get("axis_arrows", False) is True
        # Secondary axes for the diamond's upper edges (identity mapping here).
        assert dia.settings["secondary_x"]["range"] == [0, 100]
        assert dia.settings["secondary_y"]["range"] == [0, 100]

    def test_custom_title(self):
        specs = build_piper_specs(_DATA, title="My Piper")
        assert specs[0].settings["title"] == "My Piper"

    def test_mapping_adds_color_channel(self):
        data = _DATA.copy()
        data["group"] = ["A", "B"]
        specs = build_piper_specs(data, mapping={"color": "group"})
        for child in specs[0].children:
            assert "color" in child.mappings

    def test_mapping_adds_marker_channel(self):
        data = _DATA.copy()
        data["group"] = ["A", "B"]
        specs = build_piper_specs(data, mapping={"color": "group",
                                                  "marker": "group"})
        for child in specs[0].children:
            assert "color" in child.mappings
            assert "marker" in child.mappings

    def test_missing_ion_column_raises(self):
        bad_data = pd.DataFrame({"Ca": [1], "Mg": [1]})
        with pytest.raises(ValueError, match="ion column"):
            build_piper_specs(bad_data)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class TestPiperRenderer:
    def test_render_piper_single_axes(self):
        from geofig_engine.renderers import MatplotlibRenderer
        renderer = MatplotlibRenderer()
        specs = build_piper_specs(_DATA)
        assert renderer.supports(specs[0]) is True
        fig = renderer.render(specs[0])
        assert fig is not None
        assert len(fig.axes) == 1

    def test_render_with_mapping(self):
        from geofig_engine.renderers import MatplotlibRenderer
        data = _DATA.copy()
        data["group"] = ["A", "B"]
        renderer = MatplotlibRenderer()
        specs = build_piper_specs(data, mapping={"color": "group"})
        fig = renderer.render(specs[0])
        assert fig is not None

    def test_diamond_renders_secondary_ticks(self):
        from geofig_engine.renderers import MatplotlibRenderer
        renderer = MatplotlibRenderer()
        specs = build_piper_specs(_DATA)
        fig = renderer.render(specs[0])
        ax = fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        # Upper-edge scales: interior ticks toward the apex.
        assert "80" in texts
        assert "60" in texts
        assert "40" in texts
        assert "20" in texts
        # Secondary axis titles.
        assert "Anions (%)" in texts
        assert "Cations (%)" in texts


# ---------------------------------------------------------------------------
# Parity: new linked spec matches legacy ternary/diamond math
# ---------------------------------------------------------------------------


class TestPiperParity:
    """Verify the declarative spec produces the same point positions
    as the legacy template-side math."""

    def test_ternary_positions_match_legacy(self):
        """Left triangle ternary projection matches _ternary_x/y from legacy."""
        h = np.sqrt(3) / 2.0
        specs = build_piper_specs(_DATA)
        spec = specs[0]

        left = spec.children[0]
        left_layer = left.layers[0]
        vm = left.coord.transform_visual_mapping(
            dict(left_layer.visual_mapping), left_layer.geom)
        x_new = vm["x"].to_numpy()
        y_new = vm["y"].to_numpy()

        # Legacy math
        def _fracs(cols):
            total = _DATA[list(cols)].sum(axis=1)
            return [_DATA[c] / total for c in cols]

        cat_f = _fracs(("Ca", "Mg", "Na+K"))
        legacy_x = cat_f[2].to_numpy() + 0.5 * cat_f[1].to_numpy()
        legacy_y = h * cat_f[1].to_numpy()

        np.testing.assert_allclose(x_new, legacy_x, atol=1e-12)
        np.testing.assert_allclose(y_new, legacy_y, atol=1e-12)

    def test_diamond_positions_match_legacy(self):
        """Diamond percentage data + LinkTransform maps [0,100]² to correct diamond vertices."""
        h = np.sqrt(3) / 2.0
        specs = build_piper_specs(_DATA)
        spec = specs[0]

        dia = spec.children[2]
        vm = dia.layers[0].visual_mapping
        x_new = vm["x"].to_numpy()
        y_new = vm["y"].to_numpy()

        def _fracs(cols):
            total = _DATA[list(cols)].sum(axis=1)
            return [_DATA[c] / total for c in cols]

        cat_f = _fracs(("Ca", "Mg", "Na+K"))
        an_f = _fracs(("HCO3", "SO4", "Cl"))
        expected_cation_pct = (cat_f[0] + cat_f[1]).to_numpy() * 100
        expected_anion_pct = (an_f[1] + an_f[2]).to_numpy() * 100

        np.testing.assert_allclose(x_new, expected_anion_pct, atol=1e-12)
        np.testing.assert_allclose(y_new, expected_cation_pct, atol=1e-12)

        # Verify LinkTransform maps corners to correct diamond vertices
        corners_pct = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=float)
        corners_world = dia.transform.transform_points(corners_pct)

        expected_world = np.array([
            [0.6, 0.1],          # bottom vertex
            [0.85, h / 2.0 + 0.1],  # right vertex (≈0.433)
            [0.6, h + 0.1],      # top vertex (≈0.866)
            [0.35, h / 2.0 + 0.1],  # left vertex (≈0.433)
        ])
        np.testing.assert_allclose(corners_world, expected_world, atol=1e-10)

    def test_right_triangle_positions_match_legacy(self):
        """Right triangle ternary projection matches legacy _ternary_x/y."""
        h = np.sqrt(3) / 2.0
        specs = build_piper_specs(_DATA)
        spec = specs[0]

        right = spec.children[1]
        right_layer = right.layers[0]
        vm = right.coord.transform_visual_mapping(
            dict(right_layer.visual_mapping), right_layer.geom)
        x_new = vm["x"].to_numpy()
        y_new = vm["y"].to_numpy()

        def _fracs(cols):
            total = _DATA[list(cols)].sum(axis=1)
            return [_DATA[c] / total for c in cols]

        an_f = _fracs(("HCO3", "SO4", "Cl"))
        legacy_x = an_f[2].to_numpy() + 0.5 * an_f[1].to_numpy()
        legacy_y = h * an_f[1].to_numpy()

        np.testing.assert_allclose(x_new, legacy_x, atol=1e-12)
        np.testing.assert_allclose(y_new, legacy_y, atol=1e-12)

    def test_zero_ions_produce_zero_diamond(self):
        """Rows with all-zero ions land at diamond origin."""
        zero_data = pd.DataFrame({
            "Ca": [0.0], "Mg": [0.0], "Na+K": [0.0],
            "HCO3": [0.0], "SO4": [0.0], "Cl": [0.0],
        })
        specs = build_piper_specs(zero_data)
        dia = specs[0].children[2]
        x = dia.layers[0].visual_mapping["x"].to_numpy()
        y = dia.layers[0].visual_mapping["y"].to_numpy()
        np.testing.assert_allclose(x, 0.0, atol=1e-12)
        np.testing.assert_allclose(y, 0.0, atol=1e-12)
