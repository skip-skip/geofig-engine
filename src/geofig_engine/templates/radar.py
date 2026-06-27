from typing import Any

from geofig_engine.core.coord import CoordPolar
from geofig_engine.core.geom import GeomArea, GeomLine, GeomText
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatRadar
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import SourceType


RADAR_DEFAULTS: dict[str, Any] = {
    "figsize": (8, 8),
    "xscale": "linear",
    "yscale": "linear",
    "grid": True,
    "hide_spine": True,
    "hide_angular_ticks": True,
    "polar_tick_labels": True,
    "xlabel": "",
    "ylabel": "",
}


def radar(
    mapping: dict[str, SourceType] | None = None,
    fill: bool = True,
    fill_alpha: float = 0.7,
    shared_axes: bool = True,
) -> FigureTemplate:
    mapping = mapping or {}
    x_col = mapping.get("x")
    y_col = mapping.get("y")
    if x_col is None or y_col is None:
        raise ValueError("radar template requires 'x' (axis) and 'y' (value) in mapping")

    layers: list[Layer] = []

    line_mapping: dict[str, SourceType] = {"x": "x", "y": "y", "label": "x_label"}
    if "color" in mapping:
        line_mapping["color"] = mapping["color"]

    color_col = str(mapping["color"]) if "color" in mapping else None

    if fill:
        layers.append(
            Layer(
                geom=GeomArea(),
                stat=StatRadar(shared_axes=shared_axes, x_col=str(x_col), y_col=str(y_col), color_col=color_col),
                mapping={**line_mapping, "alpha": fill_alpha},
            ),
        )

    layers.append(
        Layer(
            geom=GeomLine(),
            stat=StatRadar(shared_axes=shared_axes, x_col=str(x_col), y_col=str(y_col), color_col=color_col),
            mapping=dict(line_mapping),
        ),
    )

    return FigureTemplate(
        name="radar",
        layers=layers,
        coord=CoordPolar(theta="x"),
        default_settings=dict(RADAR_DEFAULTS),
    )
