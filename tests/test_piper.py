"""Tests for Piper diagram — declarative linked-axes spec (Phase 14.5 WP5)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import matplotlib
matplotlib.use("Agg")

from geofig_engine.core.coord import CoordCartesian, PiperCoord, TernaryCoord
from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.link import AxisLink, LinkTransform
from geofig_engine.core.spec import FigureSpec
from geofig_engine.templates import build_piper_specs, piper_overlay_diamond
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

    def test_spec_has_links_not_piper_coord(self):
        specs = build_piper_specs(_DATA)
        spec = specs[0]
        assert not isinstance(spec.coord, PiperCoord)
        assert isinstance(spec.coord, CoordCartesian)
        assert len(spec.links) == 3

    def test_link_names_and_types(self):
        specs = build_piper_specs(_DATA)
        spec = specs[0]
        names = [link.name for link in spec.links]
        assert names == ["left_tri", "right_tri", "diamond"]
        for link in spec.links:
            assert isinstance(link, AxisLink)

    def test_left_link_has_ternary_coord_and_transform(self):
        specs = build_piper_specs(_DATA)
        left = specs[0].links[0]
        assert isinstance(left.coord, TernaryCoord)
        assert left.coord.handedness == "left"
        assert left.coord.channels == ("Mg", "Ca", "Na+K")
        assert left.transform == LinkTransform(scale=(0.5, 0.5))

    def test_right_link_has_ternary_coord_and_transform(self):
        specs = build_piper_specs(_DATA)
        right = specs[0].links[1]
        assert isinstance(right.coord, TernaryCoord)
        assert right.coord.handedness == "right"
        assert right.coord.channels == ("SO4", "Cl", "HCO3")
        assert right.transform == LinkTransform(
            scale=(-0.5, 0.5), translate=(1.0, 0.0))

    def test_diamond_link_is_cartesian(self):
        specs = build_piper_specs(_DATA)
        dia = specs[0].links[2]
        assert isinstance(dia.coord, CoordCartesian)
        assert dia.transform.rotate == 45.0
        assert dia.transform.translate == (0.5, 0.0)

    def test_layers_have_subplot_tags(self):
        specs = build_piper_specs(_DATA)
        subplots = {l.subplot for l in specs[0].layers}
        assert subplots == {"left_tri", "right_tri", "diamond"}

    def test_layers_are_geom_point(self):
        specs = build_piper_specs(_DATA)
        for layer in specs[0].layers:
            assert isinstance(layer.geom, GeomPoint)
            if layer.subplot == "diamond":
                assert "x" in layer.visual_mapping
                assert "y" in layer.visual_mapping
            else:
                # Ternary layers store ion channels; x/y produced by coord
                assert len(layer.visual_mapping) >= 3

    def test_ternary_layers_have_ion_channels(self):
        specs = build_piper_specs(_DATA)
        spec = specs[0]
        left_layer = [l for l in spec.layers if l.subplot == "left_tri"][0]
        for ch in ("Ca", "Mg", "Na+K"):
            assert ch in left_layer.visual_mapping

    def test_custom_title(self):
        specs = build_piper_specs(_DATA, title="My Piper")
        assert specs[0].settings["title"] == "My Piper"

    def test_mapping_adds_color_channel(self):
        data = _DATA.copy()
        data["group"] = ["A", "B"]
        specs = build_piper_specs(data, mapping={"color": "group"})
        for layer in specs[0].layers:
            assert "color" in layer.visual_mapping

    def test_mapping_adds_marker_channel(self):
        data = _DATA.copy()
        data["group"] = ["A", "B"]
        specs = build_piper_specs(data, mapping={"color": "group",
                                                  "marker": "group"})
        for layer in specs[0].layers:
            assert "color" in layer.visual_mapping
            assert "marker" in layer.visual_mapping

    def test_missing_ion_column_raises(self):
        bad_data = pd.DataFrame({"Ca": [1], "Mg": [1]})
        with pytest.raises(ValueError, match="ion column"):
            build_piper_specs(bad_data)

    def test_frame_providers_registered(self):
        specs = build_piper_specs(_DATA)
        for link in specs[0].links:
            if link.frame:
                assert "provider" in link.frame


# ---------------------------------------------------------------------------
# piper_overlay_diamond — plain layer routing
# ---------------------------------------------------------------------------


class TestPiperOverlay:
    def test_appends_layer(self):
        specs = build_piper_specs(_DATA)
        n_before = len(specs[0].layers)
        overlaid = piper_overlay_diamond(specs[0], _DATA)
        assert len(overlaid.layers) == n_before + 1
        assert overlaid.layers[-1].subplot == "diamond"

    def test_overlay_preserves_links(self):
        specs = build_piper_specs(_DATA)
        overlaid = piper_overlay_diamond(specs[0], _DATA)
        assert overlaid.links == specs[0].links

    def test_overlay_no_piper_setting(self):
        specs = build_piper_specs(_DATA)
        overlaid = piper_overlay_diamond(specs[0], _DATA)
        assert "piper_overlay" not in overlaid.settings


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
        # Linked path renders on a single Axes
        assert len(fig.axes) == 1

    def test_render_with_mapping(self):
        from geofig_engine.renderers import MatplotlibRenderer
        data = _DATA.copy()
        data["group"] = ["A", "B"]
        renderer = MatplotlibRenderer()
        specs = build_piper_specs(data, mapping={"color": "group"})
        fig = renderer.render(specs[0])
        assert fig is not None

    def test_render_overlay(self):
        from geofig_engine.renderers import MatplotlibRenderer
        renderer = MatplotlibRenderer()
        specs = build_piper_specs(_DATA)
        overlaid = piper_overlay_diamond(specs[0], _DATA)
        fig = renderer.render(overlaid)
        assert fig is not None


# ---------------------------------------------------------------------------
# Geom compatibility on linked axes
# ---------------------------------------------------------------------------


class TestPiperGeomCompatibility:
    """Standard GoG geometries work in Piper linked-axes subplots."""

    def test_abline_in_diamond(self):
        from geofig_engine.renderers import MatplotlibRenderer
        from geofig_engine.core.layer import LayerSpec
        from geofig_engine.core.geom import GeomAbline
        from geofig_engine.core.stat import StatIdentity
        renderer = MatplotlibRenderer()
        specs = build_piper_specs(_DATA)
        spec = specs[0]
        abline_layer = LayerSpec(
            geom=GeomAbline(slope=0, intercept=0),
            stat=StatIdentity(),
            visual_mapping={"color": "red", "style": "dashed", "width": 0.5},
            subplot="diamond",
            zorder=1,
        )
        spec = spec.__class__(
            data=spec.data, mappings=spec.mappings, settings=spec.settings,
            context=spec.context, template_name=spec.template_name,
            layers=list(spec.layers) + [abline_layer],
            coord=spec.coord, facet=spec.facet, links=spec.links,
        )
        fig = renderer.render(spec)
        assert fig is not None

    def test_text_in_diamond(self):
        from geofig_engine.renderers import MatplotlibRenderer
        from geofig_engine.core.layer import LayerSpec
        from geofig_engine.core.geom import GeomText
        from geofig_engine.core.stat import StatIdentity
        renderer = MatplotlibRenderer()
        specs = build_piper_specs(_DATA)
        spec = specs[0]
        text_layer = LayerSpec(
            geom=GeomText(),
            stat=StatIdentity(),
            visual_mapping={
                "x": 0.0, "y": 0.0,
                "label": "center", "color": "red", "size": 10,
            },
            subplot="diamond",
            zorder=5,
        )
        spec = spec.__class__(
            data=spec.data, mappings=spec.mappings, settings=spec.settings,
            context=spec.context, template_name=spec.template_name,
            layers=list(spec.layers) + [text_layer],
            coord=spec.coord, facet=spec.facet, links=spec.links,
        )
        fig = renderer.render(spec)
        assert fig is not None


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

        # Apply TernaryCoord projection to get x/y from ion channels
        left_link = [l for l in spec.links if l.name == "left_tri"][0]
        left_layer = [l for l in spec.layers if l.subplot == "left_tri"][0]
        vm = left_link.coord.transform_visual_mapping(
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

        dia_layer = [l for l in spec.layers if l.subplot == "diamond"][0]
        vm = dia_layer.visual_mapping
        x_new = vm["x"].to_numpy()
        y_new = vm["y"].to_numpy()

        # Verify data is percentage values [0,100]
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
        dia_link = [l for l in spec.links if l.name == "diamond"][0]
        corners_pct = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=float)
        corners_world = dia_link.transform.transform_points(corners_pct)

        expected_world = np.array([
            [0.5, 0.0],          # bottom vertex
            [0.75, h / 2.0],     # right vertex (≈0.433)
            [0.5, h],            # top vertex (≈0.866)
            [0.25, h / 2.0],     # left vertex (≈0.433)
        ])
        np.testing.assert_allclose(corners_world, expected_world, atol=1e-10)

    def test_right_triangle_positions_match_legacy(self):
        """Right triangle ternary projection matches legacy _ternary_x/y."""
        h = np.sqrt(3) / 2.0
        specs = build_piper_specs(_DATA)
        spec = specs[0]

        right_link = [l for l in spec.links if l.name == "right_tri"][0]
        right_layer = [l for l in spec.layers if l.subplot == "right_tri"][0]
        vm = right_link.coord.transform_visual_mapping(
            dict(right_layer.visual_mapping), right_layer.geom)
        x_new = vm["x"].to_numpy()
        y_new = vm["y"].to_numpy()

        def _fracs(cols):
            total = _DATA[list(cols)].sum(axis=1)
            return [_DATA[c] / total for c in cols]

        an_f = _fracs(("HCO3", "SO4", "Cl"))
        # Legacy: _ternary_x(cl_f, so4_f) = cl + 0.5*so4
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
        dia_layer = [l for l in specs[0].layers if l.subplot == "diamond"][0]
        x = dia_layer.visual_mapping["x"].to_numpy()
        y = dia_layer.visual_mapping["y"].to_numpy()
        np.testing.assert_allclose(x, 0.0, atol=1e-12)
        np.testing.assert_allclose(y, 0.0, atol=1e-12)
