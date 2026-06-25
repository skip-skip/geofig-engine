"""
Data module for FigEngine.

Provides function registry, validators, and data models for
mathematical functions with full metadata and geospatial information.
"""

from geofig_engine.data.functions import (
    FunctionType,
    FunctionCategory,
    GeospatialMetadata,
    MathFunction,
)
from geofig_engine.data.validator import FunctionValidator
from geofig_engine.data.registry import (
    FunctionRegistry,
    FunctionLoader,
    FunctionLoadError,
    get_function_registry,
)

__all__ = [
    "FunctionType",
    "FunctionCategory",
    "GeospatialMetadata",
    "MathFunction",
    "FunctionValidator",
    "FunctionRegistry",
    "FunctionLoader",
    "FunctionLoadError",
    "get_function_registry",
]
