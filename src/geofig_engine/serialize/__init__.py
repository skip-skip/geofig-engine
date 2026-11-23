"""
Serialize: JSON round-trip for FigureSpec and core types.

Converts fully resolved FigureSpec instances (post-engine) to/from
JSON-compatible dicts and strings. All core types (Geom, Coord, Facet,
Scale, Stat, LayerSpec) are handled recursively.

A separate versioned dashboard projection (``specs_to_dashboard_dict`` /
``specs_to_dashboard_json``) is available for browser display without changing
the round-trip format. Transport-agnostic patches between snapshots are built
and applied with ``diff_dashboard_payload`` / ``apply_dashboard_patch``.
"""

from geofig_engine.serialize.dashboard_patch import (
    DASHBOARD_PATCH_SCHEMA,
    DASHBOARD_PATCH_SCHEMA_VERSION,
    apply_dashboard_patch,
    diff_dashboard_payload,
    validate_dashboard_patch,
)
from geofig_engine.serialize.dashboard import (
    DASHBOARD_SCHEMA,
    DASHBOARD_SCHEMA_VERSION,
    specs_to_dashboard_dict,
    specs_to_dashboard_json,
    validate_dashboard_payload,
)
from geofig_engine.serialize.converters import (
    figure_spec_from_dict,
    figure_spec_to_dict,
    geom_from_dict,
    geom_to_dict,
    coord_from_dict,
    coord_to_dict,
    facet_from_dict,
    facet_to_dict,
    scale_from_dict,
    scale_to_dict,
    stat_from_dict,
    stat_to_dict,
    layer_spec_from_dict,
    layer_spec_to_dict,
    spec_from_json,
    spec_to_json,
)

__all__ = [
    "figure_spec_from_dict",
    "figure_spec_to_dict",
    "geom_from_dict",
    "geom_to_dict",
    "coord_from_dict",
    "coord_to_dict",
    "facet_from_dict",
    "facet_to_dict",
    "scale_from_dict",
    "scale_to_dict",
    "stat_from_dict",
    "stat_to_dict",
    "layer_spec_from_dict",
    "layer_spec_to_dict",
    "spec_from_json",
    "spec_to_json",
    "DASHBOARD_SCHEMA",
    "DASHBOARD_SCHEMA_VERSION",
    "specs_to_dashboard_dict",
    "specs_to_dashboard_json",
    "validate_dashboard_payload",
    "DASHBOARD_PATCH_SCHEMA",
    "DASHBOARD_PATCH_SCHEMA_VERSION",
    "diff_dashboard_payload",
    "apply_dashboard_patch",
    "validate_dashboard_patch",
]
