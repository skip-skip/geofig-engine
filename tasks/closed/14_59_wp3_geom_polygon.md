# Phase 14.59: GeomPolygon geometry type

**Status**: complete
**Phase**: 14.59
**Dependencies**: `14_58` (piper charge labels)

## Description

Add a dedicated `GeomPolygon` geometry type for closed filled polygons (e.g. the
Stiff diagram loop). `GeomArea` is intentionally **not** modified — it remains a
separate feature defined as the area *below a function/line*
(`ax.fill_between(x, y, 0)`). The closed-polygon path currently achieved by the
`StiffCoord`-special-cased `ax.fill` branch in the area handler becomes a
first-class geom; after WP5 removes `StiffCoord` the Stiff polygon renders through
the normal cartesian pipeline.

This WP is independent of WP1/WP2 and can proceed in parallel.

## Changes

### `src/geofig_engine/core/geom.py`

- Add `GeomPolygon(Geom)` following the `GeomBox` pattern (fill via channels,
  outline via validated geom params):
  - `name = "polygon"`
  - `required_channels = ("x", "y")`, `optional_channels = ("color", "alpha")`
    — `color` is the **fill** color, `alpha` the fill alpha (constant values in
    the visual mapping).
  - Outline params (validated in `__init__` via `object.__setattr__`):
    - `edgecolor: str = "black"`
    - `edgealpha: float | None = None` (None = no override)
    - `edgewidth: float = 0.5`
    - `edgestyle: str = "-"` — validated against the string set
      `{"solid", "dashed", "dashdot", "dotted", "-", "--", "-.", ":"}`;
      anything else raises `ValueError`.

### `src/geofig_engine/renderers/matplotlib/handlers.py`

- Add `render_polygon(ax, layer_spec, order, coord=None)`:
  - `ax.fill(x, y, facecolor=color, alpha=alpha, edgecolor=params.edgecolor, linewidth=params.edgewidth, linestyle=params.edgestyle)`
  - `ax.fill` auto-closes the loop; vertices are the `x`/`y` series in trace
    order (last point need not equal the first).
  - Constant fill color only for now (Stiff is single-sample); multi-series
    color grouping is a future extension.

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- Import `render_polygon` and register `"polygon": render_polygon` in
  `_GEOM_HANDLERS` (`renderer.py:48`); `supports()` picks the geom up
  automatically via the registry.

### `src/geofig_engine/serialize/converters.py`

- Add `GeomPolygon` branches to `geom_to_dict` (emit only non-default outline
  params, per the existing omission style) and `geom_from_dict`.

## Acceptance criteria

- [ ] `GeomPolygon()` validates required/optional channels; bad `edgestyle` raises `ValueError`
- [ ] `render_polygon` produces a single closed filled polygon via `ax.fill`
- [ ] Outline `edgecolor` / `edgealpha` / `edgewidth` / `edgestyle` applied
- [ ] Fill `color` / `alpha` channels honored (constant values)
- [ ] `GeomArea` behavior unchanged (`fill_between` below-a-line only)
- [ ] `GeomPolygon` params serialize/round-trip (non-defaults preserved)

## Files

- `src/geofig_engine/core/geom.py`
- `src/geofig_engine/renderers/matplotlib/handlers.py`
- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `src/geofig_engine/serialize/converters.py`
- `tests/test_polygon.py` (new) or existing area/geom tests