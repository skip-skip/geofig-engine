"""
geofig_engine

A modular plotting engine for structured, multi-dimensional data visualization.
"""

# Core data structures
from .core.dataset import Dataset
from .core.dimension import Dimension
from .core.dimension_selector import DimensionSelector
from .core.iterator import ColumnSelector

# Engine
from .engine import FigureEngine

# Renderers
from .renderers import MatplotlibRenderer

# Templates
from .templates import BivariateTemplate

__all__ = [
    "Dataset",
    "Dimension",
    "DimensionSelector",
    "ColumnSelector",
    "FigureEngine",
    "MatplotlibRenderer",
    "BivariateTemplate",
]