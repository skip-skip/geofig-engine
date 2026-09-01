# WP-K: Wire `x_reversed`/`y_reversed` into cartesian arrows + tick labels (renderer.py)

**Status**: complete
**Phase**: 14.55
**Dependencies**: `14_55_wpi_reverse_flag_model.md`, `14_55_wpj_cartesian_normalize_range.md`

## Description

Apply the reversal flags to the frame so labels and arrows stay consistent with
the declared axis direction. **Rule (user-specified):** an axis arrow always
points in the direction of **increasing data**. Therefore a *reversed* axis
reads its tick labels high→low and its arrow points the opposite way (toward
the low/high-data end) — flipping together with the data and labels.

Today `_draw_cartesian_axis` hardcodes primary arrows to point from
`min → max` (renderer.py:504-515) so they always point ascenting regardless of
declaration order. With normalisation (WP-J) the arrow endpoints are built from
sorted `xlo/xhi`/`ylo/yhi`; this WP makes the `x_reversed`/`y_reversed` flags
swap those endpoints (and reverse the corresponding tick-label value sequence).

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py` — `_draw_cartesian_axis` arrows (498-533)

- **Primary x arrow**: build low/high endpoints from `(xlo, xhi)`. If
  `axis.x_reversed`, swap so the arrowhead lands on the **increasing-data** end
  (i.e. the arrow points from the high-value end back toward the low-value end,
  matching data that itself reads low→high in the frame's reading direction).
- **Primary y arrow**: mirror with `(ylo, yhi)` and `axis.y_reversed`.
- **Secondary arrows** (518-533): secondary axes already point toward increasing
  *secondary* value (`sec.inv(slo) → sec.inv(shi)`). When the linked primary axis
  is reversed, the secondary tick labels (placed via `sec.inv`) and the secondary
  arrow direction must stay consistent with "increasing data" — verify the
  secondary arrow still ends at the increasing-data end of that edge.

### Tick-label value direction

- Primary bottom/left tick labels use the local coordinate value (`_tick_label(tx, ...)`).
  With `x_reversed`, the **reading** is high→low; confirm the displayed numbers
  match the intended reversed reading (the diamond must show which number sits on
  which vertex).

## Acceptance criteria

- [ ] `x_reversed=True` makes the primary x arrow point toward the **decreasing** data end (arrowhead flips vs `False`)
- [ ] `y_reversed=True` mirrors for the primary y arrow
- [ ] Arrows still point toward **increasing data** under reversal (head on the increasing-data end)
- [ ] Reversed primary tick labels read high→low on the bottom/left edges
- [ ] No flag (`x_reversed=False`) keeps the existing ascending behavior — existing arrow tests pass unchanged
- [ ] Secondary arrows/tick labels stay consistent with their linked (possibly reversed) primary axis

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `tests/test_axis_format.py` (arrow-direction reversal coverage)
