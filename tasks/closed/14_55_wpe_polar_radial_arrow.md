# WP-E: Polar radial axis arrow (`_draw_polar_frame`)

**Status**: complete
**Phase**: 14.55
**Dependencies**: `14_55_wpb_axis_arrow_helper.md`

## Description

Wire the `axis_arrows` setting into the polar frame `_draw_polar_frame(ax,
axis, spec)` (currently at `renderer.py:903`). When enabled, draw a direction
arrow representing the **radial axis** — the arrow runs outward from the
center/heart in the direction of increasing radius `r` (matplotlib polar: `r`
grows outward from the center).

Polar axes use matplotlib's **native polar projection** (there is no local-space
matrix stamping here — the frame decorates `ax` directly, unlike cartesian/ternary
which use `_apply_matrix_pts`). So the polar arrow should be drawn as a standard
`ax.annotate` in data space (from `(theta, r_lo)` to `(theta, r_hi)` along a
chosen reference angle, e.g. a vertical/`0`-radial ray, or parallel to an edge),
pointing outward (ascending `r`), with the WP-B helper adapted or called with an
identity/`None` matrix (the helper must tolerate a matrix that is already
identity — the WP-B signature already defaults to a world-stamp that degenerates
to identity for polar).

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py` — `_draw_polar_frame`

- Read the effective flag: `arrows = axis.show_arrows()`.
- When `arrows`:
  - Call `_draw_axis_arrow` on the native polar `ax`, with the matrix treated as
    identity (polar has no affine stamp). Anchor at a reference radius
    `r = axis.effective_polar_step`-based low end to the outer `r` range (or the
    axis limit), pointing outward.
  - `local_vec` is the radial tangent at the chosen reference angle so any label
    (none by default) would rotate along the ray.
- Position the arrow clear of the polar spine/tick labels (offset outward or at
  the chosen ray) so it reads cleanly.
- Arrows only when `axis.show_arrows()`; default off ⇒ polar output unchanged
  when the setting is absent.

## Acceptance criteria

- [x] Polar with `axis_arrows: true` renders one radial arrow pointing outward (increasing `r`)
- [x] Polar with `axis_arrows: false`/absent renders no arrow (existing output unchanged)
- [x] Respects the polar `options` toggles that hide radial ticks/spine — the arrow is independent of those toggles
- [x] Works with matplotlib's native polar projection (data-space `annotate`, no affine stamp)
- [x] Existing polar tests (pie/radar, `_draw_polar_frame` toggles) still pass

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
