"""Unit tests for the secondary-axis data model and mapping helpers (WP-A)."""

import pandas as pd
import pytest

from geofig_engine.core.secondary_axis import (
    SecondaryAxis,
    linear_mapping,
    parse_secondary_settings,
)
from geofig_engine.core.spec import FigureSpec, validate_figure_spec
from geofig_engine.serialize import spec_from_json, spec_to_json


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

    def test_named_tick_values_include_edges(self):
        axis = SecondaryAxis(
            "y",
            (0, 2),
            1,
            "upright",
            "right",
            "",
            (0, 2),
            tick_labels={0: "SO4", 1: "HCO3", 2: "Cl"},
        )
        assert axis.tick_values() == [0.0, 1.0, 2.0]
        assert axis.tick_coordinates() == [
            (0.0, 0.0),
            (1.0, 1.0),
            (2.0, 2.0),
        ]

    def test_named_ticks_map_through_linear_range(self):
        axis = SecondaryAxis(
            "y",
            (100, 0),
            20,
            "upright",
            "right",
            "",
            (0, 100),
            tick_labels={100: "top", 20: "mid"},
        )
        assert axis.tick_values() == [20.0, 100.0]
        coords = dict(axis.tick_coordinates())
        assert coords[100] == pytest.approx(0)
        assert coords[20] == pytest.approx(80)

    def test_abs_ticks_and_tick_labels_construct(self):
        axis = SecondaryAxis(
            "x",
            (0, 2),
            1,
            "upright",
            "top",
            "",
            (0, 2),
            abs_ticks=True,
            tick_labels={0: "a", 2: "b"},
        )
        assert axis.abs_ticks is True
        assert axis.tick_labels == {0.0: "a", 2.0: "b"}

    def test_named_tick_labels_normalize_string_keys(self):
        axis = SecondaryAxis(
            "x",
            (0, 2),
            1,
            "upright",
            "top",
            "",
            (0, 2),
            tick_labels={"0": "a", "2": "b"},
        )
        assert axis.tick_labels == {0.0: "a", 2.0: "b"}

    def test_invalid_abs_ticks_raises(self):
        with pytest.raises(ValueError):
            SecondaryAxis(
                "x", (0, 2), 1, "upright", "top", "", (0, 2), abs_ticks="yes"
            )

    def test_invalid_tick_labels_raises(self):
        for bad in ("nope", {0: ""}, {"x": "a"}, {0: 5}, {True: "a"}):
            with pytest.raises(ValueError):
                SecondaryAxis(
                    "x", (0, 2), 1, "upright", "top", "", (0, 2), tick_labels=bad
                )


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

    def test_inherits_axis_tick_policies_from_defaults(self):
        axes = parse_secondary_settings(
            {"secondary_x": {"range": [100, 0]}},
            xlim=(0, 200),
            ylim=(0, 200),
            defaults={
                "axis_label_policy": "parallel",
                "tick_label_policy": "upright",
            },
        )
        axis = axes["x"]
        assert axis.axis_label_policy == "parallel"
        assert axis.tick_label_policy == "upright"
        assert axis.axis_label_policy_eff() == "parallel"
        assert axis.tick_label_policy_eff() == "upright"

    def test_secondary_axis_tick_policies_override_defaults(self):
        axes = parse_secondary_settings(
            {
                "secondary_x": {
                    "range": [100, 0],
                    "axis_label_policy": "upright",
                    "tick_label_policy": "parallel",
                }
            },
            defaults={
                "axis_label_policy": "parallel",
                "tick_label_policy": "upright",
            },
        )
        axis = axes["x"]
        assert axis.axis_label_policy == "upright"
        assert axis.tick_label_policy == "parallel"
        assert axis.axis_label_policy_eff() == "upright"
        assert axis.tick_label_policy_eff() == "parallel"

    def test_inherits_frame_majortick_defaults(self):
        axes = parse_secondary_settings(
            {"secondary_x": {"range": [100, 0]}},
            xlim=(0, 200),
            ylim=(0, 200),
            defaults={
                "majortick_length": 0.06,
                "majortick_offset": 0.25,
                "majortick_width": 2.0,
                "majortick_color": "tab:red",
            },
        )
        axis = axes["x"]
        assert axis.majortick_length == 0.06
        assert axis.majortick_offset == 0.25
        assert axis.majortick_width == 2.0
        assert axis.majortick_color == "tab:red"

    def test_secondary_majortick_values_override_frame_defaults(self):
        axes = parse_secondary_settings(
            {
                "secondary_y": {
                    "range": [0, 2],
                    "majortick_length": 0.3,
                    "majortick_offset": 1,
                    "majortick_width": 3.5,
                    "majortick_color": "blue",
                }
            },
            defaults={
                "majortick_length": 0.06,
                "majortick_offset": 0.0,
                "majortick_width": 1.0,
                "majortick_color": "black",
            },
        )
        axis = axes["y"]
        assert axis.majortick_length == 0.3
        assert axis.majortick_offset == 1
        assert axis.majortick_width == 3.5
        assert axis.majortick_color == "blue"

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

    def test_named_tick_labels_declared(self):
        axes = parse_secondary_settings(
            {
                "secondary_y": {
                    "range": [0, 2],
                    "abs_ticks": True,
                    "tick_labels": {0: "SO4", 1: "HCO3", 2: "Cl"},
                }
            },
            xlim=(0, 2),
            ylim=(0, 2),
        )
        axis = axes["y"]
        assert axis.abs_ticks is True
        assert axis.tick_labels == {0.0: "SO4", 1.0: "HCO3", 2.0: "Cl"}

    def test_named_tick_labels_inherited_from_defaults(self):
        axes = parse_secondary_settings(
            {"secondary_y": {"range": [0, 2]}},
            xlim=(0, 2),
            ylim=(0, 2),
            defaults={
                "abs_ticks": True,
                "tick_labels": {1: "mid"},
            },
        )
        axis = axes["y"]
        assert axis.abs_ticks is True
        assert axis.tick_labels == {1.0: "mid"}

    def test_invalid_named_tick_labels_raises(self):
        with pytest.raises(ValueError):
            parse_secondary_settings(
                {"secondary_x": {"range": [0, 2], "tick_labels": {0: ""}}}
            )
        with pytest.raises(ValueError):
            parse_secondary_settings(
                {"secondary_x": {"range": [0, 2], "tick_labels": {"x": "a"}}}
            )
        with pytest.raises(ValueError):
            parse_secondary_settings(
                {"secondary_x": {"range": [0, 2], "abs_ticks": 1}}
            )


