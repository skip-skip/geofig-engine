"""
Tests for core.link: LinkTransform math, AxisLink validation, FigureSpec
integration, and serialization round-trips (Phase 14.5 WP1).

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
from geofig_engine.core.link import AxisLink, LinkTransform
from geofig_engine.core.spec import FigureSpec, build_spec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.serialize import (
    figure_spec_from_dict,
    figure_spec_to_dict,
    link_from_dict,
    link_to_dict,
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
# AxisLink validation
# ---------------------------------------------------------------------------


class TestAxisLinkValidation:
    def test_minimal_construction(self):
        link = AxisLink(name="cation", coord=CoordCartesian())
        assert link.transform == LinkTransform()
        assert link.frame is None

    def test_frame_dict_accepted(self):
        link = AxisLink(name="a", coord=CoordCartesian(), frame={"color": "k"})
        assert link.frame == {"color": "k"}

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            AxisLink(name="", coord=CoordCartesian())

    def test_whitespace_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            AxisLink(name="   ", coord=CoordCartesian())

    def test_non_string_name_raises(self):
        with pytest.raises(ValueError, match="non-empty string"):
            AxisLink(name=42, coord=CoordCartesian())

    def test_non_coord_raises(self):
        with pytest.raises(TypeError, match="Coord"):
            AxisLink(name="a", coord="cartesian")

    def test_non_transform_raises(self):
        with pytest.raises(TypeError, match="LinkTransform"):
            AxisLink(name="a", coord=CoordCartesian(), transform={"translate": [0, 0]})

    def test_non_dict_frame_raises(self):
        with pytest.raises(TypeError, match="frame"):
            AxisLink(name="a", coord=CoordCartesian(), frame=["color"])


# ---------------------------------------------------------------------------
# FigureSpec integration
# ---------------------------------------------------------------------------


def _make_spec(links=(), layers=None):
    return FigureSpec(
        data=pd.DataFrame({"x": [1, 2], "y": [3, 4]}),
        mappings={},
        settings={},
        context={},
        template_name="test",
        layers=layers if layers is not None else [],
        links=links,
    )


class TestFigureSpecLinks:
    def test_default_links_empty(self):
        assert FigureSpec(
            data=pd.DataFrame({"x": [1]}),
            mappings={},
            settings={},
            context={},
            template_name="t",
        ).links == ()

    def test_valid_links_pass_validation(self):
        links = (
            AxisLink(name="cation", coord=CoordCartesian()),
            AxisLink(name="anion", coord=CoordPolar(theta="x")),
        )
        spec = _make_spec(links=links)
        assert spec.links == links

    def test_duplicate_link_names_raise(self):
        with pytest.raises(ValueError, match="duplicate link name: 'cation'"):
            _make_spec(
                links=(
                    AxisLink(name="cation", coord=CoordCartesian()),
                    AxisLink(name="cation", coord=CoordCartesian()),
                )
            )

    def test_non_axislink_in_links_raises(self):
        with pytest.raises(TypeError, match="AxisLink"):
            _make_spec(links=("cation",))

    def test_unrouted_subplot_raises_when_links_present(self):
        layer = LayerSpec(
            geom=GeomPoint(),
            stat=StatIdentity(),
            visual_mapping={},
            subplot="nope",
        )
        with pytest.raises(ValueError, match="does not match any link"):
            _make_spec(
                links=(AxisLink(name="cation", coord=CoordCartesian()),),
                layers=[layer],
            )

    def test_routed_subplot_resolves(self):
        layer = LayerSpec(
            geom=GeomPoint(),
            stat=StatIdentity(),
            visual_mapping={},
            subplot="cation",
        )
        spec = _make_spec(
            links=(AxisLink(name="cation", coord=CoordCartesian()),),
            layers=[layer],
        )
        assert spec.layers[0].subplot == "cation"

    def test_legacy_subplot_without_links_still_valid(self):
        # Pre-14.5 per-diagram subplot names must keep validating until the
        # legacy renderer paths are removed.
        layer = LayerSpec(
            geom=GeomPoint(),
            stat=StatIdentity(),
            visual_mapping={},
            subplot="left_tri",
        )
        spec = _make_spec(layers=[layer])
        assert spec.links == ()

    def test_build_spec_accepts_links(self):
        link = AxisLink(name="anion", coord=CoordCartesian())
        spec = build_spec(
            data=pd.DataFrame({"x": [1]}),
            mappings={},
            settings={},
            context={},
            template_name="t",
            links=(link,),
        )
        assert spec.links == (link,)


# ---------------------------------------------------------------------------
# Serialization round-trips
# ---------------------------------------------------------------------------


class TestLinkSerialization:
    def test_transform_nested_in_link_dict(self):
        link = AxisLink(
            name="diamond",
            coord=CoordCartesian(),
            transform=LinkTransform(translate=(1, 2), rotate=45, scale=(1, 0.5)),
        )
        d = link_to_dict(link)
        assert d["transform"] == {
            "translate": [1.0, 2.0],
            "rotate": 45.0,
            "scale": [1.0, 0.5],
        }

    def test_roundtrip_with_params_coord_and_frame(self):
        link = AxisLink(
            name="cation",
            coord=CoordPolar(theta="x"),
            transform=LinkTransform(translate=(-0.5, 0.0), rotate=15, scale=(2, 3)),
            frame={"edgecolor": "k", "label_policy": "parallel"},
        )
        restored = link_from_dict(link_to_dict(link))
        assert restored.name == "cation"
        assert type(restored.coord) is CoordPolar
        assert restored.coord.params["theta"] == "x"
        assert restored.transform == link.transform
        assert restored.frame == {"edgecolor": "k", "label_policy": "parallel"}

    def test_frame_omitted_when_none(self):
        d = link_to_dict(AxisLink(name="a", coord=CoordCartesian()))
        assert "frame" not in d
        restored = link_from_dict(d)
        assert restored.frame is None

    def test_unknown_coord_type_raises(self):
        d = link_to_dict(AxisLink(name="a", coord=CoordCartesian()))
        d["coord"]["type"] = "wat"
        with pytest.raises(ValueError, match="Unknown coord type"):
            link_from_dict(d)


class TestFigureSpecLinksSerialization:
    def _linked_spec(self):
        return _make_spec(
            links=(
                AxisLink(
                    name="diamond",
                    coord=CoordCartesian(),
                    transform=LinkTransform(rotate=45, scale=(1, 0.5)),
                ),
                AxisLink(
                    name="cation",
                    coord=CoordPolar(theta="x"),
                    transform=LinkTransform(translate=(-0.5, 0.0)),
                ),
            ),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={},
                    subplot="cation",
                )
            ],
        )

    def test_spec_with_links_roundtrips(self):
        spec = self._linked_spec()
        restored = figure_spec_from_dict(figure_spec_to_dict(spec))
        assert len(restored.links) == 2
        assert restored.links[0].name == "diamond"
        assert restored.links[0].transform == LinkTransform(rotate=45, scale=(1, 0.5))
        assert type(restored.links[1].coord) is CoordPolar
        assert restored.links[1].transform.translate == (-0.5, 0.0)
        assert restored.layers[0].subplot == "cation"

    def test_spec_with_links_json_roundtrip(self):
        spec = self._linked_spec()
        restored = spec_from_json(spec_to_json(spec))
        assert [lk.name for lk in restored.links] == ["diamond", "cation"]

    def test_payload_without_links_still_loads(self):
        spec = _make_spec()
        d = figure_spec_to_dict(spec)
        assert "links" in d  # current writer always emits the key
        del d["links"]      # but readers tolerate payloads predating it
        restored = figure_spec_from_dict(d)
        assert restored.links == ()
