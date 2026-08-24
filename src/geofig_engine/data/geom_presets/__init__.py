"""
Geometry presets package.

Categorized, data-only catalog of preset geometries (reference lines,
bands, rectangles, labels) that hydrate into standard Layers. Bundled
presets live as JSON files next to this module; user-supplied files can
be merged via GeomPresetRegistry.merge_path().
"""

from geofig_engine.data.geom_presets.models import (
    GEOM_KINDS,
    GeomPreset,
    GeomPresetItem,
)
from geofig_engine.data.geom_presets.loader import (
    GeomPresetLoader,
    GeomPresetLoadError,
)
from geofig_engine.data.geom_presets.registry import (
    GeomPresetRegistry,
    get_geom_preset_registry,
    reset_geom_preset_registry,
    item_to_layer,
    preset_to_layers,
)

__all__ = [
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
