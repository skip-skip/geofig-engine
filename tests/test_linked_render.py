"""
Tests for linked-axes rendering (Phase 14.5 WP4).

Covers: one shared Axes for main + links, flat Affine2D stacks per artist
group, root-transform scoping (main axis only), box frame provider, label
policies, unrouted/main-axis routing, zorder preservation, per-link coord
application, world limits, facet conflict, engine passthrough, and JSON
round-trip of links + root_transform.
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
from geofig_engine.core.geom import GeomFunctionLine, GeomLine
from geofig_engine.core.layer import Layer, LayerSpec
from geofig_engine.core.link import AxisLink, LinkTransform, label_rotation
from geofig_engine.core.spec import build_spec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.engine.generator import FigureEngine
from geofig_engine.renderers.matplotlib.renderer import (
    MatplotlibRenderer,
    _FRAME_PROVIDERS,
)
from geofig_engine.serialize import spec_from_json, spec_to_json


LINK_A = AxisLink(
    name="a",
    coord=CoordCartesian(),
    transform=LinkTransform(translate=(10, 20)),
)
LINK_B = AxisLink(
    name="b",
    coord=CoordCartesian(),
    transform=LinkTransform(translate=(-3, 4), rotate=45, scale=(1.0, 0.5)),
)


def _line_layer(x, y, subplot=None, zorder=None):
    return LayerSpec(
        geom=GeomLine(),
        stat=StatIdentity(),
        visual_mapping={"x": pd.Series(x), "y": pd.Series(y)},
        subplot=subplot,
        zorder=zorder,
    )


def _spec(layers, links=(LINK_A, LINK_B), root=None):
    return build_spec(
        data=pd.DataFrame({"v": [1.0, 2.0]}),
        mappings={},
        settings={},
        context={},
        template_name="test",
        layers=list(layers),
        links=links,
        root_transform=root,
    )


def _render(spec):
    return MatplotlibRenderer().render(spec)


def _world(ax, artist):
    """World-space coords: artist chain ends at display; undo transData."""
    disp = artist.get_transform().transform(artist.get_xydata())
    return ax.transData.inverted().transform(disp)


def _base_line():
    return np.array([[0.0, 0.0], [1.0, 0.0]])


class TestRoutingAndTransforms:
    def test_single_shared_axes(self):
        fig = _render(_spec([
            _line_layer([0, 1], [0, 0]),
            _line_layer([0, 1], [0, 0], subplot="a"),
            _line_layer([0, 1], [0, 0], subplot="b"),
        ]))
        assert len(fig.axes) == 1

    def test_layers_land_at_affine_predicted_positions(self):
        fig = _render(_spec([
            _line_layer([0, 1], [0, 0]),
            _line_layer([0, 1], [0, 0], subplot="a"),
            _line_layer([0, 1], [0, 0], subplot="b"),
        ]))
        ax = fig.axes[0]
        worlds = [_world(ax, line) for line in ax.lines]
        assert len(worlds) == 3

        base = _base_line()
        expected = {
            "main": base,
            "a": base + np.array([10.0, 20.0]),
            "b": LINK_B.transform.transform_points(base),
        }
        for exp in expected.values():
            assert any(np.allclose(w, exp, atol=1e-9) for w in worlds), exp

    def test_unrouted_layers_use_main_matrix_without_root(self):
        fig = _render(_spec([
            _line_layer([0, 1], [0, 2]),
            _line_layer([0, 1], [0, 2], subplot="a"),
        ]))
        ax = fig.axes[0]
        worlds = [_world(ax, line) for line in ax.lines]
        base = np.array([[0.0, 0.0], [1.0, 2.0]])
        assert any(np.allclose(w, base, atol=1e-9) for w in worlds)
        assert any(
            np.allclose(w, base + np.array([10.0, 20.0]), atol=1e-9) for w in worlds
        )

    def test_root_transform_applies_only_to_main_axis_artists(self):
        root = LinkTransform(rotate=90, scale=(2.0, 1.0))
        fig = _render(_spec([
            _line_layer([0, 1], [0, 0]),
            _line_layer([0, 1], [0, 0], subplot="a"),
        ], root=root))

        ax = fig.axes[0]
        worlds = [_world(ax, line) for line in ax.lines]
        base = _base_line()
        # rotate 90 then scale x: (1,0) -> (0,1)
        rooted = root.transform_points(base)
        assert any(np.allclose(w, rooted, atol=1e-9) for w in worlds)
        assert any(
            np.allclose(w, base + np.array([10.0, 20.0]), atol=1e-9) for w in worlds
        )
        assert not any(np.allclose(w, base, atol=1e-9) for w in worlds)

    def test_function_lines_routed_below_data_zorder(self):
        func_layer = LayerSpec(
            geom=GeomFunctionLine(func="0 * x"),
            stat=StatIdentity(),
            visual_mapping={},
            subplot="a",
        )
        fig = _render(_spec([
            _line_layer([0, 1], [0, 0], zorder=12),
            func_layer,
        ]))
        ax = fig.axes[0]
        orders = sorted(line.get_zorder() for line in ax.lines)
        assert min(orders) < 10 <= max(orders)

        # The function line was routed through link a: local y=0 lands at
        # world y=20.
        routed = [
            _world(ax, line)[:, 1] for line in ax.lines
            if line.get_zorder() < 10
        ]
        assert routed and all(np.allclose(yv, 20.0, atol=1e-6) for yv in routed)


class TestFrameProviders:
    def test_registry_contains_box_reference_provider(self):
        assert "box" in _FRAME_PROVIDERS

    def test_box_frame_deforms_with_link_and_labels_upright(self):
        framed_a = AxisLink(
            name="a",
            coord=CoordCartesian(),
            transform=LINK_A.transform,
            frame={"provider": "box"},
        )
        fig = _render(_spec(
            [_line_layer([0, 1], [0, 0], subplot="a")],
            links=(framed_a,),
        ))
        ax = fig.axes[0]

        outline_expected = framed_a.transform.transform_points(
            [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
        )
        outlines = [
            _world(ax, line) for line in ax.lines if len(line.get_xydata()) == 5
        ]
        assert len(outlines) == 1
        assert np.allclose(outlines[0], outline_expected, atol=1e-9)

        # Four corner labels, upright, anchored at transformed offsets.
        assert len(ax.texts) == 4
        anchors_local = [(-0.06, -0.06), (1.06, -0.06),
                         (1.06, 1.06), (-0.06, 1.06)]
        expected_pos = framed_a.transform.transform_points(anchors_local)
        for text_artist, expected in zip(ax.texts, expected_pos):
            assert text_artist.get_rotation() == 0.0
            wx, wy = text_artist.get_position()
            assert wx == pytest.approx(expected[0], abs=1e-9)
            assert wy == pytest.approx(expected[1], abs=1e-9)
        assert {t.get_text() for t in ax.texts} == {"BL", "BR", "TR", "TL"}

    def test_parallel_policy_is_squash_aware(self):
        framed_b = AxisLink(
            name="b",
            coord=CoordCartesian(),
            transform=LINK_B.transform,
            frame={"provider": "box", "label_policy": "parallel"},
        )
        fig = _render(_spec(
            [_line_layer([0, 1], [0, 0], subplot="b")],
            links=(framed_b,),
        ))
        ax = fig.axes[0]
        assert len(ax.texts) == 4

        # Linear part of M = S(1,.5) @ R(45): bottom-edge tangent (1,0)
        # maps to (cos45, .5*sin45) -> atan2 tilt ~26.565 deg, NOT 45.
        rotations = sorted(t.get_rotation() for t in ax.texts)
        expected_bottom = np.degrees(np.arctan2(0.5 * np.sin(np.pi / 4),
                                                np.cos(np.pi / 4)))
        expected_side = np.degrees(np.arctan2(0.5 * np.cos(np.pi / 4),
                                              -np.sin(np.pi / 4)))
        assert rotations[0] == pytest.approx(expected_bottom, abs=1e-6)
        assert rotations[1] == pytest.approx(expected_bottom, abs=1e-6)
        assert rotations[2] == pytest.approx(expected_side, abs=1e-6)
        assert rotations[3] == pytest.approx(expected_side, abs=1e-6)
        assert all(abs(r - 45.0) > 0.5 for r in rotations)

    def test_unknown_provider_is_ignored(self):
        framed = AxisLink(name="a", coord=CoordCartesian(),
                          frame={"provider": "does_not_exist"})
        fig = _render(_spec([_line_layer([0, 1], [0, 0])], links=(framed,)))
        ax = fig.axes[0]
        assert len(ax.texts) == 0
        assert len(ax.lines) == 1

    def test_label_rotation_pure_math(self):
        matrix = LINK_B.transform.matrix()
        assert label_rotation((1, 0), matrix, policy="upright") == 0.0
        parallel = label_rotation((1, 0), matrix, policy="parallel")
        assert parallel == pytest.approx(
            np.degrees(np.arctan2(0.5 * np.sin(np.pi / 4), np.cos(np.pi / 4))),
            abs=1e-9,
        )
        with pytest.raises(ValueError, match="label policy"):
            label_rotation((1, 0), matrix, policy="diagonal")

    def test_no_frames_when_links_have_none(self):
        fig = _render(_spec([_line_layer([0, 1], [0, 0])]))
        assert len(fig.axes[0].texts) == 0


class TestWorldLimitsAndSettings:
    def test_limits_cover_link_extents_title_applies_axis_off(self):
        framed_a = AxisLink(
            name="a",
            coord=CoordCartesian(),
            transform=LINK_A.transform,
        )
        spec = build_spec(
            data=pd.DataFrame({"v": [1.0]}),
            mappings={},
            settings={"title": "Linked Canvas"},
            context={},
            template_name="test",
            layers=[_line_layer([0, 1], [0, 0], subplot="a")],
            links=(framed_a,),
        )
        fig = _render(spec)
        ax = fig.axes[0]
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        # Link corners span (10..11, 20..21); padded by 5%.
        assert xmin <= 10.0 and xmax >= 11.0
        assert ymin <= 20.0 and ymax >= 21.0
        assert fig._suptitle.get_text() == "Linked Canvas"
        assert ax.axison is False

    def test_limits_fall_back_when_no_extents(self):
        spec = _spec([], links=())
        xlim, ylim = MatplotlibRenderer._linked_world_limits(
            spec, np.eye(3), {}
        )
        assert (xlim, ylim) == ((-1.0, 1.0), (-1.0, 1.0))


class TestPerLinkCoordsAndEngine:
    def test_routed_layer_uses_link_coord(self):
        tern_link = AxisLink(
            name="t",
            coord=TernaryCoord(channels=("p", "q", "r")),
            transform=LINK_A.transform,
        )
        layer = LayerSpec(
            geom=GeomLine(),
            stat=StatIdentity(),
            visual_mapping={
                "p": pd.Series([1.0, 0.0, 0.0]),
                "q": pd.Series([0.0, 1.0, 0.0]),
                "r": pd.Series([0.0, 0.0, 1.0]),
            },
            subplot="t",
        )
        fig = _render(_spec([layer], links=(tern_link,)))
        ax = fig.axes[0]
        # Ternary projection produced drawable x/y through the link transform.
        assert len(ax.lines) == 1
        world = _world(ax, ax.lines[0])
        assert np.all(np.isfinite(world))

    def test_engine_passthrough_links_and_root(self):
        dataset = Dataset(
            dataframe=pd.DataFrame({"id": [1, 2], "x": [0.0, 1.0], "y": [0.0, 1.0]}),
            key_column="id",
        )
        root = LinkTransform(rotate=90)
        specs = FigureEngine().build_specs_from_layers(
            dataset,
            layers=[Layer(geom=GeomLine(), mapping={"x": "x", "y": "y"})],
            links=(LINK_A,),
            root_transform=root,
        )
        assert len(specs) == 1
        spec = specs[0]
        assert tuple(link.name for link in spec.links) == ("a",)
        assert spec.links[0].transform == LINK_A.transform
        assert spec.root_transform == root

    def test_facet_with_links_raises_not_implemented(self):
        spec = build_spec(
            data=pd.DataFrame({"v": [1.0]}),
            mappings={},
            settings={},
            context={},
            template_name="test",
            layers=[_line_layer([0, 1], [0, 0])],
            links=(LINK_A,),
            facet=FacetWrap(by="v"),
        )
        with pytest.raises(NotImplementedError, match="facets"):
            _render(spec)


class TestLinkedSerializationRoundTrip:
    def test_links_and_root_survive_json_round_trip(self):
        root = LinkTransform(translate=(5, -2), rotate=15, scale=(1.2, 0.8))
        spec = _spec([_line_layer([0, 1], [0, 0])], root=root)

        restored = spec_from_json(spec_to_json(spec))

        assert tuple(l.name for l in restored.links) == ("a", "b")
        assert restored.links[0].transform == LINK_A.transform
        assert restored.links[1].transform == LINK_B.transform
        assert restored.root_transform == root
        assert restored.links == spec.links

    def test_missing_root_transform_loads_as_none(self):
        spec = _spec([_line_layer([0, 1], [0, 0])], root=None)
        payload = spec_to_json(spec)
        assert "root_transform" not in payload or \
            spec_from_json(payload).root_transform is None
