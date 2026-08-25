"""
Tests for core.link: LinkTransform math, FigureSpec children validation,
and serialization round-trips (Phase 14.51).

The matrix convention pinned here: ``M = T · S · R``, i.e. points experience
rotate -> scale -> translate, with scale acting along world axes after
rotation (this is what makes the Piper diamond's "rotate 45°, then squash y"
expressible as ``LinkTransform(translate=t, rotate=45, scale=(1, k))``).
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
import pytest

from geofig_engine.core.coord import CoordCartesian, CoordPolar
from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.link import LinkTransform
from geofig_engine.core.spec import FigureSpec, build_spec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.serialize import (
    figure_spec_from_dict,
    figure_spec_to_dict,
    spec_from_json,
    spec_to_json,
)

SQRT2_2 = np.sqrt(2.0) / 2.0


# ---------------------------------------------------------------------------
# LinkTransform math
# ---------------------------------------------------------------------------


class TestLinkTransformMath:
    def test_defaults_are_identity(self):
        t = LinkTransform()
        np.testing.assert_allclose(t.matrix(), np.eye(3))
        assert t.transform_point((3.0, 4.0)) == (3.0, 4.0)

    def test_matrix_shape_and_homogeneous_row(self):
        m = LinkTransform(translate=(1, 2), rotate=30, scale=(2, 3)).matrix()
        assert m.shape == (3, 3)
        np.testing.assert_allclose(m[2], [0.0, 0.0, 1.0])

    def test_translate_only(self):
        t = LinkTransform(translate=(10, 20))
        assert t.transform_point((1, 1)) == (11.0, 21.0)

    def test_rotate_only(self):
        t = LinkTransform(rotate=90)
        x, y = t.transform_point((1, 0))
        assert x == pytest.approx(0.0)
        assert y == pytest.approx(1.0)

    def test_scale_only(self):
        t = LinkTransform(scale=(3, 2))
        assert t.transform_point((2, 3)) == (6.0, 6.0)

    def test_application_order_is_rotate_then_scale_then_translate(self):
        # (1,1) --rot90--> (-1,1) --scale(2,3)--> (-2,3) --translate--> (8,23)
        t = LinkTransform(translate=(10, 20), rotate=90, scale=(2, 3))
        assert t.transform_point((1, 1)) == (8.0, 23.0)

    def test_diamond_convention_rotate_then_squash(self):
        # (1,0) --rot45--> (sqrt2/2, sqrt2/2) --squash-y 0.5--> (sqrt2/2, sqrt2/4)
        t = LinkTransform(translate=(-0.25, 0.5), rotate=45, scale=(1.0, 0.5))
        x, y = t.transform_point((1, 0))
        assert x == pytest.approx(SQRT2_2 - 0.25)
        assert y == pytest.approx(SQRT2_2 / 2.0 + 0.5)

    def test_matrix_matches_transform_point_on_corners(self):
        t = LinkTransform(translate=(-1.5, 2.5), rotate=-33, scale=(0.75, 1.4))
        m = t.matrix()
        for px, py in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            expected = m @ np.array([px, py, 1.0])
            assert t.transform_point((px, py)) == (
                pytest.approx(float(expected[0])),
                pytest.approx(float(expected[1])),
            )

    def test_negative_rotation_direction(self):
        # Clockwise rotation takes +y toward +x.
        t = LinkTransform(rotate=-90)
        assert t.transform_point((0, 1)) == (pytest.approx(1.0), pytest.approx(0.0))


class TestLinkTransformValidation:
    def test_translate_wrong_length_raises(self):
        with pytest.raises(TypeError, match="pair"):
            LinkTransform(translate=(1, 2, 3))

    def test_translate_non_numeric_raises(self):
        with pytest.raises(TypeError, match="real numbers"):
            LinkTransform(translate=("a", 1))

    def test_bool_rejected_for_translate(self):
        with pytest.raises(TypeError):
            LinkTransform(translate=(True, 1))

    def test_scale_wrong_length_raises(self):
        with pytest.raises(TypeError, match="pair"):
            LinkTransform(scale=[1])

    def test_scale_non_numeric_raises(self):
        with pytest.raises(TypeError, match="real numbers"):
            LinkTransform(scale=(1, None))

    def test_bool_rejected_for_scale(self):
        with pytest.raises(TypeError):
            LinkTransform(scale=(False, 1))

    def test_rotate_string_raises(self):
        with pytest.raises(TypeError, match="real number"):
            LinkTransform(rotate="45")

    def test_rotate_bool_raises(self):
        with pytest.raises(TypeError, match="real number"):
            LinkTransform(rotate=True)

    def test_int_inputs_coerced_to_float(self):
        t = LinkTransform(translate=(1, 2), rotate=90, scale=(2, 1))
        assert t.translate == (1.0, 2.0)
        assert t.rotate == 90.0
        assert t.scale == (2.0, 1.0)
        assert all(isinstance(v, float) for v in (*t.translate, *t.scale))
        assert isinstance(t.rotate, float)

    def test_frozen(self):
        t = LinkTransform()
        with pytest.raises(dataclasses.FrozenInstanceError):
            t.rotate = 45


class TestLinkTransformSerialization:
    def test_roundtrip_full(self):
        t = LinkTransform(translate=(-0.25, 0.75), rotate=45, scale=(1.0, 0.5))
        restored = LinkTransform.from_dict(t.to_dict())
        assert restored == t

    def test_from_empty_dict_gives_defaults(self):
        assert LinkTransform.from_dict({}) == LinkTransform()

    def test_from_partial_dict(self):
        t = LinkTransform.from_dict({"rotate": 30})
        assert t.rotate == 30.0
        assert t.translate == (0.0, 0.0)
        assert t.scale == (1.0, 1.0)


# ---------------------------------------------------------------------------
# FigureSpec children validation
# ---------------------------------------------------------------------------


def _make_spec(children=(), layers=None):
    return FigureSpec(
        data=pd.DataFrame({"x": [1, 2], "y": [3, 4]}),
        mappings={},
        settings={},
        context={},
        template_name="test",
        layers=layers if layers is not None else [],
        children=children,
    )


def _child(name="a", coord=None, transform=None):
    return FigureSpec(
        data=pd.DataFrame({"x": [1]}),
        mappings={},
        settings={},
        context={},
        template_name="test",
        coord=coord or CoordCartesian(),
        transform=transform or LinkTransform(),
    )


class TestFigureSpecChildren:
    def test_default_children_empty(self):
        assert FigureSpec(
            data=pd.DataFrame({"x": [1]}),
            mappings={},
            settings={},
            context={},
            template_name="t",
        ).children == ()

    def test_valid_children_pass_validation(self):
        children = (
            _child("left", CoordCartesian()),
            _child("right", CoordPolar(theta="x")),
        )
        spec = _make_spec(children=children)
        assert spec.children == children

    def test_non_figure_spec_in_children_raises(self):
        with pytest.raises(TypeError, match="FigureSpec"):
            _make_spec(children=("not_a_spec",))

    def test_nested_children_raises(self):
        deep = FigureSpec(
            data=pd.DataFrame({"x": [1]}),
            mappings={},
            settings={},
            context={},
            template_name="t",
            children=(_child(),),
        )
        with pytest.raises(ValueError, match="depth"):
            _make_spec(children=(deep,))

    def test_build_spec_accepts_children(self):
        child = _child("c", CoordCartesian())
        spec = build_spec(
            data=pd.DataFrame({"x": [1]}),
            mappings={},
            settings={},
            context={},
            template_name="t",
            children=(child,),
        )
        assert spec.children == (child,)

    def test_build_spec_accepts_transform(self):
        tf = LinkTransform(rotate=45)
        spec = build_spec(
            data=pd.DataFrame({"x": [1]}),
            mappings={},
            settings={},
            context={},
            template_name="t",
            transform=tf,
        )
        assert spec.transform == tf

    def test_build_spec_accepts_frame_config(self):
        spec = build_spec(
            data=pd.DataFrame({"x": [1]}),
            mappings={},
            settings={},
            context={},
            template_name="t",
            frame_config={"title": "Test"},
        )
        assert spec.frame_config == {"title": "Test"}

    def test_invalid_transform_raises(self):
        with pytest.raises(TypeError, match="LinkTransform"):
            FigureSpec(
                data=pd.DataFrame({"x": [1]}),
                mappings={},
                settings={},
                context={},
                template_name="t",
                transform="not_a_transform",
            )

    def test_invalid_frame_config_raises(self):
        with pytest.raises(TypeError, match="frame_config"):
            FigureSpec(
                data=pd.DataFrame({"x": [1]}),
                mappings={},
                settings={},
                context={},
                template_name="t",
                frame_config=["not", "a", "dict"],
            )


# ---------------------------------------------------------------------------
# Serialization round-trips
# ---------------------------------------------------------------------------


class TestFigureSpecChildrenSerialization:
    def _child_spec(self):
        return FigureSpec(
            data=pd.DataFrame({"v": [1.0, 2.0]}),
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
                    coord=CoordCartesian(),
                    transform=LinkTransform(rotate=45, scale=(1, 0.5)),
                    frame_config={"title": "LEFT"},
                ),
                FigureSpec(
                    data=pd.DataFrame({"v": [1.0]}),
                    mappings={},
                    settings={},
                    context={},
                    template_name="child2",
                    coord=CoordPolar(theta="x"),
                    transform=LinkTransform(translate=(-0.5, 0.0)),
                ),
            ),
        )

    def test_spec_with_children_roundtrips(self):
        spec = self._child_spec()
        restored = figure_spec_from_dict(figure_spec_to_dict(spec))
        assert len(restored.children) == 2
        assert restored.children[0].transform == LinkTransform(rotate=45, scale=(1, 0.5))
        assert type(restored.children[1].coord) is CoordPolar
        assert restored.children[1].transform.translate == (-0.5, 0.0)
        assert restored.children[0].frame_config == {"title": "LEFT"}

    def test_spec_with_children_json_roundtrip(self):
        spec = self._child_spec()
        restored = spec_from_json(spec_to_json(spec))
        assert len(restored.children) == 2
        assert restored.children[0].transform.rotate == 45.0

    def test_payload_without_children_still_loads(self):
        spec = _make_spec()
        d = figure_spec_to_dict(spec)
        assert "children" in d
        del d["children"]
        restored = figure_spec_from_dict(d)
        assert restored.children == ()
