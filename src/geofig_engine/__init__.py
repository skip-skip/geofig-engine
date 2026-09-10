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

# Declarative API (Phase 15): template registry + recipe shape
from .engine.api import TEMPLATES, get_template, register_template

# Provider contract (Phase 15)
from .provider import DataProvider, DataFrameProvider, DatasetProvider

# Renderers
from .renderers import MatplotlibRenderer

__all__ = [
    "Dataset",
    "Dimension",
    "DimensionSelector",
    "ColumnSelector",
    "FigureEngine",
    "TEMPLATES",
    "register_template",
    "get_template",
    "DataProvider",
    "DataFrameProvider",
    "DatasetProvider",
    "MatplotlibRenderer",
]