# WP-E: Serialization + validation for secondary axes

**Status**: open
**Phase**: 14.53
**Depends on**: 14_53_wpa_secondary_axis_model.md

## Description

Secondary axes live as structured entries in a spec's `settings`, which already
round-trips raw through the serializer. Ensure tuple-valued secondary `range`
entries survive a JSON round-trip, and add structural validation for the
secondary-axis settings shape.

## Changes

- `src/geofig_engine/serialize/converters.py`
  - `_settings_from_dict`: also restore length-2 list `range` entries under
    `secondary_x`/`secondary_y` as tuples (for round-trip equality), mirroring the
    existing `xlim`/`ylim` handling.
- `src/geofig_engine/core/spec.py`
  - `validate_figure_spec`: sanity-check `settings["secondary_x"]` /
    `settings["secondary_y"]` shape (`range` is length-2 numeric, `min != max`,
    recognized `position`/`label_policy` values) if present.

## Verification

- [ ] FigureSpec dict/JSON round-trip preserves `secondary_x`/`secondary_y` including tuple `range`
- [ ] Invalid secondary-axis settings raise clear validation errors

## Files

- `src/geofig_engine/serialize/converters.py`
- `src/geofig_engine/core/spec.py`
- `tests/test_links.py` (serialization + validation)
