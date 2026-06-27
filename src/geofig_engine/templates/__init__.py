"""
Template utilities for FigEngine.

This package exposes template building abstractions used by the engine.
"""

from .base import FigureTemplate
from .bivariate import bivariate
from .boxplot import boxplot_with_points
from .histogram import histogram
from .pie import pie
from .radar import radar
from .timeseries import timeseries
from .isotope import isotope

__all__ = [
    "FigureTemplate",
    "bivariate",
    "boxplot_with_points",
    "histogram",
    "pie",
    "radar",
    "timeseries",
    "isotope",
]
