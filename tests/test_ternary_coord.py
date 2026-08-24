"""
Tests for TernaryCoord: projection math, visual-mapping rewriting,
validation, and serialization round-trips (Phase 14.5 WP2).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from geofig_engine.core.coord import (
    TERNARY_HEIGHT,
    CoordPolar,
    TernaryCoord,
    ternary_project,
)
from geofig_engine.core.geom import GeomLine, GeomPoint
from geofig_engine.serialize import coord_from_dict, coord_to_dict, spec_from_json, spec_to_json


def _frac_mapping(a, b, c):
    n = len(a)
    return {
        "a": pd.Series(a, name="fa", index=pd.RangeIndex(n)),
        "b": pd.Series(b, name="fb", index=pd.RangeIndex(n)),
        "c": pd.Series(c, name="fc", index=pd.RangeIndex(n)),
    }


# ---------------------------------------------------------------------------
# ternary_project math
# ---------------------------------------------------------------------------


class TestTernaryProject:
    def test_corners_left_handed(self):
        x, y = ternary_project(1.0, 0.0, 0.0)
        assert x == pytest.approx(0.5)
        assert y == pytest.approx(TERNARY_HEIGHT)

        x, y = ternary_project(0.0, 1.0, 0.0)
        assert (x, y) == (0.0, 0.0)

        x, y = ternary_project(0.0, 0.0, 1.0)
        assert (x, y) == (1.0, 0.0)

    def test_centroid_of_equal_mix(self):
        x, y = ternary_project(1 / 3, 1 / 3, 1 / 3)
        assert x == pytest.approx(0.5)
        assert y == pytest.approx(TERNARY_HEIGHT / 3)

    def test_height_is_equilateral(self):
        assert TERNARY_HEIGHT == pytest.approx(np.sqrt(3) / 2)

    def test_right_handed_mirrors_bottom_corners(self):
        xl, _ = ternary_project(0.2, 0.5, 0.3, handedness="left")
        xr, _ = ternary_project(0.2, 0.5, 0.3, handedness="right")
        assert xr == pytest.approx(1.0 - xl)

    def test_right_handed_swaps_corner_ownership(self):
        # b moves to bottom-right, c to bottom-left; apex unchanged.
        xb, yb = ternary_project(0.0, 1.0, 0.0, handedness="right")
        xc, yc = ternary_project(0.0, 0.0, 1.0, handedness="right")
        assert (xb, yb) == (pytest.approx(1.0), pytest.approx(0.0))
        assert (xc, yc) == (pytest.approx(0.0), pytest.approx(0.0))

    def test_apex_same_both_handedness(self):
        _, yl = ternary_project(1.0, 0.0, 0.0, handedness="left")
        xr, yr = ternary_project(1.0, 0.0, 0.0, handedness="right")
        assert xr == pytest.approx(0.5)
        assert yr == pytest.approx(yl)

    def test_invalid_handedness_raises(self):
        with pytest.raises(ValueError, match="handedness"):
            ternary_project(1, 0, 0, handedness="up")

    def test_accepts_array_input(self):
        a = np.array([1.0, 0.0])
        b = np.zeros(2)
        c = np.zeros(2)
        x, y = ternary_project(a, b, c)
        np.testing.assert_allclose(x, [0.5, 0.0])


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------


class TestTernaryCoordConstruction:
    def test_defaults(self):
        coord = TernaryCoord()
        assert coord.channels == ("a", "b", "c")
        assert coord.handedness == "left"

    def test_custom_channels_and_handedness(self):
        coord = TernaryCoord(channels=("cat_f0", "cat_f1", "cat_f2"), handedness="right")
        assert coord.channels == ("cat_f0", "cat_f1", "cat_f2")
        assert coord.handedness == "right"

    def test_list_coerced_to_tuple(self):
        assert TernaryCoord(channels=["x", "y", "z"]).channels == ("x", "y", "z")

    def test_wrong_channel_count_raises(self):
        with pytest.raises(ValueError, match="exactly three"):
            TernaryCoord(channels=("a", "b"))

    def test_duplicate_channels_raise(self):
        with pytest.raises(ValueError, match="distinct"):
            TernaryCoord(channels=("a", "a", "c"))

    def test_non_string_channel_raises(self):
        with pytest.raises(ValueError, match="non-empty strings"):
            TernaryCoord(channels=("a", 2, "c"))

    def test_string_channels_raise(self):
        with pytest.raises(TypeError, match="sequence"):
            TernaryCoord(channels="abc")

    def test_invalid_handedness_raises(self):
        with pytest.raises(ValueError, match="handedness"):
            TernaryCoord(handedness="diagonal")


# ---------------------------------------------------------------------------
# transform_visual_mapping
# ---------------------------------------------------------------------------


class TestTernaryTransformMapping:
    def _project(self, coord, mapping):
        return coord.transform_visual_mapping(mapping, geom=GeomPoint())

    def test_pure_fractions_land_on_corners(self):
        coord = TernaryCoord()
        vm = self._project(coord, _frac_mapping([1, 0, 0], [0, 1, 0], [0, 0, 1]))
        np.testing.assert_allclose(vm["x"], [0.5, 0.0, 1.0], atol=1e-12)
        np.testing.assert_allclose(vm["y"], [TERNARY_HEIGHT, 0.0, 0.0], atol=1e-12)

    def test_right_handed_projection(self):
        coord = TernaryCoord(handedness="right")
        vm = self._project(coord, _frac_mapping([0, 1], [1, 0], [0, 0]))
        np.testing.assert_allclose(vm["x"], [1.0, 0.5], atol=1e-12)

    def test_fraction_channels_removed_from_mapping(self):
        coord = TernaryCoord()
        vm = self._project(coord, _frac_mapping([1, 0], [0, 1], [0, 0]))
        for ch in ("a", "b", "c"):
            assert ch not in vm
        assert "x" in vm and "y" in vm

    def test_non_fraction_channels_preserved(self):
        coord = TernaryCoord()
        mapping = _frac_mapping([1], [0], [0])
        mapping["color"] = "blue"
        mapping["size"] = pd.Series([3.0])
        vm = self._project(coord, mapping)
        assert vm["color"] == "blue"
        assert list(vm["size"]) == [3.0]

    def test_unnormalized_rows_are_normalized(self):
        coord = TernaryCoord()
        vm = self._project(coord, _frac_mapping([2.0], [6.0], [2.0]))
        # normalized to (0.2, 0.6, 0.2): x = 0.5*0.2 + 0.2 = 0.3
        np.testing.assert_allclose(vm["x"], [0.3], atol=1e-12)
        np.testing.assert_allclose(vm["y"], [TERNARY_HEIGHT * 0.2], atol=1e-12)

    def test_zero_total_rows_become_nan(self):
        coord = TernaryCoord()
        vm = self._project(coord, _frac_mapping([0.0, 1.0], [0.0, 0.0], [0.0, 0.0]))
        assert np.isnan(vm["x"].iloc[0]) and np.isnan(vm["y"].iloc[0])
        assert vm["x"].iloc[1] == pytest.approx(0.5)  # valid row unaffected

    def test_near_one_float_sums_do_not_raise(self):
        coord = TernaryCoord()
        vm = self._project(
            coord, _frac_mapping([0.3333333], [0.3333333], [0.3333334])
        )
        assert vm["y"].iloc[0] == pytest.approx(TERNARY_HEIGHT / 3, rel=1e-6)

    def test_missing_channel_raises_with_names(self):
        coord = TernaryCoord(channels=("p", "q", "r"))
        with pytest.raises(ValueError, match=r"\['q', 'r'\]"):
            self._project(coord, {"p": pd.Series([1.0])})

    def test_constant_channel_raises_typeerror(self):
        coord = TernaryCoord()
        mapping = _frac_mapping([1], [0], [0])
        mapping["c"] = 0.5  # constant, not a column reference
        with pytest.raises(TypeError, match="pd.Series"):
            self._project(coord, mapping)

    def test_index_preserved(self):
        coord = TernaryCoord()
        idx = pd.Index([10, 20, 30])
        mapping = {
            "a": pd.Series([1.0, 0.0, 0.0], index=idx),
            "b": pd.Series([0.0, 1.0, 0.0], index=idx),
            "c": pd.Series([0.0, 0.0, 1.0], index=idx),
        }
        vm = self._project(coord, mapping)
        assert list(vm["x"].index) == list(idx)

    def test_geom_agnostic(self):
        coord = TernaryCoord()
        for geom in (GeomPoint(), GeomLine(), None):
            vm = coord.transform_visual_mapping(_frac_mapping([1], [0], [0]), geom)
            assert vm["x"].iloc[0] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestTernarySerialization:
    def test_coord_dict_shape(self):
        d = coord_to_dict(TernaryCoord())
        assert d == {
            "type": "ternary",
            "params": {"channels": ["a", "b", "c"], "handedness": "left"},
        }

    def test_roundtrip_default(self):
        restored = coord_from_dict(coord_to_dict(TernaryCoord()))
        assert isinstance(restored, TernaryCoord)
        assert restored.channels == ("a", "b", "c")
        assert restored.handedness == "left"

    def test_roundtrip_custom(self):
        coord = TernaryCoord(
            channels=("cation_f0", "cation_f1", "cation_f2"), handedness="right"
        )
        restored = coord_from_dict(coord_to_dict(coord))
        assert restored.channels == ("cation_f0", "cation_f1", "cation_f2")
        assert restored.handedness == "right"
        assert restored.params["channels"] == ["cation_f0", "cation_f1", "cation_f2"]

    def test_spec_json_roundtrip(self):
        from geofig_engine.core.spec import FigureSpec

        spec = FigureSpec(
            data=pd.DataFrame({"f0": [1.0], "f1": [0.0], "f2": [0.0]}),
            mappings={},
            settings={},
            context={},
            template_name="test",
            coord=TernaryCoord(channels=("f0", "f1", "f2")),
        )
        restored = spec_from_json(spec_to_json(spec))
        assert type(restored.coord) is TernaryCoord
        assert restored.coord.channels == ("f0", "f1", "f2")


# ---------------------------------------------------------------------------
# Integration: main-coord application path used by the renderer
# ---------------------------------------------------------------------------


class TestRendererIntegrationPath:
    def test_works_through_apply_coord_transform(self):
        """The renderer's generic coord application must handle TernaryCoord."""
        import dataclasses

        from geofig_engine.core.layer import LayerSpec
        from geofig_engine.core.spec import FigureSpec

        df = pd.DataFrame({"a": [1.0, 0.0], "b": [0.0, 1.0], "c": [0.0, 0.0]})
        spec = FigureSpec(
            data=df,
            mappings={},
            settings={},
            context={},
            template_name="test",
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=None,
                    visual_mapping={
                        "a": df["a"],
                        "b": df["b"],
                        "c": df["c"],
                        "color": "k",
                    },
                )
            ],
            coord=TernaryCoord(),
        )
        trans = spec.coord.transform_visual_mapping(
            dict(spec.layers[0].visual_mapping), spec.layers[0].geom
        )
        assert set(trans) == {"x", "y", "color"}
        replaced = dataclasses.replace(spec.layers[0], visual_mapping=trans)
        assert replaced.visual_mapping["color"] == "k"
