# Phase 14.59: Remove StiffCoord and the deprecated PiperCoord

**Status**: open
**Phase**: 14.59
**Dependencies**: `14_59_wp4_stiff_template_cartesian` (template no longer uses `StiffCoord`)

## Description

Delete the `StiffCoord` coordinate type now that the stiff diagram is expressed
as a `CoordCartesian` figure, and delete the deprecated `PiperCoord` class
(kept only for backward-compat import/serialization; no renderer path remains).
`CoordFlipped` / `CoordFixed` are NOT deprecated and stay unchanged.

Removes all renderer special-casing for stiff: the dedicated `_render_stiff`
path, its frame/scale helpers, the `render()` / `supports()` isinstance
dispatch, and the `stiff=` branch in the area handler.

## Changes

### `src/geofig_engine/core/coord.py`

- Delete `StiffCoord` (and its now-unused constant params) and `PiperCoord`.
- Keep `Coord`, `CoordCartesian`, `CoordFlipped`, `CoordFixed`, `CoordPolar`,
  `TernaryCoord`, `TERNARY_HEIGHT`, `ternary_project` untouched.

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- Delete `_render_stiff`, `_draw_stiff_frame`, `_draw_stiff_scale`.
- Remove the `isinstance(spec.coord, StiffCoord)` dispatch in `render()` and the
  corresponding branch in `supports()`.
- Remove `StiffCoord` from the coord import.

### `src/geofig_engine/renderers/matplotlib/handlers.py`

- Remove the `stiff=` kwarg and `ax.fill` special case from
  `_draw_areas_grouped` / `render_area` (superseded by `render_polygon` /
  `GeomPolygon` from `14_59_wp3_geom_polygon`); drop the `StiffCoord` import.
  `GeomArea` then renders as below-a-line `fill_between` only (polar ring
  branch unchanged).

### `src/geofig_engine/serialize/converters.py`

- Remove the `"stiff"` and `"piper"` coord conversion branches and their
  imports. Unknown coord names still raise `ValueError`.

## Acceptance criteria

- [ ] No references to `StiffCoord` or `PiperCoord` remain in `src/`
- [ ] `import geofig_engine.core.coord` imports cleanly (no dangling names)
- [ ] No `stiff`/`piper` coord branches remain in converters or renderer
- [ ] `CoordFlipped` / `CoordFixed` still serialize and render (unchanged)
- [ ] `mypy`/typecheck clean (no unused imports)

## Files

- `src/geofig_engine/core/coord.py`
- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `src/geofig_engine/renderers/matplotlib/handlers.py`
- `src/geofig_engine/serialize/converters.py`