# WP-B: Shared axis-direction arrow helper (renderer)

**Status**: complete
**Phase**: 14.55
**Dependencies**: `14_55_wpa_axis_arrows_model.md`

## Description

Introduce a single, reusable matplotlib arrow helper so every framed-axis
drawer (cartesian, secondary, ternary, polar) draws a direction arrow the same
way. The helper generalizes the current ternary-only, hardcoded arrow block
(which lives inside `_draw_ternary_frame` and fuses the arrowhead style with a
`reverse` handedness flag).

Core rule: the arrow is **parallel to the axis** and **points toward
increasing values**, i.e. from the lower numeric endpoint to the higher numeric
endpoint of the axis's value range — regardless of how the range was declared
(handedness, or a reversed/descending `limits` like `(100, 0)`). This is what
"the axis values must be sorted" means: the arrow direction always follows
numeric ascending order.

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py`

Add a module-level helper, e.g.:

```python
def _draw_axis_arrow(ax, matrix, start_local, end_local, local_vec,
                     style="<|-", lw=1.0,
                     label=None, label_fs=None, label_policy="upright"):
```

- `start_local` / `end_local`: the axis's low-value and high-value local-space
  endpoints (already ordered low→high by the caller per the sorted rule).
- Uses `_apply_matrix_pts(matrix, [...])` to map both endpoints to world
  space for `ax.annotate(...)` (arrow body faint/solid + arrowhead at the
  high-value end), consistent with how the frame geometry is already stamped.
- `local_vec`: the local tangent direction of the axis, passed to
  `label_rotation(local_vec, matrix, label_policy)` to align an optional label
  parallel to the transformed edge (reuse from `core/link.py`).
- `style`: arrowhead style (e.g. `"<|-"` pointing at the high-value end). The
  caller supplies the endpoint order so the style stays constant; no `reverse`
  flag needed.
- Offset placement (parallel & clear of the axis/tick labels) mirrors how the
  frame drawers already offset tick labels / labels (e.g. the cartesian
  `label_offset` `d`, and the ternary `offset`). The helper should accept a
  small perpendicular offset parameter (or the caller places the endpoints).

Keep the helper focused and matplotlib-only (the frame drawers are already in
the renderer).

## Acceptance criteria

- [ ] `_draw_axis_arrow` renders an `ax.annotate` with an arrowhead at the high-value endpoint
- [ ] Endpoints are world-stamped through `matrix` identically to frame geometry
- [ ] Optional label uses `label_rotation(local_vec, matrix, policy)` so it runs parallel to the transformed edge (for `"parallel"`) or stays upright (for `"upright"`)
- [ ] No `reverse` handedness flag; direction is caller-chosen by endpoint order
- [ ] Replaces the ternary-only `_arrow`/style logic when integrated in WP-D (no duplicate arrow code left)

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
