# WP-G: Serializer — restore flat `xlim`/`ylim` and `figsize` tuples

**Status**: complete
**Phase**: 14.54
**Depends on**: 14_54_wpa_axis_format_model.md

## Description

settings is serialized as a raw dict, so JSON round-trips coerce length-2
tuples into lists. `_settings_from_dict` already restores `xlim`/`ylim` and
`secondary_x`/`secondary_y.range` back to tuples. Extend it to:

1. Fix the latent `figsize` gap — `figsize` is tuple-valued but never restored
   to a tuple after JSON, unlike `xlim`/`ylim`.

Axis limits stay flat (`xlim`/`ylim`) — there is no nested `settings["axis"]`
dict to restore (that structured form was reverted).

## Changes

### `src/geofig_engine/serialize/converters.py`

- In `_settings_from_dict`:
  - Also restore `figsize` when it is a length-2 sequence of numbers → tuple.
  - Restore flat `xlim`/`ylim` (and `secondary_x`/`secondary_y.range`) to tuples
    (already present).
- No other settings keys change semantics.

## Acceptance criteria

- [ ] `figure_spec_to_dict`/`spec_from_json` round-trip preserves flat `xlim`/`ylim` as tuples
- [ ] Round-trip preserves `figsize` as a tuple
- [ ] Round-trip preserves `secondary_*.range` behavior (no regression)
- [ ] A spec without `xlim`/`ylim`/`figsize` round-trips unchanged

## Files

- `src/geofig_engine/serialize/converters.py`
- `tests/test_axis_format.py` (serialization round-trip)
- `tests/test_links.py` (serialization + validation, if referenced)
