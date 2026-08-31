# WP-C: Custom polar frame `_draw_polar_frame` on AxisFormat

**Status**: complete
**Phase**: 14.54
**Depends on**: 14_54_wpa_axis_format_model.md

## Description

Pie and radar use matplotlib's polar projection — a structurally different Axes
type that cannot use the cartesian/ternary custom frame drawer. To fully unify
the pipeline, add a **custom polar frame drawer**, `_draw_polar_frame(ax, axis)`,
driven by the shared `AxisFormat` + its polar `options`. Both the top-level
polar spec (pie/radar) and any polar child route through `_draw_frame` → this
function (WP-B). Native matplotlib polar ticks/grid are replaced by the
AxisFormat-driven rendering; appearance is preserved so pie/radar output matches
today.

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- Add `_draw_polar_frame(ax, axis)`:
  - Draw angular (theta) tick labels at positions derived from the layer's
    x-mapping categories (via the existing `_apply_polar_ticks` label map), using
    `axis.tick_format` / `axis.tick_fontsize`.
  - Draw the radial threshold grid / radial labels per `AxisFormat` (`grid`,
    `grid_style`, `grid_step`, `tick_step`), replacing reliance on native polar
    grid when `grid` is set.
  - Honor `axis.options`: `hide_spine`, `hide_angular_ticks`,
    `hide_angular_labels`, `hide_radial_ticks`, `hide_radial_labels`,
    `polar_tick_labels`.
  - Keep the polar Axes projection in `_render_single` (it is the only way
    matplotlib can draw sectors/radar lines), but route **tick/grid/label
    formatting** through `axis`.
- Wire into `_draw_frame` (WP-B) via the `CoordPolar` branch.
- Preserve `_apply_polar_ticks` behavior (label map from layer x/label).

## Acceptance criteria

- [ ] Pie and radar render with the same appearance as today (sectors, ticks, labels)
- [ ] `hide_*` toggles via `AxisFormat.options` match the legacy flat-key behavior
- [ ] `polar_tick_labels` still maps category→label for pie/radar
- [ ] A polar child (if any) renders through the same `_draw_polar_frame`
- [ ] Full existing suite stays green (pie/radar parity)

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `tests/test_axis_format.py` (polar frame parity)
- `tests/test_pie.py` / `tests/test_radar.py` (light updates if assertions change)
