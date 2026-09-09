# Phase 14.59: Majortick renderer

**Status**: complete
**Phase**: 14.59
**Dependencies**: `14_59_wp8_majortick_axis_model`, `14_59_wp9_majortick_secondary`

## Description

Generalize the nub helper in `_draw_cartesian_axis` and wire majorticks into
all four edges of a drawn cartesian frame.

Replace `_draw_tick_marks` with `_draw_majorticks(ax, matrix, positions,
edge, length, offset, width, color)` where `edge` is one of
`"bottom"`/`"top"`/`"left"`/`"right"`. Each edge defines an interior unit
vector:

- bottom `(0, +1)`, top `(0, -1)`, left `(+1, 0)`, right `(-1, 0)`

For a tick position the two endpoints are:

- interior tip = base + `offset * length * dir`
- exterior tip = base - `(1 - offset) * length * dir`

Both endpoints are stamped through `_apply_matrix_pts(matrix, ...)` and drawn
as a 2-point `ax.plot(..., linewidth=width, color=color, zorder=2)`.

Call the helper at every label loop, gated on the effective `majortick_length
is not None`:

- primary x named ticks and numeric xs -> bottom edge
- primary y named ticks and numeric ys (collect ys like xs) -> left edge
- secondary x `sec.tick_coordinates()` local positions -> top edge
- secondary y local positions -> right edge

## Files to modify

- `src/geofig_engine/renderers/matplotlib/renderer.py`

## Acceptance criteria

- [ ] `_draw_tick_marks` replaced by `_draw_majorticks` with per-edge
      interior vectors
- [ ] Nubs drawn for named AND numeric primary x/y ticks
- [ ] Nubs drawn for secondary x (top) and secondary y (right) edges
- [ ] `majortick_offset` 0/0.5/1 place the edge at exterior/bisected/interior
- [ ] Effective values inherit through the secondary (`None` -> frame level)
- [ ] No nubs when `majortick_length` is unset (piper unchanged)
- [ ] Ruff clean on modified file (no new findings vs baseline)