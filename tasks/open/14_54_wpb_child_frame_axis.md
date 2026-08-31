# WP-B: Unified `_draw_frame` entry + cartesian/ternary drawers on AxisFormat

**Status**: open
**Phase**: 14.54
**Depends on**: 14_54_wpa_axis_format_model.md

## Description

Introduce a **single frame-drawing entry point**, `_draw_frame(ax, spec,
matrix)`, that **both** the top-level path and the child path call with the same
signature. It dispatches on the spec's `coord` type to the per-coordinate frame
drawers, all of which consume the shared `AxisFormat` (from WP-A) instead of
ad-hoc flat `settings` keys. This is the "same function calls + same formatting
spec" core of the unification.

`_draw_frame` replaces `_draw_implied_frame` (which only handled children) and
becomes drawable for a top-level spec too (identity/`None` matrix → local =
world).

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- Replace `_draw_implied_frame(ax, child)` with:
  ```python
  def _draw_frame(ax, spec: FigureSpec, matrix=None):
      """Draw the frame for *spec*, stamped by *matrix* (None/identity → local=world).

      Dispatches on coord type. Both top-level and child paths call this.
      """
      matrix = matrix if matrix is not None else np.eye(3)
      axis = parse_axis_settings(spec.settings, spec.coord)
      if isinstance(spec.coord, TernaryCoord):
          _draw_ternary_frame(ax, axis, matrix, spec.coord)
      elif isinstance(spec.coord, CoordCartesian) and "xlim" in spec.settings and "ylim" in spec.settings:
          _draw_cartesian_axis(ax, axis, matrix)
      elif isinstance(spec.coord, CoordPolar):
          _draw_polar_frame(ax, axis)  # WP-C
      # else: no frame
  ```
- `_draw_cartesian_axis(ax, axis, matrix)` — change signature to take a parsed
  `AxisFormat`:
  - Read `axis.limits`, `axis.grid_step or 0.2`, `axis.tick_step or axis.grid_step or 0.2`, `axis.label_policy`, `axis.title`.
  - Apply `axis.tick_format` to primary/secondary tick labels (`f"{tx:{axis.tick_format}}"`).
  - Use `axis.grid_style`, `axis.frame_linewidth`, `axis.tick_fontsize`, `axis.label_fontsize`, `axis.title_fontsize`, `axis.label_offset` instead of hardcoded values.
  - Keep `parse_secondary_settings` for secondary axes; pass the parsed axis's `tick_step`/`label_policy` as secondary defaults.
  - Defaults (via `AxisFormat`) reproduce the current custom-frame look, so EXISTING child output is unchanged.
- `_draw_ternary_frame(ax, axis, matrix, coord)` — same refactor: take `AxisFormat`; read `label_policy`/`title`/`tick_format`/font sizes; ion names/reversal keep coming from `coord` (unchanged).

## Acceptance criteria

- [ ] `_draw_frame` is the single entry used by BOTH top-level (WP-D) and children; no other path draws a frame
- [ ] `_draw_cartesian_axis`/`_draw_ternary_frame` render identically to today for existing child specs (defaults preserved)
- [ ] `tick_format` changes numeric tick label output without touching other artists
- [ ] Secondary axes inherit `tick_step`/`label_policy` from the parsed `AxisFormat`
- [ ] `debug_piper_axes.py` text/line counts unchanged (no regression for children)

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `tests/test_axis_format.py` (frame parity)
