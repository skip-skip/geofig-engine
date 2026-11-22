from typing import Any

from geofig_engine.core.coord import CoordPolar
from geofig_engine.core.geom import GeomBar
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatSum
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import SourceType


PIE_DEFAULTS: dict[str, Any] = {
    "figsize": (8, 8),
    "xscale": "linear",
    "yscale": "linear",
    "grid": False,
    "hide_spine": True,
    "hide_angular_ticks": True,
    "hide_radial_labels": True,
    "hide_radial_ticks": True,
    "polar_tick_labels": True,
    "xlabel": "",
    "ylabel": "",
}


def pie_builder(
    mapping: dict[str, SourceType] | None = None,
    settings: dict[str, Any] | None = None,
    **kwargs: Any,
) -> "TemplateRecipe":
    """Native registry builder for ``pie`` (18.4).

    ``show_percent`` / ``show_count`` / ``show_name`` come from flat settings
    or direct factory kwargs; renderer settings merge into the defaults.
    """
    from geofig_engine.engine.api import DEFAULT_TEMPLATE_MAPPING, TemplateRecipe

    options = settings or {}
    effective_mapping = (
        dict(mapping or {})
        if kwargs.get("_legacy_factory", False)
        else {**DEFAULT_TEMPLATE_MAPPING, **(mapping or {})}
    )
    cat_col = effective_mapping.get("x")
    val_col = effective_mapping.get("y")
    if cat_col is None or val_col is None:
        raise ValueError("pie template requires 'x' (category) and 'y' (value) in mapping")

    return TemplateRecipe(
        name="pie",
        layers=[
            Layer(
                geom=GeomBar(),
                stat=StatSum(
                    column=str(val_col),
                    group=str(cat_col),
                    show_percent=kwargs.get(
                        "show_percent", options.get("show_percent", False)
                    ),
                    show_count=kwargs.get(
                        "show_count", options.get("show_count", False)
                    ),
                    show_name=kwargs.get(
                        "show_name", options.get("show_name", True)
                    ),
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
        default_settings={**PIE_DEFAULTS, **options},
        mapping_consumed=True,
    )


def pie(
    mapping: dict[str, SourceType] | None = None,
    show_percent: bool = False,
    show_count: bool = False,
    show_name: bool = True,
) -> FigureTemplate:
    recipe = pie_builder(
        mapping=mapping,
        show_percent=show_percent,
        show_count=show_count,
        show_name=show_name,
        _legacy_factory=True,
    )
    return FigureTemplate(
        name=recipe.name,
        layers=recipe.layers,
        coord=recipe.coord,
        default_settings=recipe.default_settings,
    )
