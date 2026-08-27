# WP4: Serialization updates

**Status**: open
**Phase**: 14.52
**Depends on**: 14_52_wp1_fluent_link_transform.md

## Description

Update serialization to the new `LinkTransform.to_dict()` / `from_dict()` ordered-op representation. The converter structure is unchanged — only the dict shape of a transform changes.

## Changes

### `src/geofig_engine/serialize/converters.py`

- `figure_spec_to_dict` / `_spec_to_dict` (lines 444, 464) still call `spec.transform.to_dict()` — confirm output uses the op-list shape
- `_spec_from_dict` (line 495) still calls `LinkTransform.from_dict(...)` — confirm it reads the op-list
- No structural logic changes expected; verify the new `to_dict`/`from_dict` contract round-trips

## Acceptance criteria

- [ ] FigureSpec with children serializes/deserializes transforms via the new op-list form
- [ ] `spec_from_json`/`spec_to_json` round-trips preserve exact ordered transform ops
- [ ] Existing serialization tests pass (see WP5)

## Files

- `src/geofig_engine/serialize/converters.py`
- `src/geofig_engine/core/link.py` (to_dict/from_dict if needed)
