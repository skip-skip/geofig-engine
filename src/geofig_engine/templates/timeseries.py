"""
Timeseries figure template for FigEngine.

Defines the contract for two-dimensional plots with optional
color and marker encodings.
"""

from typing import Any

from geofig_engine.core.geom import GeomLine, GeomPoint
from geofig_engine.core.layer import Layer
from geofig_engine.core.scale import Scale
from geofig_engine.core.stat import StatIdentity
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import SourceType


TIMESERIES_DEFAULTS: dict[str, Any] = {
    "figsize": (10, 6),
    "xscale": "linear",
    "yscale": "linear",
    "y2scale": "linear",
    "time_format": "%Y-%m-%d",
    "grid": True,
}


def timeseries_builder(
    mapping: dict[str, SourceType] | None = None,
    settings: dict[str, Any] | None = None,
    **kwargs: Any,
) -> "TemplateRecipe":
    """Native registry builder for ``timeseries`` (18.4)."""
    from geofig_engine.engine.api import DEFAULT_TEMPLATE_MAPPING, TemplateRecipe

    options = settings or {}
    effective_mapping = (
        dict(mapping or {})
        if kwargs.get("_legacy_factory", False)
        else {**DEFAULT_TEMPLATE_MAPPING, **(mapping or {})}
    )
    scales = kwargs.get("scales")
    return TemplateRecipe(
        name="timeseries",
        layers=[
            Layer(
                geom=GeomLine(),
                stat=StatIdentity(),
                mapping=effective_mapping,
                scales=scales,
            ),
            Layer(
                geom=GeomPoint(),
                stat=StatIdentity(),
                mapping=effective_mapping,
                scales=scales,
            ),
        ],
        default_settings={**TIMESERIES_DEFAULTS, **options},
        mapping_consumed=True,
    )


def timeseries(
    mapping: dict[str, SourceType] | None = None,
    scales: dict[str, Scale] | None = None,
) -> FigureTemplate:
    recipe = timeseries_builder(mapping=mapping, scales=scales, _legacy_factory=True)
    return FigureTemplate(
        name=recipe.name,
        layers=recipe.layers,
        coord=recipe.coord,
        default_settings=recipe.default_settings,
    )
