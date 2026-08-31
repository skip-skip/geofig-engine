"""
Tests for the AxisFormat model and parse_axis_settings (Phase 14.54 WP-A).

Covers the shared declarative axis-formatting model consumed by the unified
frame pipeline: flat top-level axis keys, appearance knobs, and validation.
"""

import numpy as np
import pandas as pd
import pytest

from geofig_engine.core.axis import AxisFormat, parse_axis_settings, VALID_LABEL_POLICIES
from geofig_engine.core.coord import CoordCartesian, CoordPolar, TernaryCoord
from geofig_engine.core.spec import FigureSpec


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
    # Ternary triangle produces grid lines + tick labels + ion arrows
    assert len(ax.lines) > 1
    texts = [t.get_text() for t in ax.texts]
    assert any(t in ("20", "40", "60", "80") for t in texts)
    assert ax.get_aspect() == 1


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
