"""
Isotope figure template for FigEngine.

Defines the contract for two-dimensional plots with optional
color and marker encodings.
"""

from collections.abc import Sequence

from geofig_engine.layers.function_line import FunctionLineLayer
from geofig_engine.layers.scatter import ScatterLayer
from geofig_engine.templates.base import FigureTemplate
from enum import Enum

class IsotopeTemplate(FigureTemplate):
    class MeteoricWaterLines(Enum):
        # Craig, 1961
        GLOBAL = {
            "label": "GMWL",
            "equation": "8*x+10",
            "color": "black",
            "linestyle": "--",
        }
        # Rightmire and Lewis, 1987
        ID_FALLS = {
            "label": "Idaho Falls LMWL",
            "equation": "7.5*x+5",
            "color": "blue",
            "linestyle": ":",
        }
        # Tappa et al., 2016
        ID_SOUTHEAST = {
            "label": "SE Idaho LMWL",
            "equation": "7.4*x-2.17",
            "color": "green",
            "linestyle": ":",
        }
        # Wood and Low, 1986
        ID_SNAKERIVER = {
            "label": "Snake River Basin LMWL",
            "equation": "6.4*x-21",
            "color": "red",
            "linestyle": ":",
        }
    def __init__(self, lines: Sequence[MeteoricWaterLines] | None = None,) -> None:
        line_layers = [
            FunctionLineLayer(
                func=line.value["equation"],
                color=line.value["color"],
                linestyle=line.value["linestyle"],
                label=line.value["label"]
            )
            for line in (lines or [])
        ]
        super().__init__(
            name="isotope",
            required_mappings=("x", "y"),
            optional_mappings=("color", "marker", "size", "alpha"),
            default_settings={
                "figsize": (10, 6),
                "xscale": "linear",
                "yscale": "linear",
                "grid": True,
            },
            projection=FigureTemplate.ProjectionType.CARTESIAN,
            layers = [*line_layers, ScatterLayer()]
        )
