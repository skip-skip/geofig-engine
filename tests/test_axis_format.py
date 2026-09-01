"""
Tests for the AxisFormat model and parse_axis_settings (Phase 14.54 WP-A).

Covers the shared declarative axis-formatting model consumed by the unified
frame pipeline: flat top-level axis keys, appearance knobs, and validation.
"""

import numpy as np
import pandas as pd
import pytest

import matplotlib

from geofig_engine.core.axis import AxisFormat, parse_axis_settings, VALID_LABEL_POLICIES
from geofig_engine.core.coord import CoordCartesian, CoordPolar, TernaryCoord
from geofig_engine.core.geom import GeomLine
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.spec import FigureSpec
from geofig_engine.core.stat import StatIdentity


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
    assert a.tick_fontsize is None
    assert a.axis_label_fontsize is None
    assert a.title_fontsize is None
    assert a.fontsize is None
    assert a.xlabel_fontsize is None
    assert a.ylabel_fontsize is None
    assert a.suptitle_fontsize is None
    assert a.legend_fontsize is None
    assert a.facet_title_fontsize is None
    assert a.grid_style == {"color": "gray", "linewidth": 0.3, "linestyle": ":"}
    assert a.frame_linewidth == 1.0
    assert a.label_offset is None

    # Unset knobs resolve to the built-in defaults (current rendered output).
    assert a.resolve_fontsize("tick") == 5
    assert a.resolve_fontsize("axis_label") == 7
    assert a.resolve_fontsize("title") == 7
    assert a.resolve_fontsize("xlabel") == 10
    assert a.resolve_fontsize("ylabel") == 10
    assert a.resolve_fontsize("suptitle") == 14
    assert a.resolve_fontsize("legend") == 9
    assert a.resolve_fontsize("facet_title") == 10


