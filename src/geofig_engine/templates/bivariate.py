"""
Bivariate figure template for FigEngine.

Defines the contract for two-dimensional plots with optional
color and marker encodings.
"""

from geofig_engine.layers.scatter import ScatterLayer
from geofig_engine.templates.base import FigureTemplate


class BivariateTemplate(FigureTemplate):
    def __init__(self) -> None:
        super().__init__(
            name="bivariate",
            required_mappings=("x", "y"),
            optional_mappings=("y2", "color", "marker", "size", "alpha"),
            default_settings={
                "figsize": (10, 6),
                "xscale": "linear",
                "yscale": "linear",
                "y2scale": "linear",
                "figname": None,
                "grid": True,
            },
            projection=FigureTemplate.ProjectionType.CARTESIAN,
            layers = [ScatterLayer()]
        )
