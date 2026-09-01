# Phase 14.57: Independent axis-label and tick-label rotation policies

**Status**: complete
**Phase**: 14.57
**Dependencies**: `14_56_*` (font-size knobs)

## Description

Split the single `label_policy` (upright/parallel) text-rotation control into
two independently-settable policies: one for **axis labels** (frame/edge titles,
ternary ion names) and one for **tick labels**. Both inherit from `label_policy`
unless overridden, preserving existing configurations. Also fix a latent bug where
all three ternary ion labels rotated with the base-edge tangent instead of each
following its own edge.

## Changes

### `src/geofig_engine/core/axis.py`

- Add `axis_label_policy: str | None = None` and `tick_label_policy: str | None = None`
  to `AxisFormat`. `None` means "inherit".
- Validate both in `__post_init__` via `_policy_value` (one of
  `("upright", "parallel")`).
- Add effective resolvers `axis_label_policy_eff()` / `tick_label_policy_eff()`,
  returning the per-kind value when set, else the shared `label_policy`.
- `parse_axis_settings` reads the new flat keys.

### `src/geofig_engine/core/secondary_axis.py`

- Add `axis_label_policy` / `tick_label_policy` to `SecondaryAxis` (default `None`
  = inherit the secondary's `label_policy`), with validation and effective
  resolvers.
- `parse_secondary_settings` inherits them from `defaults` (the primary's
  effective policies) unless the declaration overrides them.

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- `_draw_ternary_frame`: use `tick_label_policy_eff()` for tick labels and
  `axis_label_policy_eff()` for the ion edge labels.
- Fix ternary ion labels: each ion rotates parallel to **its own** edge
  (base `(1,0)`, left `(0.5, sqrt3/2)`, right `(-0.5, sqrt3/2)`), replacing the
  shared base tangent.
- `_draw_cartesian_axis`: primary ticks use `tick_label_policy_eff()`; secondary
  ticks use `sec.tick_label_policy_eff()`; secondary titles use
  `sec.axis_label_policy_eff()`. Pass primary effective policies into
  `parse_secondary_settings` defaults.

## Acceptance criteria

- [x] `axis_label_policy` and `tick_label_policy` parse/validate independently
- [x] Both inherit from `label_policy` unless set (backward compatible)
- [x] `label_policy: "parallel"` still rotates both (inheritance)
- [x] Ternary ion labels each rotate parallel to their own edge under "parallel"
- [x] Cartesian/ternary/secondary ticks vs titles rotate independently
- [x] Full suite passes (968); default output unchanged

## Files

- `src/geofig_engine/core/axis.py`
- `src/geofig_engine/core/secondary_axis.py`
- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `tests/test_axis_format.py`
- `tests/test_secondary_axis.py`
