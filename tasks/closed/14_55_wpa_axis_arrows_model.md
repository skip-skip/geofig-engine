# WP-A: `axis_arrows` common field in `AxisFormat` (core/axis.py)

**Status**: complete
**Phase**: 14.55
**Dependencies**: none (first WP)

## Description

Add a **common** `AxisFormat` setting that toggles axis-direction arrows on
the unified framed-axis pipeline. Today arrows exist **only** in the ternary
frame, hardcoded in `_draw_ternary_frame` and fused with the ion edge labels
(see WP-D for decoupling). This WP adds the declarative control that will let
**all** framed axes (cartesian x/y, cartesian secondary, ternary edges, polar
radial) draw an arrow pointing toward increasing values.

Follows the existing common-field convention (`grid`, `label_policy`, etc.) —
a flat top-level settings key parsed into a validated `AxisFormat` field, not a
per-coordinate `options` entry.

## Changes

### `src/geofig_engine/core/axis.py`

- Add a common field alongside `grid`:
  - `axis_arrows: bool | None = None`
- In `__post_init__`, validate it with `_bool_value(self.axis_arrows, "axis_arrows")`
  when not `None` (mirror the `grid` handling) — reject non-bool values with
  `ValueError`.
- Add a convenience accessor (the renderer needs an effective bool):
  - `def show_arrows(self) -> bool:` returning `bool(self.axis_arrows)` so callers
    get a plain `False` when the setting is absent/`None`.
- In `parse_axis_settings`, read the flat top-level key:
  - `axis_arrows=_pick("axis_arrows")`
- Update the module docstring's list of flat keys to include `axis_arrows`.

## Acceptance criteria

- [ ] `parse_axis_settings({}, coord).show_arrows()` is `False` (default off)
- [ ] `parse_axis_settings({"axis_arrows": True}, coord).show_arrows()` is `True`
- [ ] `AxisFormat(axis_arrows="nope")` / `parse_axis_settings({"axis_arrows": "nope"}, coord)` raise `ValueError`
- [ ] Non-boolean values are rejected; `None` is allowed (treated as off)
- [ ] No matplotlib imports added to `core/axis.py`

## Files

- `src/geofig_engine/core/axis.py`
- `tests/test_axis_format.py` (model/parse/validation additions)