class TestSecondarySettingsSerialization:
    def _spec(self, settings):
        return FigureSpec(
            data=pd.DataFrame({"v": [1.0]}),
            mappings={},
            settings=settings,
            context={},
            template_name="test",
        )

    def test_secondary_range_survives_json_round_trip_as_tuple(self):
        spec = self._spec({
            "xlim": (0, 100),
            "ylim": (0, 100),
            "secondary_x": {"range": [0, 100], "label": "Anions (%)"},
            "secondary_y": {"range": [100, 0], "tick_step": 20},
        })
        restored = spec_from_json(spec_to_json(spec))
        assert restored.settings["secondary_x"]["range"] == (0, 100)
        assert restored.settings["secondary_y"]["range"] == (100, 0)
        assert restored.settings["secondary_x"]["label"] == "Anions (%)"
        assert restored.settings["secondary_y"]["tick_step"] == 20

    def test_xlim_ylim_still_restored(self):
        spec = self._spec({"xlim": (0, 100), "ylim": (0, 100)})
        restored = spec_from_json(spec_to_json(spec))
        assert restored.settings["xlim"] == (0, 100)
        assert restored.settings["ylim"] == (0, 100)

    def test_tick_labels_survive_json_round_trip(self):
        spec = self._spec({
            "xlim": (0, 2),
            "ylim": (0, 2),
            "secondary_y": {
                "range": [0, 2],
                "abs_ticks": True,
                "tick_labels": {0: "SO4", 1: "HCO3", 2: "Cl"},
            },
        })
        restored = spec_from_json(spec_to_json(spec))
        decl = restored.settings["secondary_y"]
        assert decl["abs_ticks"] is True
        assert decl["tick_labels"] == {"0": "SO4", "1": "HCO3", "2": "Cl"}
        axes = parse_secondary_settings(
            {"secondary_y": decl}, xlim=(0, 2), ylim=(0, 2)
        )
        assert axes["y"].abs_ticks is True
        assert axes["y"].tick_labels == {0.0: "SO4", 1.0: "HCO3", 2.0: "Cl"}


class TestSecondarySettingsValidation:
    def _spec(self, settings):
        return FigureSpec(
            data=pd.DataFrame({"v": [1.0]}),
            mappings={},
            settings=settings,
            context={},
            template_name="test",
        )

    def test_valid_secondary_settings_pass(self):
        spec = self._spec({
            "xlim": (0, 100), "ylim": (0, 100),
            "secondary_x": {"range": [0, 100], "tick_step": 20, "label_policy": "upright"},
            "secondary_y": {"range": [100, 0], "position": "right"},
        })
        validate_figure_spec(spec)

    def test_missing_range_raises(self):
        with pytest.raises(ValueError):
            validate_figure_spec(self._spec({"secondary_x": {"tick_step": 20}}))

    def test_non_mapping_declaration_raises(self):
        with pytest.raises(ValueError):
            validate_figure_spec(self._spec({"secondary_x": [0, 100]}))

    def test_degenerate_range_raises(self):
        with pytest.raises(ValueError):
            validate_figure_spec(self._spec({"secondary_x": {"range": [50, 50]}}))

    def test_invalid_policy_raises(self):
        with pytest.raises(ValueError):
            validate_figure_spec(self._spec(
                {"secondary_x": {"range": [0, 100], "label_policy": "diagonal"}}))

    def test_invalid_axis_tick_policy_raises(self):
        with pytest.raises(ValueError):
            validate_figure_spec(self._spec(
                {"secondary_x": {"range": [0, 100], "axis_label_policy": "diagonal"}}))
        with pytest.raises(ValueError):
            validate_figure_spec(self._spec(
                {"secondary_x": {"range": [0, 100], "tick_label_policy": "diagonal"}}))

    def test_invalid_position_raises(self):
        with pytest.raises(ValueError):
            validate_figure_spec(self._spec(
                {"secondary_y": {"range": [0, 100], "position": "top"}}))

    def test_nonpositive_tick_step_raises(self):
        with pytest.raises(ValueError):
            validate_figure_spec(self._spec(
                {"secondary_y": {"range": [0, 100], "tick_step": 0}}))

    def test_valid_named_tick_labels_pass(self):
        validate_figure_spec(self._spec({
            "xlim": (0, 2),
            "ylim": (0, 2),
            "secondary_y": {
                "range": [0, 2],
                "abs_ticks": True,
                "tick_labels": {0: "SO4", 1: "HCO3", 2: "Cl"},
            },
        }))

    def test_invalid_named_tick_labels_raise(self):
        with pytest.raises(ValueError):
            validate_figure_spec(self._spec(
                {"secondary_y": {"range": [0, 2], "tick_labels": {0: ""}}}))
        with pytest.raises(ValueError):
            validate_figure_spec(self._spec(
                {"secondary_y": {"range": [0, 2], "abs_ticks": 1}}))
