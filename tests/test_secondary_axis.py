"""Unit tests for the secondary-axis data model and mapping helpers (WP-A)."""

import pytest

from geofig_engine.core.secondary_axis import (
    SecondaryAxis,
    linear_mapping,
    parse_secondary_settings,
)


class TestLinearMapping:
    def test_identity_ranges(self):
        fwd, inv = linear_mapping((0, 100), (0, 100))
        for v in (0, 25, 50, 75, 100):
            assert fwd(v) == pytest.approx(v)
            assert inv(v) == pytest.approx(v)

    def test_shift_and_scale(self):
        fwd, inv = linear_mapping((0, 100), (10, 30))
        assert fwd(0) == pytest.approx(10)
        assert fwd(50) == pytest.approx(20)
        assert fwd(100) == pytest.approx(30)
        assert inv(10) == pytest.approx(0)
        assert inv(30) == pytest.approx(100)

    def test_reversed_range_produces_complement(self):
        # range [100,0] on a [0,100] primary -> inv(80) == 20, etc.
        fwd, inv = linear_mapping((0, 100), (100, 0))
        assert inv(100) == pytest.approx(0)
        assert inv(80) == pytest.approx(20)
        assert inv(20) == pytest.approx(80)
        assert inv(0) == pytest.approx(100)
        assert fwd(80) == pytest.approx(20)

    def test_fwd_inv_roundtrip(self):
        fwd, inv = linear_mapping((0, 100), (100, 0))
        for p in (0, 15, 42, 63, 100):
            assert inv(fwd(p)) == pytest.approx(p)
            assert fwd(inv(p)) == pytest.approx(p)

    def test_degenerate_primary_raises(self):
        with pytest.raises(ValueError):
            linear_mapping((50, 50), (0, 100))

    def test_degenerate_secondary_raises(self):
        with pytest.raises(ValueError):
            linear_mapping((0, 100), (50, 50))

    def test_numeric_pair_validation(self):
        with pytest.raises(ValueError):
            linear_mapping("oops", (0, 100))
        with pytest.raises(ValueError):
            linear_mapping((0, 100), (0, 100, 200))


class TestSecondaryAxis:
    def test_construct_and_properties(self):
        axis = SecondaryAxis(
            orientation="x",
            range=(100, 0),
            tick_step=20,
            label_policy="upright",
            position="top",
            label="Anions (%)",
            primary_range=(0, 100),
        )
        assert axis.range == (100.0, 0.0)
        assert axis.inv(80) == pytest.approx(20)
        assert axis.fwd(20) == pytest.approx(80)

    def test_default_position_per_orientation(self):
        x = SecondaryAxis("x", (0, 100), 20, "upright", "top", "", (0, 100))
        y = SecondaryAxis("y", (0, 100), 20, "upright", "right", "", (0, 100))
        assert x.position == "top"
        assert y.position == "right"

    def test_degenerate_range_raises(self):
        with pytest.raises(ValueError):
            SecondaryAxis("x", (50, 50), 20, "upright", "top", "", (0, 100))

    def test_invalid_policy_raises(self):
        with pytest.raises(ValueError):
            SecondaryAxis("x", (0, 100), 20, "slanted", "top", "", (0, 100))

    def test_invalid_position_raises(self):
        with pytest.raises(ValueError):
            SecondaryAxis("y", (0, 100), 20, "upright", "top", "", (0, 100))

    def test_nonpositive_tick_step_raises(self):
        with pytest.raises(ValueError):
            SecondaryAxis("x", (0, 100), 0, "upright", "top", "", (0, 100))

    def test_tick_values_interior_only(self):
        # On [0,100] step 20, endpoints 0 and 100 are excluded.
        axis = SecondaryAxis("x", (0, 100), 20, "upright", "top", "", (0, 100))
        assert axis.tick_values() == [20.0, 40.0, 60.0, 80.0]

    def test_tick_values_reversed(self):
        axis = SecondaryAxis("x", (100, 0), 20, "upright", "top", "", (0, 100))
        assert axis.tick_values() == [20.0, 40.0, 60.0, 80.0]

    def test_tick_coordinates_reversed(self):
        axis = SecondaryAxis("y", (100, 0), 20, "upright", "right", "", (0, 100))
        coords = dict(axis.tick_coordinates())
        assert coords[80] == pytest.approx(20)
        assert coords[20] == pytest.approx(80)


class TestParseSecondarySettings:
    def test_none_returns_empty(self):
        assert parse_secondary_settings(None) == {}

    def test_missing_declarations_return_empty(self):
        assert parse_secondary_settings({"xlim": (0, 100), "ylim": (0, 100)}) == {}

    def test_declares_both_axes(self):
        axes = parse_secondary_settings({
            "xlim": (0, 100),
            "ylim": (0, 100),
            "tick_step": 20,
            "label_policy": "upright",
            "secondary_x": {"range": [100, 0], "label": "Anions (%)"},
            "secondary_y": {"range": [100, 0], "label": "Cations (%)"},
        })
        assert set(axes) == {"x", "y"}
        assert axes["x"].position == "top"
        assert axes["y"].position == "right"
        assert axes["x"].label == "Anions (%)"
        assert axes["x"].tick_step == 20
        assert axes["x"].primary_range == (0.0, 100.0)

    def test_inherits_defaults(self):
        axes = parse_secondary_settings(
            {"secondary_x": {"range": [100, 0]}},
            xlim=(0, 200),
            ylim=(0, 200),
            defaults={"tick_step": 40, "label_policy": "parallel"},
        )
        axis = axes["x"]
        assert axis.tick_step == 40
        assert axis.label_policy == "parallel"
        assert axis.primary_range == (0.0, 200.0)

    def test_explicit_xlim_ylim_override_settings(self):
        axes = parse_secondary_settings(
            {"xlim": (0, 50), "ylim": (0, 50), "secondary_x": {"range": [50, 0]}},
            xlim=(0, 100),
            ylim=(0, 100),
        )
        assert axes["x"].primary_range == (0.0, 100.0)

    def test_non_mapping_declaration_raises(self):
        with pytest.raises(ValueError):
            parse_secondary_settings({"secondary_x": [100, 0]})

    def test_missing_range_raises(self):
        with pytest.raises(ValueError):
            parse_secondary_settings({"secondary_x": {"tick_step": 20}})
