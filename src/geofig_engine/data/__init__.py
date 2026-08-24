"""
Data module for FigEngine.

Provides the geom preset registry (categorized preset geometries),
expression validators, and legacy function-registry views over the
preset catalog.
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
from geofig_engine.data.geom_presets import (
    GEOM_KINDS,
    GeomPreset,
    GeomPresetItem,
    GeomPresetLoader,
    GeomPresetLoadError,
    GeomPresetRegistry,
    get_geom_preset_registry,
    reset_geom_preset_registry,
    item_to_layer,
    preset_to_layers,
)

__all__ = [
    # Legacy function API (view over geom presets)
    "FunctionType",
    "FunctionCategory",
    "GeospatialMetadata",
    "MathFunction",
    "FunctionValidator",
    "FunctionRegistry",
    "FunctionLoader",
    "FunctionLoadError",
    "get_function_registry",
    # Geom preset API
    "GEOM_KINDS",
    "GeomPreset",
    "GeomPresetItem",
    "GeomPresetLoader",
    "GeomPresetLoadError",
    "GeomPresetRegistry",
    "get_geom_preset_registry",
    "reset_geom_preset_registry",
    "item_to_layer",
    "preset_to_layers",
]
