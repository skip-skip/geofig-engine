# Phase 18.2: DEM elevation contours for the site map template

**Status**: open
**Phase**: 18.2
**Version target**: v0.3.1+ (patch — bump decision deferred to the epic review WP)
**Dependencies**: none (phase overview)

## Description

Pull the **M2-deferred DEM contour geom** forward and wire it into the
`site_map` template (`ARCHITECTURE.md` line 80: "| DEM contour / stream
geoms | deferred |"; line 354: "contour geom | DEM contour lines";
`ROADMAP.md` line 455: "**Deferred to M2:** DEM contour, stream geoms").

Reference implementation: `../geochemmapper.py` `MapBuilder.download_dem`
(l.455) + `add_contours` (l.767):

- map bounds → EPSG:4326 via pyproj; **10% lon/lat buffer**
- **cache keyed by integer bbox** (`./cache/dem/dem_{minx}_{miny}_{maxx}_{maxy}.tif`)
- download via the `elevation` package; rioxarray-read, reproject, save
- `levels = np.arange(np.nanmin(z), np.nanmax(z), interval)`;
  `ax.contour(x, y, z, levels, ...)` — defaults `interval=10`,
  `color="white"`, `linewidth=0.5`, `alpha=0.6`

**Decisions locked (with the requester):**

- **DEM source: AWS Terrain Tiles (terrarium)** —
  `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`,
  decoded `alt = (r*256 + g + b/256) - 32768`; `requests` + `Pillow` only
  (both already used by the wp14 basemap module) — **no GDAL/rasterio/
  rioxarray/elevation package**, no new required dependency. The bbox →
  EPSG:4326 clamp + 10% buffer + extent/bbox-keyed cache semantics of the
  old geomapper are preserved, but the raster is stitched from XYZ tiles
  (mirroring `renderers/matplotlib/basemap.py`) instead of `elevation.clip`.
- **Default state: on.** The contour layer is part of the `site_map`
  recipe and DEM fetch is lazy per render (old-geomapper parity). Offline/
  HTTP failure degrades to a `UserWarning` + empty contour layer (the wp14
  basemap degrade pattern). Disable with `settings={"contours": None}` or
  `{"contours": {"enabled": False}}`.
- **Styling: constant** — single color/width/alpha for every level
  (old-geomapper look); no level channel, no legend interplay in M1.
- **Projection:** contour polylines are extracted **in lon/lat** from the
  tile grid; `CoordGeo.transform_visual_mapping` already projects each
  layer's x/y into a non-WGS84 `crs`, so no raster reprojection is needed
  (a simplification vs. the old `rio.reproject`).

Rendering reuses the shipped NaN-separated multipath machinery
(`StatParticleOverlay(mode="contours")` frame shape + `render_boundary`
handlers.py:1020 — open paths at NaN).

## Phase-level acceptance criteria

- [ ] `render_template(data, template="site_map")` renders elevation
      contour lines by default (lazy DEM fetch, bbox-keyed tile cache),
      painted above the basemap and below the boundary ring
- [ ] `settings={"contours": None}` (or `{"enabled": False}`) renders the
      previous contour-free figure with no DEM fetch attempt
- [ ] Contour lines are drawn under a constant style with old-geomapper
      defaults (`interval=10` m, white, `linewidth=0.5`, `alpha=0.6`);
      the `level`/color machinery is not extended in M1
- [ ] Offline/HTTP failure or invalid DEM data is non-fatal:
      `UserWarning` + empty contour layer (render proceeds)
- [ ] No new required dependency (`requests` + `Pillow` only); terrarium
      tiles work without the `[geo]` extra (closed-form Web-Mercator math,
      copied into `io/dem.py`)
- [ ] Non-WGS84 `CoordGeo` `crs` projects the lon/lat contour polylines
      via the existing `transform_visual_mapping` path
- [ ] Test suite never touches the network (stubbed `fetch_dem` /
      `dem_source` seam + fake sessions); existing `site_map` render tests
      pin `settings={"contours": None}` where they assert line counts
- [ ] Full suite green (baseline 1392 passed / 6 skipped, 0 warning skips)
      after every WP
- [ ] Commits labeled `geofig-engine: <scope> → v0.3.1` (target finalized
      at epic review)

## Ticket map

| Ticket file | Scope | Depends |
| --- | --- | --- |
| `18_2_wp1_dem_io.md` | `io/dem.py`: terrarium decode/stitch/cache/fetch + degrade | epic (context) |
| `18_2_wp2_stat_geom_contour.md` | `GeomContour` + handler + `StatContour` (levels → NaN-separated x/y) | `18_2_wp1_dem_io` |
| `18_2_wp3_template_wiring.md` | default-on recipe wiring, settings, docs, example, stale-test updates | `18_2_wp2_stat_geom_contour` |
| `18_2_wp4_tests_docs_roadmap.md` | `test_dem.py` + contour coverage + ROADMAP/ARCHITECTURE un-defer | `18_2_wp3_template_wiring` |

## Files

- `src/geofig_engine/io/dem.py` (new)
- `src/geofig_engine/core/geom.py`
- `src/geofig_engine/templates/site_map.py`
- `src/geofig_engine/renderers/matplotlib/renderer.py` (handler registration)
- `tests/test_dem.py` (new), `tests/test_site_map.py`, `tests/test_contour.py` (new)
- `examples/site_map_example.py`, `docs/api/engine.md`, `ARCHITECTURE.md`,
  `ROADMAP.md`
- this ticket list (`tasks/open/18_2_*.md`)