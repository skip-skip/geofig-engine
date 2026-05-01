"""
Template utilities for FigEngine.

This package exposes template building abstractions used by the engine.
"""

from .base import FigureTemplate
from .bivariate import BivariateTemplate

__all__ = ["FigureTemplate", "BivariateTemplate"]
