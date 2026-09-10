"""
Bivariate figure template for FigEngine.

Defines the contract for two-dimensional plots with optional
color and marker encodings.
"""

from typing import Any

from geofig_engine.core.coord import CoordCartesian
from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.layer import Layer
from geofig_engine.core.scale import Scale
from geofig_engine.core.stat import StatIdentity
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import SourceType


BIVARIATE_DEFAULTS: dict[str, Any] = {
    "figsize": (10, 6),
    "xscale": "linear",
    "yscale": "linear",
    "y2scale": "linear",
    "grid": True,
}


def bivariate(
    mapping: dict[str, SourceType] | None = None,
    scales: dict[str, Scale] | None = None,
) -> FigureTemplate:
    return FigureTemplate(
        name="bivariate",
        layers=[
            Layer(
                geom=GeomPoint(),
                stat=StatIdentity(),
                mapping=mapping or {},
                scales=scales,
            )
        ],
        default_settings=dict(BIVARIATE_DEFAULTS),
    )


def bivariate_builder(
    mapping: dict[str, SourceType] | None = None,
    settings: dict[str, Any] | None = None,
    **_,
) -> "TemplateRecipe":
    """Pipeline registry builder for the ``bivariate`` key (15_wp6).

    Returns the canonical recipe shape with an x/y scatter on ``GeomPoint``
    plus ``CoordCartesian``. Usable with **no mapping beside ``data``/
    ``template``**: the recipe defaults to ``{"x": "x", "y": "y"}`` (the same
    sensible default the legacy workflow documents), and a ``color`` channel
    in the mapping drives grouping/cluster labels. User ``settings`` merge on
    top of the template defaults.

    The ``TemplateRecipe`` import is deferred to call time so this template
    module never depends on ``engine.api`` at import time.
    """
    from geofig_engine.engine.api import TemplateRecipe

    return TemplateRecipe(
        name="bivariate",
        layers=[
            Layer(
                geom=GeomPoint(),
                stat=StatIdentity(),
                mapping=mapping or {"x": "x", "y": "y"},
            )
        ],
        coord=CoordCartesian(),
        default_settings={**BIVARIATE_DEFAULTS, **(settings or {})},
    )
