"""
Tests for the AxisFormat model and parse_axis_settings (Phase 14.54 WP-A).

Covers the shared declarative axis-formatting model consumed by the unified
frame pipeline: structured ``settings["axis"]`` parsing, the legacy flat-key
fallback, appearance knobs, and validation.
"""

import pytest

from geofig_engine.core.axis import AxisFormat, parse_axis_settings, VALID_LABEL_POLICIES
from geofig_engine.core.coord import CoordCartesian, CoordPolar, TernaryCoord


@pytest.fixture(params=[CoordCartesian(), CoordPolar(), TernaryCoord()])
def coord(request):
    return request.param


@pytest.mark.parametrize("with_coord", [True, False])
def test_defaults_no_crash(with_coord):
    coord = CoordCartesian() if with_coord else None
    a = parse_axis_settings({}, coord)
    assert isinstance(a, AxisFormat)
    assert a.title == ""
    assert a.xlabel is None
    assert a.ylabel is None
    assert a.limits is None
    assert a.label_policy == "upright"


def test_tick_format_defaults_to_g():
    a = parse_axis_settings({}, CoordCartesian())
    assert a.tick_format == ":g"


def test_appearance_knob_defaults():
    a = parse_axis_settings({}, CoordCartesian())
    assert a.tick_fontsize == 5
    assert a.label_fontsize == 7
    assert a.title_fontsize == 7
    assert a.grid_style == {"color": "gray", "linewidth": 0.3, "linestyle": ":"}
    assert a.frame_linewidth == 1.0
    assert a.label_offset is None


def test_explicit_axis_parses_fields():
    a = parse_axis_settings(
        {
            "axis": {
                "title": "T",
                "limits": [[0, 100], [0, 100]],
                "grid": True,
                "grid_step": 20,
                "tick_step": 10,
                "label_policy": "parallel",
                "xscale": "log",
                "tick_format": "{:.1f}",
            }
        },
        CoordCartesian(),
    )
    assert a.title == "T"
    assert a.limits == ((0.0, 100.0), (0.0, 100.0))
    assert a.grid is True
    assert a.grid_step == 20.0
    assert a.tick_step == 10.0
    assert a.label_policy == "parallel"
    assert a.xscale == "log"
    assert a.tick_format == "{:.1f}"


@pytest.mark.parametrize("coord", [CoordCartesian(), CoordPolar(), TernaryCoord()])
def test_explicit_and_legacy_parity(coord):
    explicit = {
        "axis": {
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "limits": [[0, 100], [20, 80]],
            "grid": True,
            "grid_step": 20,
            "tick_step": 10,
            "label_policy": "parallel",
            "xscale": "linear",
            "yscale": "linear",
            "time_format": "%H:%M",
            "tick_format": "{:.1f}",
        }
    }
    legacy = {
        "title": "T",
        "xlabel": "X",
        "ylabel": "Y",
        "xlim": [0, 100],
        "ylim": [20, 80],
        "grid": True,
        "grid_step": 20,
        "tick_step": 10,
        "label_policy": "parallel",
        "xscale": "linear",
        "yscale": "linear",
        "time_format": "%H:%M",
        "tick_format": "{:.1f}",
    }
    assert parse_axis_settings(explicit, coord) == parse_axis_settings(legacy, coord)


@pytest.mark.parametrize("coord", [CoordCartesian(), CoordPolar(), TernaryCoord()])
def test_legacy_polar_options_map(coord):
    settings = {
        "hide_spine": True,
        "hide_angular_ticks": True,
        "hide_angular_labels": True,
        "hide_radial_labels": True,
        "hide_radial_ticks": True,
        "polar_tick_labels": 1,
    }
    a = parse_axis_settings(settings, coord)
    assert a.option("hide_spine") is True
    assert a.option("hide_angular_ticks") is True
    assert a.option("hide_angular_labels") is True
    assert a.option("hide_radial_labels") is True
    assert a.option("hide_radial_ticks") is True
    assert a.option("polar_tick_labels") == 1


def test_explicit_options_pass_through():
    a = parse_axis_settings(
        {"axis": {"options": {"hide_spine": True, "polar_tick_labels": 1}}},
        CoordPolar(),
    )
    assert a.option("hide_spine") is True
    assert a.option("polar_tick_labels") == 1
    assert a.option("missing", "d") == "d"


def test_limits_pair_of_pairs_coerced():
    a = parse_axis_settings(
        {"axis": {"limits": ([0, 10], [5, 15])}}, CoordCartesian()
    )
    assert a.limits == ((0.0, 10.0), (5.0, 15.0))


def test_xlim_ylim_properties():
    a = parse_axis_settings(
        {"axis": {"limits": [[0, 100], [20, 80]]}}, CoordCartesian()
    )
    assert a.xlim == (0.0, 100.0)
    assert a.ylim == (20.0, 80.0)
    a2 = parse_axis_settings({}, CoordCartesian())
    assert a2.xlim is None
    assert a2.ylim is None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "axis",
    [
        {"limits": [0, 100]},  # not a pair of pairs
        {"limits": [[0, 100], [0]]},  # ylim not a pair
        {"limits": [[0, "a"], [0, 1]]},  # non-numeric
        {"grid_step": -2},  # non-positive
        {"tick_step": 0},  # non-positive
        {"label_policy": "bad"},  # invalid policy
        {"tick_format": None},  # not a string
        {"grid_style": "nope"},  # not a dict
        {"options": "nope"},  # not a dict
    ],
)
def test_invalid_axis_raises(axis):
    with pytest.raises(ValueError):
        AxisFormat(**axis)


@pytest.mark.parametrize("coord", [CoordCartesian(), CoordPolar(), TernaryCoord()])
def test_legacy_invalid_cases_raise(coord):
    with pytest.raises(ValueError):
        parse_axis_settings({"tick_step": -2}, coord)
    with pytest.raises(ValueError):
        parse_axis_settings({"label_policy": "bad"}, coord)
    with pytest.raises(ValueError):
        parse_axis_settings({"xlim": [0, "a"], "ylim": [0, 1]}, coord)


def test_grid_style_dict_enforced():
    with pytest.raises(ValueError):
        AxisFormat(grid_style=None)


def test_fontsize_positive():
    with pytest.raises(ValueError):
        AxisFormat(tick_fontsize=0)
    with pytest.raises(ValueError):
        AxisFormat(label_fontsize=-1)


def test_label_policy_constant():
    assert VALID_LABEL_POLICIES == ("upright", "parallel")


def test_no_matplotlib_import():
    import ast
    import inspect
    import geofig_engine.core.axis as axis

    tree = ast.parse(inspect.getsource(axis))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    assert not any(name.split(".")[0] == "matplotlib" for name in imports)
