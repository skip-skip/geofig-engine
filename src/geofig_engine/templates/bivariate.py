"""
Bivariate figure template for FigEngine.

Defines the contract for two-dimensional plots with optional
color and marker encodings.
"""

from typing import Any

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
