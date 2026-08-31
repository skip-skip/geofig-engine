# WP-C: Cartesian frame arrows — x/y + secondary axes (`_draw_cartesian_axis`)

**Status**: complete
**Phase**: 14.55
**Dependencies**: `14_55_wpb_axis_arrow_helper.md`

## Description

Wire the new `axis_arrows` setting into the framed cartesian drawer
`_draw_cartesian_axis(ax, axis, matrix)` (currently at `renderer.py:264`).
When enabled, draw a direction arrow parallel to each cartesian edge and
pointing toward increasing values, using the WP-B `_draw_axis_arrow` helper.

Applies to **all valid cartesian axes**:
- X axis (bottom edge)
- Y axis (left edge)
- Secondary-x axis (top edge)
- Secondary-y axis (right edge) — when the corresponding `secondary_x`/`secondary_y` is declared

Direction rule (per the sorted-values rule): the arrow always points from the
**lower numeric value** to the **higher numeric value** of that axis's range,
regardless of how the range is declared. For the primary axes, derive ascending
order from `axis.xlim` / `axis.ylim` (i.e. sort `x0, x1`; if `x1 < x0` the arrow
still points toward the larger value). For secondary axes, derive it from each
`SecondaryAxis`'s value range in the same way.

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py` — `_draw_cartesian_axis`

- Read the effective flag: `arrows = axis.show_arrows()`.
- When `arrows`:
  - **X axis**: arrow along the bottom edge, offset like the bottom tick labels
    (use the computed `d`/`label_offset`), from `min(x0,x1) → max(x0,x1)` in
    local x at `y0 - d`.
  - **Y axis**: arrow along the left edge, offset like the left tick labels,
    from `min(y0,y1) → max(y0,y1)` in local y at `x0 - d`.
  - **Secondary x** (top): arrow along the top edge when `secondary["x"]` exists,
    direction from that axis's ascending value range, offset above the edge.
  - **Secondary y** (right): arrow along the right edge when `secondary["y"]`
    exists, direction from its ascending value range, offset right of the edge.
- Each arrow uses `_draw_axis_arrow` with the appropriate `local_vec`
  (`(1, 0)` for x/secondary-x, `(0, 1)` for y/secondary-y) so a parallel label
  rotates correctly if later added.
- Arrows are drawn only when `axis.show_arrows()` is true; otherwise `_draw_cartesian_axis`
  output is unchanged (default off ⇒ no regression to existing cartesian output).

## Acceptance criteria

- [x] Framed cartesian with `axis_arrows: true` draws 2 arrows (x + y); with `axis_arrows: false`/absent draws none
- [x] With `secondary_x`/`secondary_y` declared and `axis_arrows: true`, arrows also appear on the top/right edges (4 total)
- [x] Arrow direction points toward ascending numeric values even when limits are declared descending (e.g. `xlim=(100, 0)`)
- [x] Default off — existing cartesian outputs (no `axis_arrows`) are unchanged
- [x] Existing cartesian/piper-diamond tests still pass (unless the piper template opts in — see WP-F)

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
