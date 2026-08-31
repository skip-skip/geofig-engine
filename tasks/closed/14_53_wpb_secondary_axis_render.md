# WP-B: Frame tick-label rendering for secondary axes

**Status**: open
**Phase**: 14.53
**Depends on**: 14_53_wpa_secondary_axis_model.md

## Description

Extend `_draw_cartesian_axis` in the matplotlib renderer to draw secondary-axis
tick labels on the frame's top edge (secondary x) and right edge (secondary y),
deformed by the same `matrix` as the primary bottom/left ticks. Transforms are
applied identically: local-space anchors passed through `_apply_matrix_pts`,
rotated via `label_rotation`.

## Changes

- `src/geofig_engine/renderers/matplotlib/renderer.py`
  - After the existing bottom-edge (primary x) and left-edge (primary y) tick
    loops in `_draw_cartesian_axis`, add:
    - Top-edge loop (secondary x): for each secondary tick value, compute the
      local x via the linear mapping, place text at `(local_x, y1 + d)` — mirror
      of the bottom edge — using the secondary `label_policy`.
    - Right-edge loop (secondary y): text at `(x1 + d, local_y)` — mirror of the
      left edge.
  - Guard both loops on the presence of the secondary settings declarations
    (opt-in; no behavior change for existing cartesian frames without them).
  - Reuse `d`, `fontsize=5`, `clip_on=False`, corner-avoidance conventions.
  - Optionally draw the secondary `label` as a world-side rotated axis title on
    the top/right.

## Design notes

- Secondary labels are text artists only (like primary); they must NOT affect
  world limits (existing `_children_world_limits` uses data + frame corners only,
  so no change needed — just confirm).

## Verification

- [ ] Secondary x ticks appear along the top edge, reversed when `range` is reversed
- [ ] Secondary y ticks appear along the right edge, reversed when `range` is reversed
- [ ] Text count in `debug_piper_axes.py`/`test_diamond_frame_renders` updates accordingly

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `tests/test_linked_render.py` (frame tests)
