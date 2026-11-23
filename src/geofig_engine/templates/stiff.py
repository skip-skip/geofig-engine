from typing import TYPE_CHECKING, Any

import pandas as pd

from geofig_engine.core.coord import Coord, CoordCartesian
from geofig_engine.core.geom import GeomLine, GeomPolygon
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.core.spec import FigureSpec, build_spec

if TYPE_CHECKING:
    from geofig_engine.engine.api import SpecRecipe

STIFF_IONS = ("ca", "mg", "na_k", "cl", "hco3", "so4")

STIFF_DEFAULTS: dict[str, Any] = {
    "title": "",
    "figsize": (6, 6),
    "fontsize": None,
}

_NICE_TICK_MAXES = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]


def _nice_tick_max(max_val: float) -> float:
    """Return a nice round max tick value >= max_val for a 5-tick scale.

    Produces ticks at -tick_max, -tick_max/2, 0, tick_max/2, tick_max.
    """
    for nm in _NICE_TICK_MAXES:
        if nm >= max_val:
            return nm
    return _NICE_TICK_MAXES[-1]


def _build_stiff_specs(
    frame: pd.DataFrame,
    mapping: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
    coord: Coord | None = None,
) -> list[FigureSpec]:
    """Build the canonical stiff spec from a one-row ion frame."""
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("stiff frame must be a pandas DataFrame")
    missing = [column for column in STIFF_IONS if column not in frame.columns]
    if missing:
        raise ValueError(
            f"stiff frame requires ion columns {missing}; "
            f"available: {sorted(frame.columns)}"
        )
    if len(frame) != 1:
        raise ValueError(
            f"stiff template requires exactly one row of ion data; got {len(frame)}"
        )

    options = {**STIFF_DEFAULTS, **(settings or {})}
    row = frame.iloc[0]
    ca, mg, na_k, cl, hco3, so4 = (
        value.item() if hasattr(value, "item") else value
        for value in (row[column] for column in STIFF_IONS)
    )

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

    spec_settings = {
        "figsize": options["figsize"],
        "title": options["title"],
        "xlim": xlim,
        "ylim": (ylo, yhi),
        "tick_step": half,
        "grid": False,
        "label_offset": 0.15,
        "majortick_length": 0.06,
        "majortick_offset": 0,
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
    if options["fontsize"] is not None:
        spec_settings["fontsize"] = options["fontsize"]

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

    return [
        build_spec(
            data=data,
            mappings={},
            settings=spec_settings,
            context={},
            template_name="stiff",
            coord=CoordCartesian(),
            layers=layers,
        )
    ]


def stiff_builder(
    mapping: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
    **_: Any,
) -> "SpecRecipe":
    """Native registry builder for ``stiff`` (18.4 wp2)."""
    from geofig_engine.engine.api import SpecRecipe

    default_settings = {**STIFF_DEFAULTS, **(settings or {})}
    builder_mapping = dict(mapping or {})

    def build_specs(
        frame: pd.DataFrame,
        runtime_mapping: dict[str, Any] | None = None,
        runtime_settings: dict[str, Any] | None = None,
        coord: Coord | None = None,
    ) -> list[FigureSpec]:
        effective_mapping = {**builder_mapping, **(runtime_mapping or {})}
        options = {**default_settings, **(runtime_settings or {})}
        return _build_stiff_specs(
            frame,
            mapping=effective_mapping or None,
            settings=options,
            coord=coord,
        )

    return SpecRecipe(
        name="stiff",
        default_settings=default_settings,
        build_specs=build_specs,
    )


def plot_stiff(
    ca: float,
    mg: float,
    na_k: float,
    cl: float,
    hco3: float,
    so4: float,
    title: str = "",
    figsize: tuple[float, float] = (6, 6),
    fontsize: float | None = None,
):
    """Build a stiff-diagram FigureSpec from one water analysis.

    ``fontsize`` sets the generic font-size fallback on the spec; omit it to
    keep renderer defaults.
    """
    frame = pd.DataFrame(
        {
            "ca": [ca],
            "mg": [mg],
            "na_k": [na_k],
            "cl": [cl],
            "hco3": [hco3],
            "so4": [so4],
        }
    )
    settings: dict[str, Any] = {"title": title, "figsize": figsize}
    if fontsize is not None:
        settings["fontsize"] = fontsize
    return _build_stiff_specs(frame, settings=settings)[0]