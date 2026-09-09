# Phase 14.59: Majortick axis model

**Status**: closed
**Phase**: 14.59
**Dependencies**: none (foundation for `14_59_wp9`–`14_59_wp17`)

## Description

Add the majortick settings to the frame axis model so any drawn cartesian
frame can render major tick marks on its four edges. Four new `AxisFormat`
fields are picked from flat settings by `parse_axis_settings` and validated.

Naming/semantics:

- `majortick_length` — tick line length in local (frame) units; `None`
  disables majorticks entirely (the gate).
- `majortick_offset` — where the frame edge crosses the tick line, measured
  from the interior tip: `0` = wholly exterior, `1` = wholly interior,
  `0.5` = bisected. Default `0.0`.
- `majortick_width` — tick linewidth in points. Default `1.0`.
- `majortick_color` — tick color. Default `"black"`.

## Files to modify

- `src/geofig_engine/core/axis.py` — add the four fields to `AxisFormat`,
  `_pick` them in `parse_axis_settings`, and validate in `__post_init__`
  (length >= 0, offset in [0, 1], width > 0).

## Acceptance criteria

- [ ] `AxisFormat` has `majortick_length`, `majortick_offset`,
      `majortick_width`, `majortick_color` (all `None` by default)
- [ ] `parse_axis_settings` reads the four flat keys
- [ ] `majortick_offset` defaults to `0.0` when length is set but unset
- [ ] Validation raises `ValueError` for length < 0, offset outside [0, 1],
      width <= 0
- [ ] Ruff clean on modified file (no new findings vs baseline)