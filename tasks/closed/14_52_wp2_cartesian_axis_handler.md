# WP2: Generalized cartesian-axis handler

**Status**: open
**Phase**: 14.52
**Depends on**: 14_52_wp1_fluent_link_transform.md

## Description

Replace the special-cased `_draw_diamond_frame` (and its fragile `rotate != 0` dispatch) with a **general cartesian-axis handler** that draws a cartesian child's full axis region (box, grid, tick labels, title) in local space and applies the child's affine to all geometry + data. Text labels stay upright world-side.

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py`

Add `_draw_cartesian_axis(ax, matrix, frame_config)` — generalizes and subsumes `_draw_diamond_frame`, parameterized by local axis bounds read from `frame_config`:

- `xlim`/`ylim` — axis region in local space (default `(0,1)²`)
- `grid_step` (default 0.2) — gridline spacing, both directions
- `tick_step` (default = grid_step) — tick label spacing
- `label_policy` (default `"upright"`)
- `title` — world-side above the box

Draws in local space (geometry stamped with the affine like data; tick/title text placed world-side upright via `_apply_matrix_pts` + `label_rotation`):
- box outline at `xlim × ylim`
- gridlines at `grid_step`
- tick labels along bottom (x) and left (y) edges
- title world-side above

Update `_draw_implied_frame` — remove the `rotate != 0` proxy:
```python
if isinstance(child.coord, TernaryCoord):
    _draw_ternary_frame(ax, matrix, child.coord, child.frame_config)
elif isinstance(child.coord, CoordCartesian) and child.frame_config:
    _draw_cartesian_axis(ax, matrix, child.frame_config)
```
Cartesian children with no `frame_config` draw no frame (preserves existing behavior). A diamond becomes just "a cartesian child with a rotated transform + `frame_config` declaring `[0,100]²` bounds."

Update `_child_local_bbox` — remove `rotate != 0` dependency:
- `TernaryCoord` → triangle
- `CoordCartesian` with `frame_config["xlim"]`/`["ylim"]` → those bounds
- else → unit square

Delete `_draw_diamond_frame`.

## Acceptance criteria

- [ ] `_draw_diamond_frame` deleted
- [ ] `_draw_cartesian_axis` draws box/grid/ticks/title from frame_config bounds in local space
- [ ] `_draw_implied_frame` dispatches by coord type + frame_config presence, not `rotate != 0`
- [ ] Diamond renders identically to before (box, grid, tick labels, title) with `[0,100]²` bounds
- [ ] Cartesian child with no frame_config still draws no frame
- [ ] `_child_local_bbox` no longer checks `rotate`
- [ ] All geometry (data + axis) gets the same affine; text stays upright world-side
- [ ] Full test suite passes (see WP5)

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
