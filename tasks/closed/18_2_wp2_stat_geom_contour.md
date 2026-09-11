# Phase 18.2: `GeomContour` + `StatContour`

**Status**: complete
**Phase**: 18.2
**Version target**: v0.3.1+ (patch — bump decision deferred to the epic review WP)
**Dependencies**: `18_2_wp1_dem_io`

## Description

Declarative surface for DEM contour lines: a `GeomContour` mark (name
`"contour"`, reusing the boundary path-rendering machinery) and a
`StatContour` that downloads/loads the DEM for the frame's lon/lat extent
(via `io.dem.fetch_dem`), extracts contour polylines with
`matplotlib.contour`, and emits a NaN-separated `x`/`y` frame — the exact
frame shape `render_boundary` already draws as open multipart paths
(handlers.py:1020, the `StatParticleOverlay(mode="contours")` idiom).

## Changes

### `src/geofig_engine/core/geom.py`

- New `GeomContour` (name `"contour"`), field-for-field mirrors
  `GeomBoundary`: `edgecolor="white"`, `edgealpha=None`, `edgewidth=0.5`,
  `edgestyle="-"` (old-geomapper `add_contours` defaults);
  `required_channels=("x", "y")`, `optional_channels=("color", "alpha")`.
- Channel-note in the docstring: M1 is constant-style — the per-level
  `level` channel is intentionally **not** added (color/width/alpha are
  geometry params applied to the whole line set).

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- Register `"contour"` → `render_boundary` in the geom-handler map (one line,
  same dispatch as `"boundary"`).

### `src/geofig_engine/templates/site_map.py`

- New `StatContour(interval: float = 10, dem_source: Callable | None = None,
  dem_bounds: tuple[float, float, float, float] | None = None)`:
  - `compute(data)`:
    - coordinates detected from the provider frame like `StatSiteMap`
      (`X_CANDIDATES`/`Y_CANDIDATES`); missing coordinates → empty
      `x`/`y` frame (contour layer renders nothing; no DEM fetch);
    - bbox = `(min(lon), min(lat), max(lon), max(lat))` of the provider
      coordinates, or `dem_bounds` when given; empty frame (0 rows) →
      empty `x`/`y` frame;
    - DEM loaded from `dem_source(bbox)` when provided (**test/inject
      seam**), else `fetch_dem(*bbox_buffered, interval=interval)` from
      `io.dem`;
    - **fetch failure / all-NaN DEM** → `warnings.warn(UserWarning,
      "site_map contours unavailable: ...")` and return the empty
      `x`/`y` frame (non-fatal, mirrors the basemap degrade);
    - otherwise extract polylines:
      `levels = np.arange(np.nanmin(z), np.nanmax(z), interval)`
      (old-geomapper parity; `interval` must be > 0 — `ValueError`);
      `cs = matplotlib.contour.QuadContourSet(fig, lon, lat, z,
      levels=levels)` or the equivalent low-cost path
      (`contour.contour` on a throwaway figure is fine — no draw);
      flatten `cs.allsegs` per level into a long-form frame
      `{"x": [...], "y": [...]}` where each closed/open polyline is
      NaN-separated from the next (trailing separator trimmed, matching
      `StatParticleOverlay._contours_frame`).
  - `__init__` validation: `interval` positive real; `dem_source` callable
    or None; params recorded for serialization like `StatSiteMap`.
- `GeomContour`/`render_boundary` constraints: the frame must stay
  index-aligned with `FigureSpec.data`? **No** — like `StatSiteMap`
  boundary/labels modes, the contour frame is an independent row-filtered
  series per layer; document that a `mapping` override on the contour
  layer's x/y is an M1 edge (row sets are stat-owned).

## Acceptance criteria

- [ ] `GeomContour` is exported/registered with name `"contour"`, renders
      through the boundary handler (open NaN-separated multipaths); constant
      style from geometry params
- [ ] `StatContour.compute` produces a NaN-separated `x`/`y` frame whose
      polylines lie on the requested DEM, with contour levels at multiples
      of `interval` within `[nanmin, nanmax)` (old-geomapper parity)
- [ ] Missing/invalid coordinates, empty frame, fetch failure, or all-NaN
      DEM → empty `x`/`y` frame (`len == 0`); fetch failure warns
      `UserWarning` and never raises
- [ ] `dem_source` seam injectable (tests pass a synthetic DEM callable;
      no network in the test suite)
- [ ] `interval` validation (`ValueError` for non-positive); stat params
      serializable like `StatSiteMap`
- [ ] Non-WGS84 `CoordGeo` `crs`: contour polylines (lon/lat) flow through
      `CoordGeo.transform_visual_mapping` unchanged in this WP — projection
      handling verified in wp3 or wp4 tests
- [ ] Full suite green after this WP