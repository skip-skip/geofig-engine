"""
Tests for linked-axes rendering (Phase 14.51).

Covers: child FigureSpecs on one shared Axes, flat Affine2D stacks per
child, frame implication from coord type, label policies, world limits,
facet conflict, engine passthrough, and JSON round-trip of children.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import matplotlib

matplotlib.use("Agg")

from geofig_engine.core.coord import CoordCartesian, TernaryCoord
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.facet import FacetWrap
from geofig_engine.core.geom import GeomLine
from geofig_engine.core.layer import Layer, LayerSpec
from geofig_engine.core.link import LinkTransform, label_rotation
from geofig_engine.core.secondary_axis import parse_secondary_settings
from geofig_engine.core.spec import FigureSpec, build_spec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.engine.generator import FigureEngine
from geofig_engine.renderers.matplotlib.renderer import MatplotlibRenderer
from geofig_engine.serialize import spec_from_json, spec_to_json


CHILD_A = FigureSpec(
    data=pd.DataFrame({"v": [1.0]}),
    mappings={},
    settings={},
    context={},
    template_name="test",
    transform=LinkTransform().translate(10, 20),
)
CHILD_B = FigureSpec(
    data=pd.DataFrame({"v": [1.0]}),
    mappings={},
    settings={},
    context={},
    template_name="test",
    transform=LinkTransform().rotate(45).scale(1.0, 0.5).translate(-3, 4),
)


def _child_layer(x, y, zorder=None):
    return LayerSpec(
        geom=GeomLine(),
        stat=StatIdentity(),
        visual_mapping={"x": pd.Series(x), "y": pd.Series(y)},
        zorder=zorder,
    )


def _child_spec(x, y, transform=None, coord=None, settings=None, zorder=None):
    n = len(x)
    return FigureSpec(
        data=pd.DataFrame({"v": np.arange(n, dtype=float)}),
        mappings={},
        settings=settings or {},
        context={},
        template_name="test",
        coord=coord or CoordCartesian(),
        transform=transform or LinkTransform(),
        layers=[_child_layer(x, y, zorder=zorder)],
    )


def _parent(children, settings=None):
    return FigureSpec(
        data=pd.DataFrame({"v": [1.0]}),
        mappings={},
        settings=settings or {},
        context={},
        template_name="test",
        children=tuple(children),
    )


def _render(spec):
    return MatplotlibRenderer().render(spec)


def _world(ax, artist):
    """World-space coords: artist chain ends at display; undo transData."""
    disp = artist.get_transform().transform(artist.get_xydata())
    return ax.transData.inverted().transform(disp)


class TestChildRendering:
    def test_single_shared_axes(self):
        fig = _render(_parent([
            _child_spec([0, 1], [0, 0], transform=CHILD_A.transform),
            _child_spec([0, 1], [0, 0], transform=LinkTransform().translate(-3, 4)),
        ]))
        assert len(fig.axes) == 1

    def test_children_land_at_affine_predicted_positions(self):
        base = np.array([[0.0, 0.0], [1.0, 0.0]])

        # Child A: translate=(10,20)
        fig_a = _render(_parent([
            _child_spec([0, 1], [0, 0], transform=CHILD_A.transform),
        ]))
        ax_a = fig_a.axes[0]
        worlds_a = [_world(ax_a, line) for line in ax_a.lines]
        expected_a = base + np.array([10.0, 20.0])
        assert any(np.allclose(w, expected_a, atol=1e-9) for w in worlds_a)

        # Child B: translate=(-3,4), scale=(1,0.5)
        child_b_no_rotate = LinkTransform().scale(1.0, 0.5).translate(-3, 4)
        fig_b = _render(_parent([
            _child_spec([0, 1], [0, 0], transform=child_b_no_rotate),
        ]))
        ax_b = fig_b.axes[0]
        worlds_b = [_world(ax_b, line) for line in ax_b.lines]
        expected_b = child_b_no_rotate.transform_points(base)
        assert any(np.allclose(w, expected_b, atol=1e-9) for w in worlds_b)


class TestFrameImplication:
    def test_ternary_frame_renders(self):
        from geofig_engine.core.coord import TernaryCoord
        coord = TernaryCoord(channels=("Mg", "Ca", "Na+K"), handedness="left")
        layer = LayerSpec(
            geom=GeomLine(),
            stat=StatIdentity(),
            visual_mapping={
                "Mg": pd.Series([0.0, 0.5, 1.0]),
                "Ca": pd.Series([0.0, 0.433, 0.0]),
                "Na+K": pd.Series([1.0, 0.067, 0.0]),
            },
        )
        fig = _render(_parent([
            FigureSpec(
                data=pd.DataFrame({"v": np.arange(3, dtype=float)}),
                mappings={}, settings={"title": "TEST TRIANGLE"}, context={},
                template_name="test",
                coord=coord,
                transform=LinkTransform().scale(0.5, 0.5),
                layers=[layer],
            ),
        ]))
        ax = fig.axes[0]
        # Ternary frame produces grid lines + tick labels + title + ion labels
        # (arrows are opt-in via axis_arrows, off here).
        assert len(ax.lines) > 1
        texts = [t.get_text() for t in ax.texts]
        assert "TEST TRIANGLE" in texts

    def test_diamond_frame_renders(self):
        fig = _render(_parent([
            _child_spec(
                [0.0, 50.0, 100.0], [0.0, 50.0, 100.0],
                transform=LinkTransform()
                .rotate(45.0)
                .scale(np.sqrt(2) / 400, np.sqrt(3) / 200)
                .translate(0.5, 0.0),
                settings={
                    "title": "TEST DIAMOND",
                    "xlim": (0, 100),
                    "ylim": (0, 100),
                    "grid_step": 20,
                    "tick_step": 20,
                },
            ),
        ]))
        ax = fig.axes[0]
        assert len(ax.lines) > 1
        texts = [t.get_text() for t in ax.texts]
        assert "TEST DIAMOND" in texts

    def test_no_frame_when_no_frame_bounds_and_identity_transform(self):
        fig = _render(_parent([
            _child_spec([0, 1], [0, 0]),
        ]))
        ax = fig.axes[0]
        # No frame for plain Cartesian with no xlim/ylim bounds in settings
        assert len(ax.texts) == 0


class TestSecondaryFrameTicks:
    """Reversed secondary axes draw top/right tick labels deformed by the matrix."""

    def _diamond_spec(self):
        """A rotated cartesian child with reversed secondary x/y axes."""
        shared = {
            "title": "TEST DIAMOND",
            "xlim": (0, 100),
            "ylim": (0, 100),
            "grid_step": 20,
            "tick_step": 20,
            "secondary_x": {"range": [100, 0], "label": "Anions (%)"},
            "secondary_y": {"range": [100, 0], "label": "Cations (%)"},
        }
        transform = (
            LinkTransform()
            .rotate(45.0)
            .scale(np.sqrt(2) / 400, np.sqrt(3) / 200)
            .translate(0.5, 0.0)
        )
        return _parent([
            _child_spec([0.0, 50.0, 100.0], [0.0, 50.0, 100.0],
                        transform=transform, settings=shared),
        ])

    def test_secondary_axis_titles_rendered(self):
        fig = _render(self._diamond_spec())
        ax = fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        assert "Anions (%)" in texts
        assert "Cations (%)" in texts

    def test_secondary_ticks_match_expected_world_positions(self):
        """Secondary ticks sit at the matrix-transformed local anchors."""
        fig = _render(self._diamond_spec())
        ax = fig.axes[0]

        transform = (
            LinkTransform()
            .rotate(45.0)
            .scale(np.sqrt(2) / 400, np.sqrt(3) / 200)
            .translate(0.5, 0.0)
        )

        # Reversed secondary range [100,0] on a [0,100] primary: secondary value
        # sv -> local coord inv(sv) = 100 - sv. Secondary-x anchors sit on the
        # top edge at local y=105 (just outside y1=100); secondary-y anchors on
        # the right edge at local x=105.
        def inv(sv):
            return 100.0 - sv

        x_anchor = {f"{sv:g}": transform.transform_points([[inv(sv), 105.0]])[0]
                    for sv in (20, 40, 60, 80)}
        y_anchor = {f"{sv:g}": transform.transform_points([[105.0, inv(sv)]])[0]
                    for sv in (20, 40, 60, 80)}

        matched_x = 0
        matched_y = 0
        for t in ax.texts:
            text = t.get_text()
            if text not in x_anchor:
                continue
            x, y = t.get_position()
            if np.allclose(x_anchor[text], (x, y), atol=1e-9):
                matched_x += 1
            if np.allclose(y_anchor[text], (x, y), atol=1e-9):
                matched_y += 1

        # 4 interior ticks drawn on the top (secondary x) and right (secondary y).
        assert matched_x == 4
        assert matched_y == 4

    def test_no_secondary_ticks_when_not_declared(self):
        fig = _render(_parent([
            _child_spec([0.0, 50.0, 100.0], [0.0, 50.0, 100.0],
                        transform=LinkTransform()
                        .rotate(45.0)
                        .scale(np.sqrt(2) / 400, np.sqrt(3) / 200)
                        .translate(0.5, 0.0),
                        settings={
                            "title": "TEST DIAMOND",
                            "xlim": (0, 100),
                            "ylim": (0, 100),
                            "grid_step": 20,
                            "tick_step": 20,
                        }),
        ]))
        ax = fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        assert "Anions (%)" not in texts
        assert "Cations (%)" not in texts


class TestDataTwinAxis:
    """WP-D: secondary-axis (x2/y2) data channels map into local x/y."""

    def _child(self, vm, secondary=True):
        settings = {
            "xlim": (0, 100), "ylim": (0, 100),
            "grid_step": 20, "tick_step": 20,
        }
        if secondary:
            settings["secondary_x"] = {"range": [0, 100]}
            settings["secondary_y"] = {"range": [0, 100]}
        return FigureSpec(
            data=pd.DataFrame({"v": [1.0]}),
            mappings={}, settings=settings, context={},
            template_name="other",
            coord=CoordCartesian(),
            transform=LinkTransform().translate(0, 0),
            layers=[LayerSpec(
                geom=GeomLine(), stat=StatIdentity(),
                visual_mapping=vm, zorder=10,
            )],
        )

    def test_y2_maps_through_secondary_y(self):
        secondary = parse_secondary_settings(
            self._child({"x": pd.Series([10.0]), "y2": pd.Series([80.0])}).settings)
        out = MatplotlibRenderer._remap_secondary_channels(
            {"x": pd.Series([10.0]), "y2": pd.Series([80.0])}, secondary)
        assert "y2" not in out
        assert out["y"].iloc[0] == pytest.approx(80.0)
        assert out["x"].iloc[0] == pytest.approx(10.0)

    def test_x2_maps_through_secondary_x_reversed(self):
        settings = {
            "xlim": (0, 100), "ylim": (0, 100),
            "secondary_x": {"range": [100, 0]},
        }
        secondary = parse_secondary_settings(settings)
        out = MatplotlibRenderer._remap_secondary_channels(
            {"x2": pd.Series([20.0]), "y": pd.Series([5.0])}, secondary)
        assert "x2" not in out
        assert out["x"].iloc[0] == pytest.approx(80.0)
        assert out["y"].iloc[0] == pytest.approx(5.0)

    def test_no_secondary_channel_is_noop(self):
        secondary = parse_secondary_settings({})
        vm = {"x": pd.Series([1.0]), "y": pd.Series([2.0])}
        out = MatplotlibRenderer._remap_secondary_channels(vm, secondary)
        assert "x2" not in out and "y2" not in out
        assert out["x"].iloc[0] == pytest.approx(1.0)
        assert out["y"].iloc[0] == pytest.approx(2.0)

    def test_y2_without_declaration_raises(self):
        secondary = parse_secondary_settings({"xlim": (0, 100), "ylim": (0, 100)})
        with pytest.raises(ValueError, match="secondary_y"):
            MatplotlibRenderer._remap_secondary_channels(
                {"x": pd.Series([1.0]), "y2": pd.Series([2.0])}, secondary)

    def test_non_series_secondary_channel_raises(self):
        secondary = parse_secondary_settings({"secondary_y": {"range": [0, 100]}})
        with pytest.raises(TypeError):
            MatplotlibRenderer._remap_secondary_channels({"y2": [1, 2]}, secondary)

    def test_apply_child_coord_transforms_remaps_y2(self):
        child = self._child({"x": pd.Series([50.0]), "y2": pd.Series([30.0])})
        out = MatplotlibRenderer()._apply_child_coord_transforms(child)
        vm = out.layers[0].visual_mapping
        assert "y2" not in vm
        assert vm["y"].iloc[0] == pytest.approx(30.0)
        assert vm["x"].iloc[0] == pytest.approx(50.0)

    def test_render_pipeline_accepts_twin_axis_layer(self):
        child = self._child({"x": pd.Series([50.0]), "y2": pd.Series([30.0])},
                            secondary=True)
        fig = _render(_parent([child]))
        ax = fig.axes[0]
        assert len(ax.lines) >= 1


class TestWorldLimits:
    def test_limits_cover_child_extents(self):
        fig = _render(_parent(
            [_child_spec([0, 1], [0, 0], transform=CHILD_A.transform)],
            settings={"title": "Test"},
        ))
        ax = fig.axes[0]
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        # Child A corners span (10..11, 20..21); padded by 5%.
        assert xmin <= 10.0 and xmax >= 11.0
        assert ymin <= 20.0 and ymax >= 21.0
        assert fig._suptitle.get_text() == "Test"
        assert ax.axison is False

    def test_limits_fall_back_when_no_children(self):
        xlim, ylim = MatplotlibRenderer._children_world_limits([])
        assert (xlim, ylim) == ((-1.0, 1.0), (-1.0, 1.0))


class TestFacetConflict:
    def test_facet_with_children_raises_not_implemented(self):
        spec = FigureSpec(
            data=pd.DataFrame({"v": [1.0]}),
            mappings={},
            settings={},
            context={},
            template_name="test",
            facet=FacetWrap(by="v"),
            children=(_child_spec([0, 1], [0, 0]),),
        )
        with pytest.raises(NotImplementedError, match="facets"):
            _render(spec)


class TestEnginePassthrough:
    def test_engine_builds_specs_without_links(self):
        dataset = Dataset(
            dataframe=pd.DataFrame({"id": [1, 2], "x": [0.0, 1.0], "y": [0.0, 1.0]}),
            key_column="id",
        )
        specs = FigureEngine().build_specs_from_layers(
            dataset,
            layers=[Layer(geom=GeomLine(), mapping={"x": "x", "y": "y"})],
        )
        assert len(specs) == 1
        spec = specs[0]
        assert spec.children == ()


class TestLabelRotation:
    def test_label_rotation_pure_math(self):
        matrix = CHILD_B.transform.matrix()
        assert label_rotation((1, 0), matrix, policy="upright") == 0.0
        parallel = label_rotation((1, 0), matrix, policy="parallel")
        assert parallel == pytest.approx(
            np.degrees(np.arctan2(0.5 * np.sin(np.pi / 4), np.cos(np.pi / 4))),
            abs=1e-9,
        )
        with pytest.raises(ValueError, match="label policy"):
            label_rotation((1, 0), matrix, policy="diagonal")


class TestLinkedSerializationRoundTrip:
    def test_children_survive_json_round_trip(self):
        spec = FigureSpec(
            data=pd.DataFrame({"v": [1.0]}),
            mappings={},
            settings={},
            context={},
            template_name="test",
            children=(
                FigureSpec(
                    data=pd.DataFrame({"v": [1.0]}),
                    mappings={},
                    settings={},
                    context={},
                    template_name="child",
                    transform=LinkTransform().translate(10, 20),
                ),
                FigureSpec(
                    data=pd.DataFrame({"v": [1.0]}),
                    mappings={},
                    settings={},
                    context={},
                    template_name="child2",
                    transform=CHILD_B.transform,
                ),
            ),
        )

        restored = spec_from_json(spec_to_json(spec))

        assert len(restored.children) == 2
        assert restored.children[0].transform == LinkTransform().translate(10, 20)
        assert restored.children[1].transform == CHILD_B.transform
