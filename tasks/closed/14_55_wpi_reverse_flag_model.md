# WP-I: `x_reversed`/`y_reversed` common fields in `AxisFormat` (core/axis.py)

**Status**: complete
**Phase**: 14.55
**Dependencies**: none (first WP of the reversal series)

## Description

Add **common** `AxisFormat` settings to declaratively reverse a cartesian axis.
Today there is **no** reverse capability: the ROADMAP 14.55 entry explicitly
states "there is no `reverse` handedness flag", and `_draw_cartesian_axis`
hardcodes arrows to point toward ascending numeric value **regardless of
declared limit order** (renderer.py:500-501). Reversing a diamond child's
`xlim`/`ylim` to `(100, 0)` therefore changes *nothing* about the arrows and
merely breaks grid/ticks (empty `np.arange`) and misplaces titles.

This WP adds the declarative control — `x_reversed`/`y_reversed` — that a later
WP uses to reverse tick labels **and** arrow direction together (arrows must
always point toward increasing data, so a reversed axis's arrows flip with it).

Follows the existing common-field convention (`axis_arrows`, `grid`, etc.): flat
top-level settings keys parsed into validated `AxisFormat` fields.

## Changes

### `src/geofig_engine/core/axis.py`

- Add two common fields alongside `axis_arrows`:
  - `x_reversed: bool = False`
  - `y_reversed: bool = False`
- In `__post_init__`, validate each with `_bool_value(self.x_reversed, "x_reversed")`
  / `_bool_value(self.y_reversed, "y_reversed")` — reject non-bool values with
  `ValueError` (bools only; fields default `False`, not `None`).
- In `parse_axis_settings`, read the flat top-level keys:
  - `x_reversed=_pick("x_reversed", default=False)`
  - `y_reversed=_pick("y_reversed", default=False)`
- Update the module docstring's list of flat keys to include `x_reversed` /
  `y_reversed`.

## Acceptance criteria

- [ ] `parse_axis_settings({}, coord).x_reversed` is `False` and `.y_reversed` is `False` (defaults)
- [ ] `parse_axis_settings({"x_reversed": True, "y_reversed": True}, coord)` round-trips to `True`/`True`
- [ ] `AxisFormat(x_reversed="nope")` and `AxisFormat(y_reversed=1)` raise `ValueError`
- [ ] Bools are the only accepted values; `None` is **not** accepted (these are plain bools, unlike `axis_arrows`)
- [ ] No matplotlib imports added to `core/axis.py`

## Files

- `src/geofig_engine/core/axis.py`
- `tests/test_axis_format.py` (model/parse/validation additions)
