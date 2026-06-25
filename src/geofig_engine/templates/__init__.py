"""
Template utilities for FigEngine.

This package exposes template building abstractions used by the engine.
"""

from .base import FigureTemplate
from .bivariate import bivariate
from .timeseries import timeseries
from .isotope import isotope

__all__ = [
    "FigureTemplate",
    "bivariate",
    "timeseries",
    "isotope",
]
