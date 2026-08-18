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
from .npr_nnp import npr_nnp
from .anp_agp import anp_agp
from .nagph_nag import nagph_nag
from .piper import build_piper_specs, piper_overlay_diamond
from .stiff import plot_stiff

__all__ = [
    "FigureTemplate",
    "bivariate",
    "boxplot_with_points",
    "histogram",
    "pie",
    "radar",
    "timeseries",
    "isotope",
    "npr_nnp",
    "anp_agp",
    "nagph_nag",
    "build_piper_specs",
    "piper_overlay_diamond",
    "plot_stiff",
]
