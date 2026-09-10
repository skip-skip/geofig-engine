# Phase 15: CoordGeo + geo geoms + handlers + [geo] extra

**Status**: open
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_wp1_provider_contract`, `15_wp3_figure_generator`

## Description

Add geographic rendering support (`ARCHITECTURE.md` §8 coord list entry
"CoordGeo", §13 renderer "geometry/image handlers", M1 roadmap "Required geo
support"). **Basemap tiles, DEM contour, and stream geoms are deferred to M2**
— this ticket provides point/boundary/label/image-inset geoms and a declarative
geo coordinate. The `[geo]` optional extra (`pyproject.toml`) carries the
heavier geo deps; the base install must still import and render a projection-
free fallback map.

## Changes

### `src/geofig_engine/core/coord.py`

- `CoordGeo(Coord)` — declarative geo coordinate: `crs` (default WGS84),
  optional `bounds`/`bounds_crs`, `aspect`; transform only when the `[geo]`
  projection backend is importable, otherwise falls back to an identity
  (lon/lat → x/y) projection with a clear note. Serialization round-trip via the
  coord converter (`coord_from_dict`).

### `src/geofig_engine/core/geom.py`

- Geo geoms following the existing `Geom` pattern (required/optional channels
  validated in `__init__`):
  - `GeomSitePoint` — `x`/`y` (lon/lat), `color`/`shape`/`size` mapping, group
    labels for legends
  - `GeomBoundary` — closed polygon outline from a `x`/`y` path (reuses
    `GeomPolygon` edge machinery where applicable)
  - `GeomLabel` — text at `x`/`y` with `label` channel + size/rotation params
  - `GeomImageInset` — `OffsetImage`-style inset at an anchor point: `x`/`y`
    anchor + an `image` channel resolving to a 2D/3D array, `zoom` param
- Update the geom converter (serialize) branches for the new geoms.

### `src/geofig_engine/renderers/matplotlib/handlers.py`

- Geometry/image handlers: `render_site_point`, `render_boundary`,
  `render_geo_label`, `render_image_inset` (matplotlib `inset_axes`/
  `OffsetImage`); register in `_GEOM_HANDLERS` (`renderer.py`) so `supports()`
  picks them up automatically. Handlers respect `Coord`/`Facet`; unsupported
  combos return `NotImplemented`.

### `pyproject.toml`

- Add `[project.optional-dependencies] geo = [...]` (projection lib, optional
  shapefile/geojson reader — concrete pins chosen by implementer); base
  `dependencies` unchanged.

## Acceptance criteria

- [ ] `CoordGeo` imports without geo extras; renders an identity-projection map
      fallback; full projection path activates only with `[geo]` installed
- [ ] Each geo geom validates its channels; bad channels raise `ValueError`
- [ ] `GeomSitePoint`/`GeomBoundary`/`GeomLabel`/`GeomImageInset` render through
      the new handlers and are registered in `_GEOM_HANDLERS`
- [ ] Geo geoms serialize/round-trip (non-default params preserved)
- [ ] With `[geo]` absent, skip (not fail) the projection-dependent tests
  (mirror the cv2 skip pattern in geochemmodel)
- [ ] Tests extended in `tests/test_coord.py`, `tests/test_geom.py`,
      `tests/test_renderers.py`
- [ ] Committed as a single commit (`geofig-engine: CoordGeo + geo geoms → v0.2.0`); full suite green

## Files

- `src/geofig_engine/core/coord.py`
- `src/geofig_engine/core/geom.py`
- `src/geofig_engine/serialize/converters.py`
- `src/geofig_engine/renderers/matplotlib/handlers.py`
- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `pyproject.toml`
- `tests/test_coord.py` / `tests/test_geom.py` / `tests/test_renderers.py`