def test_flat_axis_parses_fields():
    a = parse_axis_settings(
        {
            "title": "T",
            "xlim": [0, 100],
            "ylim": [0, 100],
            "grid": True,
            "grid_step": 20,
            "tick_step": 10,
            "label_policy": "parallel",
            "xscale": "log",
            "tick_format": "{:.1f}",
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


@pytest.mark.parametrize(
    "key,attr",
    [
        ("fontsize", "fontsize"),
        ("tick_fontsize", "tick_fontsize"),
        ("axis_label_fontsize", "axis_label_fontsize"),
        ("title_fontsize", "title_fontsize"),
        ("xlabel_fontsize", "xlabel_fontsize"),
        ("ylabel_fontsize", "ylabel_fontsize"),
        ("suptitle_fontsize", "suptitle_fontsize"),
        ("legend_fontsize", "legend_fontsize"),
        ("facet_title_fontsize", "facet_title_fontsize"),
    ],
)
def test_font_keys_parse_roundtrip(key, attr):
    a = parse_axis_settings({key: 12}, CoordCartesian())
    assert getattr(a, attr) == 12.0
    # Only the specified knob is set; all others remain unset (None).
    for check_attr in (
        "fontsize", "tick_fontsize", "axis_label_fontsize", "title_fontsize",
        "xlabel_fontsize", "ylabel_fontsize", "suptitle_fontsize",
        "legend_fontsize", "facet_title_fontsize",
    ):
        if check_attr == attr:
            continue
        assert getattr(a, check_attr) is None


def test_generic_fontsize_only_sets_generic():
    a = parse_axis_settings({"fontsize": 9}, CoordCartesian())
    assert a.fontsize == 9.0
    assert a.tick_fontsize is None
    assert a.axis_label_fontsize is None


def test_parse_font_keys_coerce_to_float_and_validate():
    a = parse_axis_settings({"title_fontsize": 11}, CoordCartesian())
    assert a.title_fontsize == 11.0
    with pytest.raises(ValueError):
        parse_axis_settings({"tick_fontsize": 0}, CoordCartesian())
    with pytest.raises(ValueError):
        parse_axis_settings({"fontsize": -3}, CoordCartesian())
    with pytest.raises(ValueError):
        parse_axis_settings({"legend_fontsize": True}, CoordCartesian())
    with pytest.raises(ValueError):
        parse_axis_settings({"suptitle_fontsize": "11"}, CoordCartesian())


@pytest.mark.parametrize("coord", [CoordCartesian(), CoordPolar(), TernaryCoord()])
def test_flat_keys_parse(coord):
    settings = {
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
    a = parse_axis_settings(settings, coord)
    assert a.title == "T"
    assert a.xlabel == "X"
    assert a.ylabel == "Y"
    assert a.limits == ((0.0, 100.0), (20.0, 80.0))
    assert a.grid is True
    assert a.grid_step == 20.0
    assert a.tick_step == 10.0
    assert a.label_policy == "parallel"
    assert a.xscale == "linear"
    assert a.yscale == "linear"
    assert a.time_format == "%H:%M"
    assert a.tick_format == "{:.1f}"


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


def test_limits_pair_of_pairs_coerced():
    a = parse_axis_settings(
        {"xlim": [0, 10], "ylim": [5, 15]}, CoordCartesian()
    )
    assert a.limits == ((0.0, 10.0), (5.0, 15.0))


def test_xlim_ylim_properties():
    a = parse_axis_settings(
        {"xlim": [0, 100], "ylim": [20, 80]}, CoordCartesian()
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
        {"axis_arrows": "nope"},  # not a bool
        {"x_reversed": "nope"},  # not a bool
        {"y_reversed": 1},  # not a bool
    ],
)
def test_invalid_axis_raises(axis):
    with pytest.raises(ValueError):
        AxisFormat(**axis)


@pytest.mark.parametrize("coord", [CoordCartesian(), CoordPolar(), TernaryCoord()])
def test_axis_arrows_model_and_parse(coord):
    assert parse_axis_settings({}, coord).show_arrows() is False
    assert parse_axis_settings({"axis_arrows": True}, coord).show_arrows() is True
    assert parse_axis_settings({"axis_arrows": False}, coord).show_arrows() is False
    assert parse_axis_settings({"axis_arrows": None}, coord).show_arrows() is False
    assert AxisFormat(axis_arrows=True).show_arrows() is True
    with pytest.raises(ValueError):
        AxisFormat(axis_arrows="nope")
    with pytest.raises(ValueError):
        parse_axis_settings({"axis_arrows": 1}, coord)


def test_axis_arrow_offset_model_and_parse(coord):
    assert parse_axis_settings({}, coord).axis_arrow_offset is None
    assert parse_axis_settings({"axis_arrow_offset": 1.5}, coord).axis_arrow_offset == 1.5
    assert AxisFormat(axis_arrow_offset=1.5).axis_arrow_offset == 1.5
    with pytest.raises(ValueError):
        AxisFormat(axis_arrow_offset="nope")
    with pytest.raises(ValueError):
        parse_axis_settings({"axis_arrow_offset": "nope"}, coord)


@pytest.mark.parametrize("coord", [CoordCartesian(), CoordPolar(), TernaryCoord()])
def test_axis_reversed_model_and_parse(coord):
    # Defaults: both flags off.
    assert parse_axis_settings({}, coord).x_reversed is False
    assert parse_axis_settings({}, coord).y_reversed is False
    assert AxisFormat().x_reversed is False
    assert AxisFormat().y_reversed is False
    # Round-trip both True and independent per-axis flags.
    a = parse_axis_settings({"x_reversed": True, "y_reversed": True}, coord)
    assert a.x_reversed is True and a.y_reversed is True
    assert AxisFormat(x_reversed=True).x_reversed is True
    assert AxisFormat(y_reversed=True).y_reversed is True
    # None is NOT accepted (plain bools, unlike axis_arrows).
    with pytest.raises(ValueError):
        AxisFormat(x_reversed=None)
    with pytest.raises(ValueError):
        parse_axis_settings({"y_reversed": None}, coord)
    with pytest.raises(ValueError):
        parse_axis_settings({"x_reversed": 1}, coord)


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
        AxisFormat(axis_label_fontsize=-1)
    with pytest.raises(ValueError):
        AxisFormat(fontsize=0)
    with pytest.raises(ValueError):
        AxisFormat(xlabel_fontsize=-5)
    with pytest.raises(ValueError):
        AxisFormat(legend_fontsize="big")
    with pytest.raises(ValueError):
        AxisFormat(suptitle_fontsize=True)


def test_fontsize_resolution_cascade():
    a = AxisFormat()
    assert a.resolve_fontsize("tick") == 5  # built-in default

    gen = AxisFormat(fontsize=9)
    assert gen.resolve_fontsize("tick") == 9  # generic fallback
    assert gen.resolve_fontsize("title") == 9

    specific = AxisFormat(fontsize=9, tick_fontsize=6)
    assert specific.resolve_fontsize("tick") == 6  # per-element wins
    assert specific.resolve_fontsize("title") == 9  # other kinds use generic

    with pytest.raises(ValueError):
        a.resolve_fontsize("bogus")


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


# ---------------------------------------------------------------------------
# Unified frame rendering (WP-B): _draw_frame + drawers on AxisFormat
# ---------------------------------------------------------------------------


def _child_frame_spec(settings):
    """A cartesian child with empty point layers, diamond-stamped."""
    from geofig_engine.core.geom import GeomPoint
    from geofig_engine.core.layer import LayerSpec
    from geofig_engine.core.link import LinkTransform
    from geofig_engine.core.stat import StatIdentity

    empty = pd.DataFrame({"v": []}, dtype=float)
    dia_pct = np.sqrt(3) / 200.0
    dia_scale = (np.sqrt(2) / 400.0, dia_pct * np.sqrt(2) / 2.0)
    return FigureSpec(
        data=empty,
        mappings={},
        settings=settings,
        context={},
        template_name="test",
        coord=CoordCartesian(),
        transform=LinkTransform().rotate(45.0).scale(*dia_scale).translate(0.6, 0.0),
        layers=[
            LayerSpec(
                geom=GeomPoint(),
                stat=StatIdentity(),
                visual_mapping={"x": pd.Series([], dtype=float), "y": pd.Series([], dtype=float)},
                zorder=10,
            )
        ],
    )


def _render_child(settings):
    import matplotlib

    matplotlib.use("Agg")
    from geofig_engine.renderers.matplotlib.renderer import MatplotlibRenderer

    parent = FigureSpec(
        data=pd.DataFrame({"v": []}, dtype=float),
        mappings={},
        settings={"figsize": (10, 8)},
        context={},
        template_name="test",
        children=(_child_frame_spec(settings),),
    )
    fig = MatplotlibRenderer().render(parent)
    ax = fig.axes[0]
    return ax


TICK_TEXT_SETTINGS = {
    "xlim": (0, 100),
    "ylim": (0, 100),
    "grid_step": 20,
    "tick_step": 20,
}


def test_child_frame_renders_via_draw_frame():
    ax = _render_child(TICK_TEXT_SETTINGS)
    texts = [t.get_text() for t in ax.texts]
    # Interior ticks at 20/40/60/80 on both edges.
    assert "20" in texts and "80" in texts


def test_tick_format_changes_tick_labels():
    plain = _render_child(TICK_TEXT_SETTINGS)
    formatted = _render_child({**TICK_TEXT_SETTINGS, "tick_format": ":.1f"})
    plain_texts = {t.get_text() for t in plain.texts}
    form_texts = {t.get_text() for t in formatted.texts}
    assert "20" in plain_texts
    assert "20.0" in form_texts
    assert "20" not in form_texts and "20.0" not in plain_texts


def test_draw_axis_arrow_helper():
    from geofig_engine.renderers.matplotlib.renderer import _draw_axis_arrow

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    identity = np.eye(3)
    _draw_axis_arrow(
        ax,
        identity,
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 0.0),
        label="X",
        label_fs=7,
    )
    _draw_axis_arrow(ax, identity, (0.0, 0.0), (0.0, 1.0), (0.0, 1.0))
    # Two arrows → two annotate artists.
    assert len(ax.texts) >= 2
    assert any(isinstance(t, matplotlib.text.Annotation) for t in ax.texts)
    labels = {t.get_text() for t in ax.texts}
    assert "X" in labels
    plt.close(fig)


def test_secondary_axis_titles_from_flat_keys():
    ax = _render_child(
        {
            "xlim": [0, 100],
            "ylim": [0, 100],
            "secondary_x": {"range": [100, 0], "label": "Anions (%)"},
            "secondary_y": {"range": [100, 0], "label": "Cations (%)"},
        }
    )
    texts = [t.get_text() for t in ax.texts]
    assert "Anions (%)" in texts
    assert "Cations (%)" in texts


def test_cartesian_frame_axis_arrows():
    ax_off = _render_child(
        {
            **TICK_TEXT_SETTINGS,
            "secondary_x": {"range": [100, 0]},
            "secondary_y": {"range": [100, 0]},
        }
    )
    ax_on = _render_child(
        {
            **TICK_TEXT_SETTINGS,
            "axis_arrows": True,
            "secondary_x": {"range": [100, 0]},
            "secondary_y": {"range": [100, 0]},
        }
    )
    count = lambda ax: sum(1 for t in ax.texts if isinstance(t, matplotlib.text.Annotation))
    assert count(ax_off) == 0
    # Primary x, primary y, secondary x, secondary y → four arrows.
    assert count(ax_on) == 4


def test_cartesian_x_and_y_arrows_present():
    # Base frame (no secondary axes): exactly 2 arrows when on, 0 when off.
    ax_off = _render_child(TICK_TEXT_SETTINGS)
    ax_on = _render_child({**TICK_TEXT_SETTINGS, "axis_arrows": True})
    count = lambda ax: sum(1 for t in ax.texts if isinstance(t, matplotlib.text.Annotation))
    assert count(ax_off) == 0
    assert count(ax_on) == 2


def test_cartesian_arrow_offset_default_and_override():
    from geofig_engine.core.coord import CoordCartesian
    from geofig_engine.core.geom import GeomLine
    from geofig_engine.core.layer import LayerSpec
    from geofig_engine.core.stat import StatIdentity

    default_layer = lambda: [
        LayerSpec(
            geom=GeomLine(),
            stat=StatIdentity(),
            visual_mapping={"x": pd.Series([], dtype=float), "y": pd.Series([], dtype=float)},
        )
    ]

    def bottom_arrow_y(settings):
        ax = _render_single_top(settings, coord=CoordCartesian(), layers=default_layer())
        anns = [t for t in ax.texts if isinstance(t, matplotlib.text.Annotation)]
        ys = []
        for a in anns:
            st = np.asarray(a.xyann, dtype=float)
            en = np.asarray(a.xy, dtype=float)
            # Bottom-edge arrow: horizontal (equal y) and below the box (y<0).
            if abs(en[1] - st[1]) < 1e-9 and en[1] < 0:
                ys.append(float(en[1]))
        assert len(ys) == 1, f"expected one bottom arrow, got {ys}"
        return ys[0]

    base = {"xlim": (0, 100), "ylim": (0, 100), "tick_step": 20, "axis_arrows": True}
    default_y = bottom_arrow_y(base)
    explicit_y = bottom_arrow_y({**base, "axis_arrow_offset": 20.0})
    # Default multiplier (2*d = 2*5) places the arrow beyond the tick-label
    # strip (tick offset d = 100/20 = 5), and an explicit offset overrides it.
    assert default_y == -10.0
    assert explicit_y == -20.0
    assert explicit_y < default_y


def test_cartesian_arrow_points_to_ascending_when_limits_descending():
    import matplotlib.pyplot as plt

    from geofig_engine.core.coord import CoordCartesian
    from geofig_engine.core.geom import GeomPoint
    from geofig_engine.core.layer import LayerSpec
    from geofig_engine.core.link import LinkTransform
    from geofig_engine.core.stat import StatIdentity
    from geofig_engine.renderers.matplotlib.renderer import MatplotlibRenderer

    empty = pd.DataFrame({"v": []}, dtype=float)
    # x declared descending (100 -> 0): arrow must still point toward the
    # higher numeric value (from low x to high x in local space).
    child = FigureSpec(
        data=empty,
        mappings={},
        settings={"xlim": (10, 0), "ylim": (0, 10), "grid_step": 2, "tick_step": 2, "axis_arrows": True},
        context={},
        template_name="test",
        coord=CoordCartesian(),
        transform=LinkTransform(),
        layers=[
            LayerSpec(
                geom=GeomPoint(),
                stat=StatIdentity(),
                visual_mapping={"x": pd.Series([], dtype=float), "y": pd.Series([], dtype=float)},
                zorder=10,
            )
        ],
    )
    parent = FigureSpec(
        data=empty,
        mappings={},
        settings={"figsize": (10, 8)},
        context={},
        template_name="test",
        children=(child,),
    )
    ax = MatplotlibRenderer().render(parent).axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.figure.canvas.draw()
    x_coords = []
    for a in (t for t in ax.texts if isinstance(t, matplotlib.text.Annotation)):
        pad = a.arrow_patch
        dc = ax.transData.inverted().transform(
            pad.get_transform().transform(pad.get_path().vertices)
        )
        xs = dc[:, 0]
        # Focus on the bottom-edge x axis arrow: its path is the one whose
        # y-extent stays below the frame (near y=0) but spans most of x.
        if xs.max() - xs.min() > 5:
            x_coords.append((xs.min(), xs.max()))
    assert x_coords, "no x-axis arrow found"
    assert all(lo < hi for lo, hi in x_coords)


def test_cartesian_normalizes_descending_limits():
    # Declaring descending limits (100 -> 0) must not blow away the grid/ticks
    # (an empty np.arange) nor drive the secondary titles to the lower edges.
    ax = _render_single_top(
        {
            "xlim": (100, 0),
            "ylim": (100, 0),
            "grid_step": 20,
            "tick_step": 20,
            "secondary_x": {"range": [0, 100], "label": "Anions (%)"},
            "secondary_y": {"range": [0, 100], "label": "Cations (%)"},
        }
    )
    ax.figure.canvas.draw()
    grid_lines = sum(1 for l in ax.lines if l.get_linestyle() != "-")
    assert grid_lines > 0
    ticks = [t for t in ax.texts if t.get_text().isdigit()]
    assert len(ticks) > 0
    positions = {
        t.get_text(): np.asarray(t.get_position())
        for t in ax.texts if t.get_text() in ("Anions (%)", "Cations (%)")
    }
    assert "Anions (%)" in positions and "Cations (%)" in positions
    # Anions title above the frame center; Cations title right of it.
    assert positions["Anions (%)"][1] > 50.0
    assert positions["Cations (%)"][0] > 50.0


def test_cartesian_x_arrow_and_labels_reverse_together():
    # Arrows always point toward increasing data: reversing the axis flips the
    # arrowhead AND the bottom-edge tick labels together.
    def bottom_arrow_head_tail(revx):
        settings = {
            "xlim": (0, 100), "ylim": (0, 100),
            "grid_step": 20, "tick_step": 20, "axis_arrows": True,
        }
        if revx:
            settings["x_reversed"] = True
        ax = _render_single_top(settings)
        ax.figure.canvas.draw()
        for t in ax.texts:
            if isinstance(t, matplotlib.text.Annotation):
                end = np.asarray(t.xy)
                start = np.asarray(t.xyann)
                if abs(end[1] - start[1]) < 1e-9 and end[1] < 0:
                    return start[0], end[0]
        return None

    def bottom_ticks(revx):
        settings = {"xlim": (0, 100), "ylim": (0, 100), "grid_step": 20, "tick_step": 20}
        if revx:
            settings["x_reversed"] = True
        ax = _render_single_top(settings)
        ax.figure.canvas.draw()
        out = []
        for t in ax.texts:
            if t.get_text().isdigit() and t.get_position()[1] < 0:
                out.append((round(t.get_position()[0]), t.get_text()))
        out.sort()
        return [lbl for _, lbl in out]

    # Non-reversed: arrowhead at high x; labels ascend 20..80.
    s0, e0 = bottom_arrow_head_tail(False)
    assert e0 > s0
    assert bottom_ticks(False) == ["20", "40", "60", "80"]
    # Reversed: arrowhead flips to low x; labels descend 80..20.
    s1, e1 = bottom_arrow_head_tail(True)
    assert s1 > e1
    assert bottom_ticks(True) == ["80", "60", "40", "20"]


# ---------------------------------------------------------------------------
# Custom polar frame (WP-C): _draw_polar_frame on AxisFormat
# ---------------------------------------------------------------------------


def _polar_spec(settings):
    from geofig_engine.core.geom import GeomLine
    from geofig_engine.core.layer import LayerSpec
    from geofig_engine.core.stat import StatIdentity

    return FigureSpec(
        data=pd.DataFrame({"v": [1.0, 2.0, 3.0]}),
        mappings={},
        settings=settings,
        context={},
        template_name="test",
        coord=CoordPolar(),
        layers=[
            LayerSpec(
                geom=GeomLine(),
                stat=StatIdentity(),
                visual_mapping={
                    "x": pd.Series([0.0, np.pi / 2, np.pi]),
                    "y": pd.Series([1.0, 2.0, 1.0]),
                    "label": pd.Series(["A", "B", "C"]),
                },
            )
        ],
    )


def _frame_polar_axes():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    return fig, ax


def test_polar_frame_hides_spine():
    from geofig_engine.renderers.matplotlib.renderer import MatplotlibRenderer

    settings = {"hide_spine": True, "grid": False}
    fig, ax = _frame_polar_axes()
    renderer = MatplotlibRenderer()
    renderer._draw_frame(ax, _polar_spec(settings))
    assert not ax.spines["polar"].get_visible()
    fig.clf()


def test_polar_frame_polar_tick_labels_mapping():
    from geofig_engine.renderers.matplotlib.renderer import MatplotlibRenderer

    fig, ax = _frame_polar_axes()
    renderer = MatplotlibRenderer()
    renderer._draw_frame(
        ax,
        _polar_spec(
            {"polar_tick_labels": True}
        ),
    )
    labels = [t.get_text() for t in ax.get_xticklabels()]
    assert any(lbl == "A" for lbl in labels)
    assert any(lbl == "C" for lbl in labels)
    fig.clf()


def test_polar_tick_fontsize_applies_resolved_tick():
    from geofig_engine.renderers.matplotlib.renderer import MatplotlibRenderer

    renderer = MatplotlibRenderer()

    fig, ax = _frame_polar_axes()
    renderer._draw_frame(ax, _polar_spec({"polar_tick_labels": True}))
    assert ax.xaxis.get_ticklabels()[0].get_fontsize() == 5.0  # built-in default
    fig.clf()

    fig, ax = _frame_polar_axes()
    renderer._draw_frame(
        ax,
        _polar_spec({"polar_tick_labels": True, "tick_fontsize": 12}),
    )
    assert ax.xaxis.get_ticklabels()[0].get_fontsize() == 12.0  # per-element wins
    fig.clf()

    fig, ax = _frame_polar_axes()
    renderer._draw_frame(
        ax,
        _polar_spec({"polar_tick_labels": True, "fontsize": 11}),
    )
    assert ax.xaxis.get_ticklabels()[0].get_fontsize() == 11.0  # generic fallback
    fig.clf()


def test_polar_frame_hide_radial_ticks():
    from geofig_engine.renderers.matplotlib.renderer import MatplotlibRenderer

    fig, ax = _frame_polar_axes()
    renderer = MatplotlibRenderer()
    renderer._draw_frame(
        ax,
        _polar_spec(
            {"hide_radial_ticks": True}
        ),
    )
    assert ax.get_yticks().size == 0
    fig.clf()


def test_polar_grid_toggled():
    from geofig_engine.renderers.matplotlib.renderer import MatplotlibRenderer

    renderer = MatplotlibRenderer()

    fig_g, ax_g = _frame_polar_axes()
    renderer._draw_frame(ax_g, _polar_spec({"grid": False}))
    gridlines_false = list(ax_g.yaxis.get_gridlines())
    fig_g.clf()

    fig_t, ax_t = _frame_polar_axes()
    renderer._draw_frame(ax_t, _polar_spec({"grid": True}))
    gridlines_true = list(ax_t.yaxis.get_gridlines())
    fig_t.clf()

    assert any(
        not gl.get_visible() for gl in gridlines_false
    ) or not gridlines_false
    assert gridlines_true and all(gl.get_visible() for gl in gridlines_true)


def test_polar_radial_arrow_opt_in_points_outward():
    from geofig_engine.renderers.matplotlib.renderer import MatplotlibRenderer

    def render(settings):
        fig, ax = _frame_polar_axes()
        MatplotlibRenderer()._draw_frame(ax, _polar_spec(settings))
        ax.set_ylim(0, 1)
        ax.figure.canvas.draw()
        return fig, ax

    count = lambda ax: sum(1 for t in ax.texts if isinstance(t, matplotlib.text.Annotation))

    fig_off, ax_off = render({})
    assert count(ax_off) == 0
    fig_off.clf()

    fig_on, ax_on = render({"axis_arrows": True})
    assert count(ax_on) == 1
    ann = next(t for t in ax_on.texts if isinstance(t, matplotlib.text.Annotation))
    dc = ax_on.transData.inverted().transform(
        ann.arrow_patch.get_transform().transform(ann.arrow_patch.get_path().vertices)
    )
    # Filter to stem points near the north ray (theta ~ pi/2) within the radial
    # plot, ignoring arrowhead wings and clipping artifacts. The remaining
    # points span increasing radius r -> outward along the ray.
    mask = (np.abs(dc[:, 0] - np.pi / 2) < 0.5) & (dc[:, 1] <= 1.0)
    stem = dc[mask]
    assert stem.shape[0] >= 2
    assert stem[:, 1].max() > stem[:, 1].min()
    fig_on.clf()


def test_polar_radial_arrow_independent_of_hide_toggles():
    from geofig_engine.renderers.matplotlib.renderer import MatplotlibRenderer

    renderer = MatplotlibRenderer()
    fig, ax = _frame_polar_axes()
    renderer._draw_frame(
        ax,
        _polar_spec(
            {
                "axis_arrows": True,
                "hide_spine": True,
                "hide_radial_ticks": True,
            }
        ),
    )
    count = lambda ax: sum(1 for t in ax.texts if isinstance(t, matplotlib.text.Annotation))
    # The arrow is drawn regardless of the polar hide toggles.
    assert count(ax) == 1
    assert not ax.spines["polar"].get_visible()
    assert ax.get_yticks().size == 0
    fig.clf()


# ---------------------------------------------------------------------------
# Top-level unified single path (WP-D): render a single framed spec like a child
# ---------------------------------------------------------------------------


def _render_single_top(settings, coord=CoordCartesian(), layers=None):
    """Render a top-level spec directly (through the unified framed path)."""
    from geofig_engine.core.geom import GeomLine
    from geofig_engine.core.layer import LayerSpec
    from geofig_engine.core.stat import StatIdentity

    if layers is None:
        layers = [
            LayerSpec(
                geom=GeomLine(),
                stat=StatIdentity(),
                visual_mapping={
                    "x": pd.Series([0.0, 50.0, 100.0]),
                    "y": pd.Series([0.0, 50.0, 100.0]),
                },
            )
        ]
    import matplotlib

    matplotlib.use("Agg")
    from geofig_engine.renderers.matplotlib.renderer import MatplotlibRenderer

    spec = FigureSpec(
        data=pd.DataFrame({"v": [0.0, 1.0, 2.0]}),
        mappings={},
        settings={"figsize": (8, 8), **settings},
        context={},
        template_name="test",
        coord=coord,
        layers=layers,
    )
    fig = MatplotlibRenderer().render(spec)
    ax = fig.axes[0]
    return ax


def test_top_level_cartesian_framed_renders_via_draw_frame():
    ax = _render_single_top(
        {"xlim": (0, 100), "ylim": (0, 100), "grid_step": 20, "tick_step": 20}
    )
    texts = [t.get_text() for t in ax.texts]
    assert "20" in texts and "80" in texts
    assert ax.get_aspect() == 1
    assert len(ax.lines) > 1


def test_top_level_cartesian_flat_equals_child():
    flat = _render_single_top({"xlim": (0, 100), "ylim": (0, 100), "grid_step": 20, "tick_step": 20})
    child = _render_child({"xlim": (0, 100), "ylim": (0, 100), "grid_step": 20, "tick_step": 20})
    assert sorted(t.get_text() for t in flat.texts) == sorted(
        t.get_text() for t in child.texts
    )
    # Top-level adds its data line on top of the same 9 frame lines the child has.
    assert len(flat.lines) == len(child.lines) + 1


def test_top_level_ternary_renders_triangle():
    from geofig_engine.core.geom import GeomLine
    from geofig_engine.core.layer import LayerSpec
    from geofig_engine.core.stat import StatIdentity

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
    ax = _render_single_top({}, coord=coord, layers=[layer])
    # Ternary triangle produces grid lines + tick labels + ion labels (arrows
    # are opt-in via axis_arrows, off here).
    assert len(ax.lines) > 1
    texts = [t.get_text() for t in ax.texts]
    assert any(t in ("20", "40", "60", "80") for t in texts)
    assert ax.get_aspect() == 1


def test_ternary_ion_labels_are_standalone_and_arrows_opt_in():
    from geofig_engine.core.geom import GeomLine
    from geofig_engine.core.layer import LayerSpec
    from geofig_engine.core.stat import StatIdentity

    def render(settings):
        coord = TernaryCoord(channels=("Mg", "Ca", "Na+K"), handedness="left")
        layer = LayerSpec(
            geom=GeomLine(),
            stat=StatIdentity(),
            visual_mapping={
                "Mg": pd.Series([0.5], dtype=float),
                "Ca": pd.Series([0.3], dtype=float),
                "Na+K": pd.Series([0.2], dtype=float),
            },
        )
        return _render_single_top(settings, coord=coord, layers=[layer])

    ax_off = render({})
    ax_on = render({"axis_arrows": True})

    count = lambda ax: sum(1 for t in ax.texts if isinstance(t, matplotlib.text.Annotation))
    labels = lambda ax: [t.get_text() for t in ax.texts]

    # Ion labels are plain text, always present, independent of arrows.
    for ax in (ax_off, ax_on):
        text_labels = labels(ax)
        assert "Mg" in text_labels and "Ca" in text_labels and "Na+K" in text_labels
    assert count(ax_off) == 0
    # Three edges -> three arrows when opted in.
    assert count(ax_on) == 3


def test_ternary_arrows_point_toward_ascending_value():
    from geofig_engine.core.geom import GeomLine
    from geofig_engine.core.layer import LayerSpec
    from geofig_engine.core.stat import StatIdentity

    coord = TernaryCoord(channels=("Mg", "Ca", "Na+K"), handedness="left")
    layer = LayerSpec(
        geom=GeomLine(),
        stat=StatIdentity(),
        visual_mapping={
            "Mg": pd.Series([0.5], dtype=float),
            "Ca": pd.Series([0.3], dtype=float),
            "Na+K": pd.Series([0.2], dtype=float),
        },
    )
    ax = _render_single_top({"axis_arrows": True}, coord=coord, layers=[layer])
    anns = [t for t in ax.texts if isinstance(t, matplotlib.text.Annotation)]
    assert len(anns) == 3
    # The annotate head (xy) is the high-value end; the tail (xyann) the low
    # end. Triangle vertices: base-left (0,0), base-right (1,0), apex (0.5,h).
    # For a LEFT-handed (cation) triangle the reversal flags are
    # rev_bottom=True, rev_left=False, rev_right=True, so the increasing
    # (100%) corner is:
    #   - bottom: base-left -> arrow points LEFT (decreasing x),
    #   - left:   apex -> arrow rises toward the apex,
    #   - right:  base-right -> arrow falls toward the base-right (y only).
    horizontal = 0
    rising = 0
    falling = 0
    for a in anns:
        head = np.asarray(a.xy, dtype=float)
        tail = np.asarray(a.xyann, dtype=float)
        delta = head - tail
        if abs(delta[1]) < 1e-9:
            horizontal += 1
            assert delta[0] < 0  # bottom edge points toward base-left (increasing x reversed)
        if delta[1] > 1e-9:
            rising += 1  # left edge rises toward the apex
        if delta[1] < -1e-9:
            falling += 1  # right edge falls toward the base-right
    assert horizontal == 1  # exactly the bottom (flattened to the base) edge
    assert rising == 1  # only the left edge rises toward the apex
    assert falling == 1  # the right edge falls toward its 100% corner


def test_ternary_arrows_point_toward_ascending_value_right_handed():
    from geofig_engine.core.geom import GeomLine
    from geofig_engine.core.layer import LayerSpec
    from geofig_engine.core.stat import StatIdentity

    coord = TernaryCoord(channels=("SO4", "Cl", "HCO3"), handedness="right")
    layer = LayerSpec(
        geom=GeomLine(),
        stat=StatIdentity(),
        visual_mapping={
            "SO4": pd.Series([0.5], dtype=float),
            "Cl": pd.Series([0.3], dtype=float),
            "HCO3": pd.Series([0.2], dtype=float),
        },
    )
    ax = _render_single_top({"axis_arrows": True}, coord=coord, layers=[layer])
    anns = [t for t in ax.texts if isinstance(t, matplotlib.text.Annotation)]
    assert len(anns) == 3
    # Both cation and anion triangles read with the same (non-mirrored) value
    # pattern, so the right-handed triangle shares the left-handed reversals
    # (rev_bottom=True, rev_left=False, rev_right=True). The increasing (100%)
    # corner per edge:
    #   - bottom: base-left -> arrow points LEFT (decreasing x),
    #   - left:   apex -> arrow rises toward the apex,
    #   - right:  base-right -> arrow falls toward the base-right.
    horizontal = 0
    rising = 0
    falling = 0
    for a in anns:
        head = np.asarray(a.xy, dtype=float)
        tail = np.asarray(a.xyann, dtype=float)
        delta = head - tail
        if abs(delta[1]) < 1e-9:
            horizontal += 1
            assert delta[0] < 0  # bottom edge points toward base-left (increasing x reversed)
        if delta[1] > 1e-9:
            rising += 1  # left edge rises toward the apex
        if delta[1] < -1e-9:
            falling += 1  # right edge falls toward the base-right
    assert horizontal == 1  # exactly the bottom (flattened to the base) edge
    assert rising == 1  # only the left edge rises toward the apex
    assert falling == 1  # the right edge falls toward its 100% corner


def test_plain_single_stays_native_axes():
    # A plain cartesian chart with no explicit limits keeps native matplotlib
    # axes (not the custom off-axis frame).
    from geofig_engine.core.geom import GeomLine
    from geofig_engine.core.layer import LayerSpec
    from geofig_engine.core.stat import StatIdentity

    layers = [
        LayerSpec(
            geom=GeomLine(),
            stat=StatIdentity(),
            visual_mapping={
                "x": pd.Series([0.0, 1.0, 2.0]),
                "y": pd.Series([0.0, 1.0, 4.0]),
            },
        )
    ]
    ax = _render_single_top({"xlabel": "X AXIS"}, layers=layers)
    assert ax.get_xlabel() == "X AXIS"
    assert ax.axison is True


def test_native_title_xlabel_ylabel_use_resolved_fontsize():
    # Defaults: title 7, xlabel 10, ylabel 10.
    ax = _render_single_top({"title": "T", "xlabel": "X", "ylabel": "Y"})
    assert ax.title.get_fontsize() == 7.0
    assert ax.xaxis.label.get_fontsize() == 10.0
    assert ax.yaxis.label.get_fontsize() == 10.0


def test_native_fontsize_knobs_override_defaults():
    ax = _render_single_top(
        {
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "title_fontsize": 8,
            "xlabel_fontsize": 12,
            "ylabel_fontsize": 11,
        }
    )
    assert ax.title.get_fontsize() == 8.0
    assert ax.xaxis.label.get_fontsize() == 12.0
    assert ax.yaxis.label.get_fontsize() == 11.0


def test_native_title_xlabel_ylabel_use_generic_fontsize():
    ax = _render_single_top(
        {"title": "T", "xlabel": "X", "ylabel": "Y", "fontsize": 9}
    )
    assert ax.title.get_fontsize() == 9.0
    assert ax.xaxis.label.get_fontsize() == 9.0
    assert ax.yaxis.label.get_fontsize() == 9.0

def test_ternary_frame_title_uses_resolved_title():
    # Ternary drawn frame's title text (drawn on the axes) uses resolve_fontsize("title").
    ternary_layers = [
        LayerSpec(
            geom=GeomLine(),
            stat=StatIdentity(),
            visual_mapping={
                "a": pd.Series([0.0, 0.5, 1.0]),
                "b": pd.Series([0.0, 0.433, 0.0]),
                "c": pd.Series([1.0, 0.067, 0.0]),
            },
        )
    ]
    ax = _render_single_top(
        {"title": "TRI TITLE"}, coord=TernaryCoord(), layers=ternary_layers
    )
    sized = [
        t.get_fontsize()
        for t in ax.texts
        if t.get_text() == "TRI TITLE"
    ]
    assert sized == [7.0]  # built-in default

    ax = _render_single_top(
        {"title": "TRI TITLE", "title_fontsize": 13},
        coord=TernaryCoord(), layers=ternary_layers,
    )
    sized = [
        t.get_fontsize()
        for t in ax.texts
        if t.get_text() == "TRI TITLE"
    ]
    assert sized == [13.0]

    ax = _render_single_top(
        {"title": "TRI TITLE", "fontsize": 14},
        coord=TernaryCoord(), layers=ternary_layers,
    )
    sized = [
        t.get_fontsize()
        for t in ax.texts
        if t.get_text() == "TRI TITLE"
    ]
    assert sized == [14.0]  # generic fallback

def test_suptitle_uses_resolved_fontsize():
    import matplotlib
    matplotlib.use("Agg")
    from geofig_engine.renderers.matplotlib.renderer import MatplotlibRenderer

    def render(settings):
        spec = FigureSpec(
            data=pd.DataFrame({"v": [0.0, 1.0, 2.0]}),
            mappings={},
            settings={"figsize": (8, 8), "xlim": (0, 100), "ylim": (0, 100), **settings},
            context={},
            template_name="test",
            layers=[
                LayerSpec(
                    geom=GeomLine(),
                    stat=StatIdentity(),
                    visual_mapping={
                        "x": pd.Series([0.0, 1.0]),
                        "y": pd.Series([0.0, 1.0]),
                    },
                ),
            ],
        )
        return MatplotlibRenderer().render(spec)

    fig = render({"title": "T"})
    assert fig._suptitle.get_text() == "T"
    assert fig._suptitle.get_fontsize() == 14.0

    fig = render({"title": "T", "suptitle_fontsize": 18})
    assert fig._suptitle.get_fontsize() == 18.0

    fig = render({"title": "T", "fontsize": 20})
    assert fig._suptitle.get_fontsize() == 20.0

def test_facet_panel_titles_use_facet_title_fontsize():
    fig = _render_facet({"xlabel": "X"})
    # FacetWrap panels each get a "g=<v>" title using facet_title (default 10).
    for ax in fig.axes:
        assert ax.title.get_fontsize() == 10.0
        assert ax.get_title() in ("g=A", "g=B")


def test_facet_panel_titles_override_facet_title_fontsize():
    fig = _render_facet({"xlabel": "X", "facet_title_fontsize": 13})
    for ax in fig.axes:
        assert ax.title.get_fontsize() == 13.0


# ---------------------------------------------------------------------------
# Facet panels consume AxisFormat (WP-E): per-panel native formatting
# ---------------------------------------------------------------------------


def _render_facet(settings, scales="fixed"):
    from geofig_engine.core.facet import FacetWrap
    from geofig_engine.core.geom import GeomPoint
    from geofig_engine.core.layer import LayerSpec
    from geofig_engine.core.stat import StatIdentity

    import matplotlib

    matplotlib.use("Agg")
    from geofig_engine.renderers.matplotlib.renderer import MatplotlibRenderer

    data = pd.DataFrame({"x": [1, 2, 3, 4], "y": [5, 6, 7, 8], "g": ["A", "A", "B", "B"]})
    spec = FigureSpec(
        data=data,
        mappings={},
        settings={"figsize": (10, 6), **settings},
        context={},
        template_name="test",
        facet=FacetWrap(by="g", scales=scales),
        layers=[
            LayerSpec(
                geom=GeomPoint(),
                stat=StatIdentity(),
                visual_mapping={"x": data["x"], "y": data["y"]},
            )
        ],
    )
    fig = MatplotlibRenderer().render(spec)
    return fig


def test_facet_panels_formatted_from_flat_keys():
    fig = _render_facet(
        {"xlabel": "X-LAB", "ylabel": "Y-LAB", "grid": True}
    )
    assert len(fig.axes) == 2
    for ax in fig.axes:
        assert ax.get_xlabel() == "X-LAB"
        assert ax.get_ylabel() == "Y-LAB"
        assert any(gl.get_visible() for gl in ax.get_xgridlines())


def test_facet_flat_limits():
    fig = _render_facet({"xlim": (0, 10), "ylim": (0, 10)}, scales="free")
    for ax in fig.axes:
        assert ax.get_xlim() == (0.0, 10.0)
        assert ax.get_ylim() == (0.0, 10.0)


def test_facet_layout_and_sharing_preserved():
    fig = _render_facet({"xlabel": "X-LAB"})
    # Same two panels, x shared (fixed scales), each carries the AxisFormat label.
    assert len(fig.axes) == 2
    for ax in fig.axes:
        assert ax.get_shared_x_axes().joined(ax, fig.axes[0])
        assert ax.get_xlabel() == "X-LAB"


# ---------------------------------------------------------------------------
# Construction-time axis validation (WP-F): validate_figure_spec on settings
# ---------------------------------------------------------------------------


def _construction_spec(settings):
    from geofig_engine.core.geom import GeomPoint
    from geofig_engine.core.layer import LayerSpec
    from geofig_engine.core.stat import StatIdentity

    return FigureSpec(
        data=pd.DataFrame({"x": [1.0], "y": [2.0]}),
        mappings={},
        settings=settings,
        context={},
        template_name="test",
        coord=CoordCartesian(),
        layers=[
            LayerSpec(
                geom=GeomPoint(),
                stat=StatIdentity(),
                visual_mapping={"x": pd.Series([1.0]), "y": pd.Series([2.0])},
            )
        ],
    )


@pytest.mark.parametrize(
    "bad_settings",
    [
        {"xlim": [0, 100, 200], "ylim": [0, 100]},  # xlim not a pair
        {"xlim": [0, 100], "ylim": [0, 100, 200]},  # ylim not a pair
        {"xlim": [0, "a"], "ylim": [0, 1]},  # non-numeric
        {"xlim": "oops", "ylim": [0, 1]},  # not a sequence
    ],
)
def test_axis_limits_validation_at_construction(bad_settings):
    with pytest.raises(ValueError):
        _construction_spec(bad_settings)


def test_bad_label_policy_raises_at_construction():
    with pytest.raises(ValueError):
        _construction_spec({"label_policy": "slanted"})


def test_nonpositive_tick_step_raises_at_construction():
    with pytest.raises(ValueError):
        _construction_spec({"tick_step": 0})
    with pytest.raises(ValueError):
        _construction_spec({"grid_step": -3})


def test_bad_tick_format_raises_at_construction():
    with pytest.raises(ValueError):
        _construction_spec({"tick_format": 123})


def test_valid_axis_constructs_cleanly():
    spec = _construction_spec(
        {"xlim": (0, 100), "ylim": (0, 100), "grid_step": 20, "tick_step": 20}
    )
    assert spec is not None


def test_flat_keys_construct_cleanly():
    spec = _construction_spec(
        {"xlim": (0, 100), "ylim": (0, 100), "grid_step": 20, "tick_step": 20}
    )
    assert spec is not None


# ---------------------------------------------------------------------------
# Serialization round-trips for AxisFormat settings (WP-G): figsize + xlim/ylim
# ---------------------------------------------------------------------------


def _roundtrip_settings(settings):
    from geofig_engine.serialize.converters import spec_from_json, spec_to_json

    spec = _construction_spec(settings)
    restored = spec_from_json(spec_to_json(spec))
    return restored.settings


def test_roundtrip_preserves_limits_as_flat_tuples():
    s = _roundtrip_settings(
        {"xlim": (0, 100), "ylim": (0, 100), "grid_step": 20}
    )
    assert s["xlim"] == (0, 100)
    assert isinstance(s["xlim"], tuple)
    assert s["ylim"] == (0, 100)


def test_roundtrip_preserves_figsize_as_tuple():
    s = _roundtrip_settings({"figsize": (8, 8)})
    assert s["figsize"] == (8, 8)
    assert isinstance(s["figsize"], tuple)


def test_roundtrip_preserves_existing_tuple_keys():
    s = _roundtrip_settings(
        {
            "xlim": (0, 5),
            "ylim": (0, 9),
            "secondary_x": {"range": [100, 0]},
        }
    )
    assert s["xlim"] == (0, 5)
    assert s["ylim"] == (0, 9)
    assert s["secondary_x"]["range"] == (100, 0)


def test_roundtrip_unchanged_without_axis_or_figsize():
    s = _roundtrip_settings({"title": "T", "grid": True})
    assert s == {"title": "T", "grid": True}
