"""
Timeseries figure template for FigEngine.

Defines the contract for two-dimensional plots with optional
color and marker encodings.
"""

from geofig_engine.layers.line import LineLayer
from geofig_engine.layers.scatter import ScatterLayer
from geofig_engine.templates.base import FigureTemplate


class TimeseriesTemplate(FigureTemplate):
    def __init__(self) -> None:
        super().__init__(
            name="timeseries",
            required_mappings=("x", "y"),
            optional_mappings=("y2", "color", "marker", "size", "style", "alpha", "width"),
            default_settings={
                "figsize": (10, 6),
                "xscale": "linear",
                "yscale": "linear",
                "y2scale": "linear",
                "time_format": "%Y-%m-%d",
                "grid": True,
                "figname": None,
            },
            projection=FigureTemplate.ProjectionType.CARTESIAN,
            layers = [LineLayer(), ScatterLayer()]
        )
