# Phase 14.59: Absolute-value & named tick labels for cartesian frames

**Status**: complete
**Phase**: 14.59
**Dependencies**: `14_58` (piper charge labels)

## Description

Add two declarative capabilities to the cartesian frame so the Stiff diagram can
be re-expressed as a plain `CoordCartesian` figure (WP4):

1. **`abs_ticks`** — numeric tick labels displayed as absolute values. The
   current `_tick_label(value, fmt)` only supports format-specs; there is no way
   to show `-20` as `20`.
2. **`tick_labels`** — named string labels at exact positions, drawn **including
   frame edges** (the current `np.arange` tick path skips edge ticks — the Stiff
   diagram needs labels at y = 0 and y = 2). Supported on primary axes and inside
   `secondary_x`/`secondary_y` declarations (dual y axes for the anion names).

Both live in the matplotlib-free `AxisFormat`/`SecondaryAxis` models so they can
be unit-tested directly and reused by the frame renderer (WP2). New settings are
flat top-level keys; `tick_labels` maps are string-keyed after JSON round-trips.

## Changes

### `src/geofig_engine/core/axis.py`

- Add `abs_ticks: bool = False` to `AxisFormat`, validated in `__post_init__`
  via `_bool_value` (plain bool, `None` rejected like `x_reversed`/`y_reversed`).
- Add `tick_labels: dict` (position → label) to `AxisFormat`; validate it is a
  dict of numeric keys to non-empty string values.
- `parse_axis_settings` reads new flat keys `abs_ticks` and `tick_labels`.

### `src/geofig_engine/core/secondary_axis.py`

- Add `abs_ticks` and `tick_labels` to `SecondaryAxis` (validated, defaulting to
  inherit the primary's values unless the declaration overrides).
- `parse_secondary_settings` inherits `abs_ticks` / `tick_labels` from the
  primary's effective values.
- When `tick_labels` is set, named labels participate in
  `tick_coordinates()`, including edge positions.

### `src/geofig_engine/core/spec.py`

- `_validate_axis_settings` (via `parse_axis_settings`) and the secondary
  settings validation reject malformed `abs_ticks` / `tick_labels`.

### `src/geofig_engine/serialize/converters.py`

- Verify settings round-trip: string-keyed `tick_labels` maps survive JSON;
  `_settings_from_dict` continues to restore tuple ranges (no change expected).

## Acceptance criteria

- [ ] `parse_axis_settings({"abs_ticks": True})` sets the field; bad values rejected
- [ ] `tick_labels` parses on primary axes and inside `secondary_x`/`secondary_y`
- [ ] Secondary declarations inherit/override primary `abs_ticks` / `tick_labels`
- [ ] Named labels cover frame-edge positions (no endpoint skip)
- [ ] Malformed declarations raise `ValueError`
- [ ] Unit tests added in `tests/test_axis_format.py` / `tests/test_secondary_axis.py`

## Files

- `src/geofig_engine/core/axis.py`
- `src/geofig_engine/core/secondary_axis.py`
- `src/geofig_engine/core/spec.py`
- `src/geofig_engine/serialize/converters.py`
- `tests/test_axis_format.py`
- `tests/test_secondary_axis.py`