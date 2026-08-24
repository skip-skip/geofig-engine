"""
Core components of the FigEngine visualization system.

This module provides the fundamental building blocks for declarative visualization:
- Dataset: Tidy data with semantic metadata
- Dimension: Column metadata and attributes
- DimensionSelector: Flexible column selection
- AttributeMapping: Visual attribute mappings
- Iterator: Multi-figure generation
- FigureSpec: Renderer-agnostic plotting instructions
"""

# Dataset and data management
from .dataset import Dataset

# Dimension metadata
from .dimension import Dimension

# Column selection
from .dimension_selector import DimensionSelector

# Visual attribute mappings
from .attribute_mapping import (
    AttributeMapping,
    validate_attribute_mapping,
    resolve_source,
)

# Multi-figure iteration
from .iterator import (
    ColumnSelector,
    IteratorContext,
    IteratorResult,
    expand,
)

# Figure specifications
from .spec import (
    FigureSpec,
    validate_figure_spec,
    build_spec,
    extract_data_for_mapping,
)

# Linked secondary axes
from .link import (
    AxisLink,
    LinkTransform,
)

__all__ = [
    # Dataset
    "Dataset",
    # Dimension
    "Dimension",
    # DimensionSelector
    "DimensionSelector",
    # AttributeMapping
    "AttributeMapping",
    "validate_attribute_mapping",
    "resolve_source",
    # Iterator
    "ColumnSelector",
    "IteratorContext",
    "IteratorResult",
    "expand",
    # FigureSpec
    "FigureSpec",
    "validate_figure_spec",
    "build_spec",
    "extract_data_for_mapping",
    # Linked axes
    "AxisLink",
    "LinkTransform",
]