import pandas as pd

from geofig_engine.core.coord import CoordCartesian
from geofig_engine.core.geom import GeomLine, GeomPolygon
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.core.spec import build_spec

_NICE_TICK_MAXES = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]


def _nice_tick_max(max_val: float) -> float:
    """Return a nice round max tick value >= max_val for a 5-tick scale.

    Produces ticks at -tick_max, -tick_max/2, 0, tick_max/2, tick_max.
    """
    for nm in _NICE_TICK_MAXES:
        if nm >= max_val:
            return nm
    return _NICE_TICK_MAXES[-1]


def plot_stiff(
    ca: float,
    mg: float,
    na_k: float,
    cl: float,
    hco3: float,
    so4: float,
    title: str = "",
    figsize: tuple[float, float] = (6, 6),
):
    max_val = max(ca, mg, na_k, cl, hco3, so4) or 1.0
    tick_max = _nice_tick_max(max_val)
    half = tick_max / 2.0

    ylo, yhi = -0.55, 2.5
    xlim = (-1.5 * tick_max, 1.5 * tick_max)

    # Raw signed meq/L vertices: cations negative on the left, anions positive
    # on the right, closing back to the first vertex.
    left_vals = [-na_k, -ca, -mg]
    right_vals = [cl, hco3, so4]
    y_positions = [2, 1, 0]
    poly_x = []
    poly_y = []
    for v, y in zip(left_vals, y_positions):
        poly_x.append(v)
        poly_y.append(y)
    for v, y in zip(right_vals, y_positions[::-1]):
        poly_x.append(v)
        poly_y.append(y)
    poly_x.append(left_vals[0])
    poly_y.append(2)

    data = pd.DataFrame({"x": poly_x, "y": poly_y})

    settings = {
        "figsize": figsize,
        "title": title,
        "xlim": xlim,
        "ylim": (ylo, yhi),
        "tick_step": half,
        "grid": False,
        "label_offset": 0.15,
        "abs_ticks": True,
        "xlabel": "meq/L",
        "y_tick_labels": {
            0: "Mg²⁺",
            1: "Ca²⁺",
            2: "Na⁺+K⁺",
        },
        "secondary_y": {
            # Range equal to the y limits so the anion rows line up with the
            # cation rows at y = 0, 1, 2.
            "range": [ylo, yhi],
            "tick_labels": {
                0: "SO₄²⁻",
                1: "HCO₃⁻",
                2: "Cl⁻",
            },
        },
    }

    layers = [
        LayerSpec(
            geom=GeomPolygon(edgecolor="black", edgewidth=1.5),
            stat=StatIdentity(),
            visual_mapping={
                "x": poly_x,
                "y": poly_y,
                "color": "lightblue",
            },
        ),
        LayerSpec(
            # Dashed cation/anion divider at x = 0, clipped to the frame box
            # bounds (a bounded segment, not an infinite abline).
            geom=GeomLine(),
            stat=StatIdentity(),
            visual_mapping={
                "x": [0, 0],
                "y": [ylo, yhi],
                "color": "black",
                "style": "dashed",
            },
        ),
    ]

    return build_spec(
        data=data,
        mappings={},
        settings=settings,
        context={},
        template_name="stiff",
        coord=CoordCartesian(),
        layers=layers,
    )