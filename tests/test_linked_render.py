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
        # Ternary frame produces grid lines + tick labels + title + ion arrows
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
