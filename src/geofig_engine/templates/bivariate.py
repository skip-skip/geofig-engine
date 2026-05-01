"""
Bivariate figure template for FigEngine.

Defines the contract for two-dimensional plots with optional
color and marker encodings.
"""

from geofig_engine.templates.base import FigureTemplate


class BivariateTemplate(FigureTemplate):
    def __init__(self) -> None:
        super().__init__(
            name="bivariate",
            required_mappings=("x", "y"),
            optional_mappings=("color", "marker", "size", "alpha", "linestyle"),
            default_settings={"alpha": 0.8, "figsize": (10, 6)},
        )
