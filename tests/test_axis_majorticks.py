"""Parametrized majortick geometry tests across all four frame edges.

Proves that ``majortick_offset`` places the interior/exterior tips per the
documented formulas on bottom, top, left, and right edges, using offsets
{0, 0.5, 1} with minimal framed cartesian specs (no template dependencies).
"""

import numpy as np
import pandas as pd
import pytest

import matplotlib

matplotlib.use("Agg")

from geofig_engine.core.coord import CoordCartesian
from geofig_engine.core.geom import GeomLine
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.spec import FigureSpec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.renderers import MatplotlibRenderer

L = 0.2
XLO, XHI, YLO, YHI = 0.0, 4.0, 0.0, 4.0
POSITIONS = (1, 2, 3)


def _render(settings):
    spec = FigureSpec(
        data=pd.DataFrame({"v": [0.0, 1.0, 2.0]}),
        mappings={},
        settings={"figsize": (8, 8), **settings},
        context={},
        template_name="test",
        coord=CoordCartesian(),
        layers=[
            LayerSpec(
                geom=GeomLine(),
                stat=StatIdentity(),
                visual_mapping={
                    "x": pd.Series([0.0, 50.0, 100.0]),
                    "y": pd.Series([0.0, 50.0, 100.0]),
                },
            )
        ],
    )
    renderer = MatplotlibRenderer()
    assert renderer.supports(spec) is True
    return renderer.render(spec).axes[0]


def _nubs_for_edge(ax, edge, length=L):
    """Map each tick's along-edge coordinate to its (interior, exterior) tip.

    Majortick segments are axis-aligned 2-point lines of exact length *length*
    (in practice ``L``, but overridden to test per-secondary values).  A
    segment belongs to an edge when its extent spans that edge's coordinate
    (true for every offset in [0, 1]), which also disambiguates overlapping
    top/bottom and left/right keys.
    """
    anchor = {"bottom": YLO, "top": YHI, "left": XLO, "right": XHI}[edge]
    nubs = {}
    for line in ax.lines:
        xs = np.asarray(line.get_xdata())
        ys = np.asarray(line.get_ydata())
        if len(xs) != 2:
            continue
        if edge in ("bottom", "top"):
            if not (np.allclose(xs, xs[0]) and abs(ys[1] - ys[0]) == pytest.approx(length)):
                continue
            if not min(ys) <= anchor <= max(ys):
                continue
            nubs[round(float(xs[0]), 6)] = (float(ys[0]), float(ys[1]))
        else:
            if not (np.allclose(ys, ys[0]) and abs(xs[1] - xs[0]) == pytest.approx(length)):
                continue
            if not min(xs) <= anchor <= max(xs):
                continue
            nubs[round(float(ys[0]), 6)] = (float(xs[0]), float(xs[1]))
    return nubs


# interior tip = toward frame center; exterior tip = away from frame center.
#   bottom: interior y = ylo + offset*L       exterior y = ylo - (1-offset)*L
#   top:    interior y = yhi - offset*L       exterior y = yhi + (1-offset)*L
#   left:   interior x = xlo + offset*L       exterior x = xlo - (1-offset)*L
#   right:  interior x = xhi - offset*L       exterior x = xhi + (1-offset)*L
_EXPECTED = {
    ("bottom", "x"): lambda o: (YLO + o * L, YLO - (1 - o) * L),
    ("top", "x"): lambda o: (YHI - o * L, YHI + (1 - o) * L),
    ("left", "y"): lambda o: (XLO + o * L, XLO - (1 - o) * L),
    ("right", "y"): lambda o: (XHI - o * L, XHI + (1 - o) * L),
}


@pytest.mark.parametrize(
    "edge,offset",
    [
        ("bottom", 0), ("bottom", 0.5), ("bottom", 1),
        ("top", 0), ("top", 0.5), ("top", 1),
        ("left", 0), ("left", 0.5), ("left", 1),
        ("right", 0), ("right", 0.5), ("right", 1),
    ],
)
def test_majortick_offset_semantics_per_edge(edge, offset):
    ax = _render(
        {
            "xlim": (XLO, XHI),
            "ylim": (YLO, YHI),
            "tick_step": 1,
            "majortick_length": L,
            "majortick_offset": offset,
            "grid": False,
            "secondary_x": {"range": (XLO, XHI), "tick_step": 1},
            "secondary_y": {"range": (YLO, YHI), "tick_step": 1},
        }
    )
    nubs = _nubs_for_edge(ax, edge)
    along = "x" if edge in ("bottom", "top") else "y"
    expected = _EXPECTED[(edge, along)](offset)
    for pos in POSITIONS:
        interior, exterior = nubs[pos]
        assert interior == pytest.approx(expected[0], abs=1e-9), (
            f"{edge} interior tip at {along}={pos} for offset {offset}"
        )
        assert exterior == pytest.approx(expected[1], abs=1e-9), (
            f"{edge} exterior tip at {along}={pos} for offset {offset}"
        )


def test_no_majorticks_without_majortick_length():
    ax = _render(
        {
            "xlim": (XLO, XHI),
            "ylim": (YLO, YHI),
            "tick_step": 1,
            "grid": False,
        }
    )
    for edge in ("bottom", "top", "left", "right"):
        assert _nubs_for_edge(ax, edge) == {}


def test_named_edges_tick_at_all_label_positions_including_frame_edges():
    ax = _render(
        {
            "xlim": (XLO, XHI),
            "ylim": (YLO, YHI),
            "majortick_length": L,
            "majortick_offset": 0,
            "grid": False,
            "y_tick_labels": {0: "a", 1: "b", 2: "c", 3: "d", 4: "e"},
            "secondary_y": {
                "range": (YLO, YHI),
                "tick_labels": {0: "A", 2: "C", 4: "E"},
            },
        }
    )
    assert sorted(_nubs_for_edge(ax, "left")) == [0.0, 1.0, 2.0, 3.0, 4.0]
    # Frame edges y = ylo and y = yhi get ticks too.
    assert sorted(_nubs_for_edge(ax, "right")) == [0.0, 2.0, 4.0]


def test_top_edge_inherits_frame_majortick_length():
    ax = _render(
        {
            "xlim": (XLO, XHI),
            "ylim": (YLO, YHI),
            "tick_step": 1,
            "majortick_length": L,
            "majortick_offset": 0,
            "grid": False,
            "secondary_x": {"range": (XLO, XHI), "tick_step": 1},
        }
    )
    top = _nubs_for_edge(ax, "top")
    assert sorted(top) == [1.0, 2.0, 3.0]
    assert top[1] == pytest.approx((YHI, YHI + L))


def test_secondary_override_beats_frame_majortick_length():
    ax = _render(
        {
            "xlim": (XLO, XHI),
            "ylim": (YLO, YHI),
            "tick_step": 1,
            "majortick_length": L,
            "majortick_offset": 0,
            "grid": False,
            "secondary_y": {
                "range": (YLO, YHI),
                "tick_step": 1,
                "majortick_length": 2 * L,
            },
        }
    )
    left = _nubs_for_edge(ax, "left")
    right = _nubs_for_edge(ax, "right", length=2 * L)
    for pos in POSITIONS:
        iy, ey = left[pos]
        assert abs(ey - iy) == pytest.approx(L)  # frame-level length
        ixs, exs = right[pos]
        assert abs(exs - ixs) == pytest.approx(2 * L)  # secondary override