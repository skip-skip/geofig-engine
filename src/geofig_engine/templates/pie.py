from typing import Any

from geofig_engine.core.coord import CoordPolar
from geofig_engine.core.geom import GeomBar
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatSum
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import SourceType


PIE_DEFAULTS: dict[str, Any] = {
    "figsize": (8, 8),
    "axis": {
        "xscale": "linear",
        "yscale": "linear",
        "grid": False,
        "xlabel": "",
        "ylabel": "",
        "options": {
            "hide_spine": True,
            "hide_angular_ticks": True,
            "hide_radial_labels": True,
            "hide_radial_ticks": True,
            "polar_tick_labels": True,
        },
    },
}


def pie(
    mapping: dict[str, SourceType] | None = None,
    show_percent: bool = False,
    show_count: bool = False,
    show_name: bool = True,
) -> FigureTemplate:
    mapping = mapping or {}
    cat_col = mapping.get("x")
    val_col = mapping.get("y")
    if cat_col is None or val_col is None:
        raise ValueError("pie template requires 'x' (category) and 'y' (value) in mapping")

    return FigureTemplate(
        name="pie",
        layers=[
            Layer(
                geom=GeomBar(),
                stat=StatSum(
                    column=str(val_col),
                    group=str(cat_col),
                    show_percent=show_percent,
                    show_count=show_count,
                    show_name=show_name,
                ),
                mapping={
                    "x": "x",
                    "y": 1.0,
                    "width": "width",
                    "color": "label",
                    "label": "label",
                },
            ),
        ],
        coord=CoordPolar(theta="x"),
        default_settings=dict(PIE_DEFAULTS),
    )
