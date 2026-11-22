from typing import Any

from geofig_engine.core.coord import CoordPolar
from geofig_engine.core.geom import GeomArea, GeomLine, GeomText
from geofig_engine.core.layer import Layer
from geofig_engine.core.scale import ScaleNormalize
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


def radar_builder(
    mapping: dict[str, SourceType] | None = None,
    settings: dict[str, Any] | None = None,
    **kwargs: Any,
) -> "TemplateRecipe":
    """Native registry builder for ``radar`` (18.4).

    ``fill`` / ``fill_alpha`` / ``shared_axes`` come from flat settings or
    direct factory kwargs; renderer settings merge into the defaults.
    """
    from geofig_engine.engine.api import DEFAULT_TEMPLATE_MAPPING, TemplateRecipe

    options = settings or {}
    effective_mapping = (
        dict(mapping or {})
        if kwargs.get("_legacy_factory", False)
        else {**DEFAULT_TEMPLATE_MAPPING, **(mapping or {})}
    )
    x_col = effective_mapping.get("x")
    y_col = effective_mapping.get("y")
    if x_col is None or y_col is None:
        raise ValueError("radar template requires 'x' (axis) and 'y' (value) in mapping")

    fill = kwargs.get("fill", options.get("fill", True))
    fill_alpha = kwargs.get("fill_alpha", options.get("fill_alpha", 0.7))
    shared_axes = kwargs.get("shared_axes", options.get("shared_axes", True))

    layers: list[Layer] = []
    line_mapping: dict[str, SourceType] = {"x": "x", "y": "y", "label": "x_label"}
    if "color" in effective_mapping:
        line_mapping["color"] = effective_mapping["color"]

    color_col = str(effective_mapping["color"]) if "color" in effective_mapping else None
    y_scale = ScaleNormalize(range_min=0.0, range_max=1.0)

    if fill:
        layers.append(
            Layer(
                geom=GeomArea(),
                stat=StatRadar(
                    shared_axes=shared_axes,
                    x_col=str(x_col),
                    y_col=str(y_col),
                    color_col=color_col,
                ),
                mapping={**line_mapping, "alpha": fill_alpha},
                scales={"y": y_scale},
            ),
        )

    layers.append(
        Layer(
            geom=GeomLine(),
            stat=StatRadar(
                shared_axes=shared_axes,
                x_col=str(x_col),
                y_col=str(y_col),
                color_col=color_col,
            ),
            mapping=dict(line_mapping),
            scales={"y": y_scale},
        ),
    )

    return TemplateRecipe(
        name="radar",
        layers=layers,
        coord=CoordPolar(theta="x"),
        default_settings={**RADAR_DEFAULTS, **options},
        mapping_consumed=True,
    )


def radar(
    mapping: dict[str, SourceType] | None = None,
    fill: bool = True,
    fill_alpha: float = 0.7,
    shared_axes: bool = True,
) -> FigureTemplate:
    recipe = radar_builder(
        mapping=mapping,
        fill=fill,
        fill_alpha=fill_alpha,
        shared_axes=shared_axes,
        _legacy_factory=True,
    )
    return FigureTemplate(
        name=recipe.name,
        layers=recipe.layers,
        coord=recipe.coord,
        default_settings=recipe.default_settings,
    )
