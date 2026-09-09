# Phase 14.59: Majorticks on secondary axes (inheritance)

**Status**: closed
**Phase**: 14.59
**Dependencies**: `14_59_wp8_majortick_axis_model`

## Description

Extend the majortick settings to the secondary axes (`x2`/`y2`, i.e.
`secondary_x`/`secondary_y`). Each `SecondaryAxis` carries the same four
nullable fields; `parse_secondary_settings` reads them from the secondary
dict with fallback to frame-level values, mirroring the existing
`tick_step`/`label_policy`/`abs_ticks` inheritance. The effective value for
an edge is `sec.<field> if not None else axis.<field>`.

## Files to modify

- `src/geofig_engine/core/secondary_axis.py` — add `majortick_length`,
  `majortick_offset`, `majortick_width`, `majortick_color` fields
  (default `None`); parse + validate in `parse_secondary_settings`.

## Acceptance criteria

- [ ] `SecondaryAxis` exposes the four fields (default `None`)
- [ ] `parse_secondary_settings` picks the four keys from each secondary
      declaration
- [ ] Omitted secondary keys fall back to frame-level values passed via
      `defaults`
- [ ] Validation matches the primary (`offset` in [0, 1], etc.)
- [ ] Existing secondary tests still pass