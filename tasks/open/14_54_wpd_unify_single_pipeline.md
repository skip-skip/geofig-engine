# WP-D: Unify the top-level single path with the child pipeline

**Status**: open
**Phase**: 14.54
**Depends on**: 14_54_wpb_child_frame_axis.md

## Description

Today `_render_single` renders a top-level spec on native matplotlib axes via
`_apply_coord_transform` + `_render_axes` + `_apply_settings`, and **does not**
draw a custom frame (top-level ternary draws no frame at all). Children render
through `_apply_child_coord_transforms` + `_draw_frame` + `_render_axes`,
with a shared axes, per-child affine stamping, and world-limit computation.

Unify so the **top-level single path uses the exact same functions and
formatting spec as children** — treating the top-level spec as one child with an
implicit identity transform (local = world). This makes top-level cartesian and
**ternary render via `_draw_frame`**, so a top-level ternary spec finally draws a
triangle. Native-axes mutators for cartesian/ternary are retired in favor of
`_draw_frame` + `AxisFormat`.

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- In `render()` dispatch, route single non-polar/non-stiff specs through a
  shared `_render_like_children` style path (identity transform, one panel).
- Reuse the child machinery for the top-level spec:
  - `_apply_child_coord_transforms` (coord transform + secondary remap) with an
    identity `matrix`.
  - `_draw_frame(ax, spec, matrix=None)` for the frame (WP-B) — draws the
    cartesian or ternary custom frame; **top-level ternary now draws its
    triangle, grid, ticks, and ion arrows**.
  - `_render_axes(..., layer_affine=identity)` so data stamps identically to a
    child.
  - Compute world limits via the same `_children_world_limits`-style logic
    (identity matrix), set `ax.set_aspect("equal")` + `ax.axis("off")` where the
    frame is drawn.
- Retire the native-axes formatting responsibilities of `_apply_settings` for
  cartesian/ternary (title, x/ylabel, x/ylim, x/yscale, grid, time_format move
  into `_draw_frame` via `AxisFormat`). Keep `_apply_settings` only where a
  native axes is still used (polar projection handling — reduced; see WP-C).
- Polar continues to use the polar Axes projection (matplotlib requirement) but
  routes formatting through `_draw_frame` → `_draw_polar_frame` (WP-C).

## Acceptance criteria

- [ ] A top-level `TernaryCoord` spec renders the same framed triangle (outline, grid, 20/40/60/80 ticks, ion arrows) as a child ternary
- [ ] A top-level cartesian spec with `settings["axis"]` renders through `_draw_frame`, not native ticks
- [ ] Appearance is preserved for existing templates (defaults preserved; only light test updates — see WP-I)
- [ ] Single and child paths call the same `_draw_frame` + `_render_axes` + world-limit code
- [ ] Full existing suite passes (with the light test updates in WP-I)

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `tests/test_axis_format.py` (top-level ≡ child parity, ternary frame)
- Affected single-template tests (light updates, WP-I)
