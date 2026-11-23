"""
Template utilities for FigEngine.

This package exposes template building abstractions used by the engine.
"""

from .anp_agp import anp_agp, anp_agp_builder
from .base import FigureTemplate
from .bivariate import bivariate
from .boxplot import boxplot_with_points
from .histogram import histogram, histogram_builder
from .isotope import isotope, isotope_builder
from .nagph_nag import nagph_nag, nagph_nag_builder
from .npr_nnp import npr_nnp, npr_nnp_builder
from .pie import pie, pie_builder
from .piper import build_piper_specs, piper_builder
from .radar import radar, radar_builder
from .stiff import plot_stiff, stiff_builder
from .timeseries import timeseries, timeseries_builder

__all__ = [
    "FigureTemplate",
    "bivariate",
    "boxplot_with_points",
    "histogram",
    "histogram_builder",
    "pie",
    "pie_builder",
    "radar",
    "radar_builder",
    "timeseries",
    "timeseries_builder",
    "isotope",
    "isotope_builder",
    "npr_nnp",
    "npr_nnp_builder",
    "anp_agp",
    "anp_agp_builder",
    "nagph_nag",
    "nagph_nag_builder",
    "build_piper_specs",
    "piper_builder",
    "plot_stiff",
    "stiff_builder",
]
