# WP-D: Data twin-axis (plot a second series against a secondary axis)

**Status**: open
**Phase**: 14.53
**Depends on**: 14_53_wpa_secondary_axis_model.md

## Description

Allow a layer to plot data against a secondary axis (matplotlib twin-axis style)
by mapping a secondary data channel (`x2`/`y2`) through the linear secondary→primary
mapping before rendering, so positions land in the correct place on the shared
child frame and deform with the same `LinkTransform` as primary data.

## Changes

- `src/geofig_engine/core/coord.py` and/or renderer normalization
  - Extend the child data path so a layer whose visual mapping carries `x2`/`y2`
    (secondary units) has those channels rewritten into local `x`/`y` using the
    secondary axis mapping for that child.
  - Wire into `_apply_child_coord_transforms` / `_render_axes` so twin-axis layers
    flow through the existing stamp-with-matrix path unchanged.
- World limits: since twin-axis positions become local `x`/`y`, they naturally
  expand `_children_world_limits` — confirm no separate handling is required.
- `x2`/`y2` are already in the channel vocabulary (`utils/typing.py`), so no new
  channel plumbing is needed; document the convention.

## Design notes

- This is the most involved WP (first time a coord maps a *secondary* channel into
  local position). Keep validation clear: a `x2`/`y2` channel requires the
  corresponding `secondary_x`/`secondary_y` declaration, else raise a clear error.

## Verification

- [ ] A layer with `y2` data lands where the secondary→primary mapping predicts
- [ ] Region without a matching secondary declaration raises a clear error
- [ ] Series, not just the frame, deform with the child's transform

## Files

- `src/geofig_engine/core/coord.py`
- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `tests/test_secondary_axis.py` (or `tests/test_linked_render.py`)
