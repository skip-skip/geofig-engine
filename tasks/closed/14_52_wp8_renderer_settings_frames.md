# WP8: Renderer frame-drawing reads `settings`

**Status**: open
**Phase**: 14.52
**Depends on**: 14_52_wp7_remove_frame_config_field.md

## Description

Update the implied-frame logic in the renderer to read frame hints from `child.settings`
instead of `child.frame_config`. Frame keys (`xlim`/`ylim`/`grid_step`/`tick_step`/
`label_policy`/`title`) mean **local-space frame bounds** for a child, not matplotlib axis
limits. Child settings must feed ONLY the frame-drawing logic, not the generic
`_apply_settings` handler.

## Changes

- `src/geofig_engine/renderers/matplotlib/renderer.py`
  - `_draw_ternary_frame(ax, matrix, coord, frame_config)` -> rename param to `settings`
  - `_draw_cartesian_axis(ax, matrix, frame_config)` -> rename param to `settings`
  - `_child_local_bbox(child)`: read `xlim`/`ylim` from `child.settings`
  - `_draw_implied_frame(ax, child)`: dispatch cartesian frame when
    `"xlim" in child.settings and "ylim" in child.settings`
  - Confirm `_apply_settings` is NOT called for children (unchanged)

## Verification

- [ ] Ternary/cartesian frames render with settings-provided title/bounds/steps
- [ ] Diamond still renders correct frame/grid/labels with bounds in settings

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
