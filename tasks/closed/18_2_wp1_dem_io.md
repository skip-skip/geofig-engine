# Phase 18.2: terrain-tile DEM module (`io/dem.py`)

**Status**: complete
**Phase**: 18.2
**Version target**: v0.3.1+ (patch — bump decision deferred to the epic review WP)
**Dependencies**: `18_2_epic`

## Description

New self-contained DEM access module replicating the old geomapper's DEM
recipe (`../geochemmapper.py` `download_dem`: bounds → EPSG:4326, 10% lon/lat
buffer, bbox-keyed cache) **without** the `elevation`/GDAL/rasterio stack:
AWS Terrain Tiles (terrarium) XYZ PNGs fetched with `requests` + `Pillow`,
decoded to meters, stitched into a lon/lat grid.

Layering: this is an **io-layer** module — no imports from
`renderers.*` (the wp14 basemap module keeps its own copies of the
closed-form Web-Mercator math; this module carries equivalent local copies so
`io` never depends on a renderer).

## Changes

### `src/geofig_engine/io/dem.py` (new)

- Constants: `TERRARIUM_URL = "https://s3.amazonaws.com/elevation-tiles-prod/"
  "terrarium/{z}/{x}/{y}.png"`, `USER_AGENT`, tile size 256, tile budget
  default, zoom bounds (0–15 for terrarium).
- Closed-form Web-Mercator math (local copies, mirroring basemap.py):
  `lonlat_to_mercator`, `tile_to_lonlat`, `tile_bounds`, mercator-lat inverse
  for per-pixel row/lon grids (lat is non-linear in pixel row — build the
  y-grid from the closed form per row, not linear interpolation).
- `decode_terrarium(image: np.ndarray) -> np.ndarray` — per-pixel
  `alt = (r*256 + g + b/256) - 32768`; decoded `-32768` (nodata/water) →
  `np.nan`; clip to a sane elevation band (e.g. `[-500, 9000]` m).
- `auto_zoom_lonlat(west, south, east, north, interval=10, max_tiles=64,
  max_zoom=15, min_zoom=6)` — smallest zoom whose pixel resolution
  (Web-Mercator meters / 2^zoom) is `<= max(5, interval/3)` m while keeping
  the tile count within `max_tiles`; monotonically decreasing scan high→low.
- `dem_tile_range(west, south, east, north, zoom)` — XYZ index range
  covering the buffered lon/lat bbox (lat clamped to ±85.0511°), inclusive.
- `fetch_dem(west, south, east, north, interval=10, zoom=None, session=None,
  timeout=10.0, cache_dir=None) -> DemGrid`:
  - applies the **10% lon/lat buffer** (old-geomapper parity),
  - resolves zoom (`auto_zoom_lonlat` unless given),
  - fetches missing tiles only; per-tile PNG cache keyed by tile index under
    `dem_cache_dir()` (see below), skipping the cache when the file exists,
  - decodes + stitches each tile into the mosaic, builds the lon/lat grids,
  - returns `DemGrid(lon: np.ndarray, lat: np.ndarray, z: np.ndarray)` —
    2-D lon/lat grids + elevation grid (NaN for nodata/water),
  - raises `TileFetchError` (mirroring basemap.py semantics) when **all**
    tiles fail; **partial** failures warn (`UserWarning`, stacklevel=2) and
    continue with the fetched subset.
- `dem_cache_dir() -> Path` — `GEOFIG_DEM_CACHE` env override, else
  `Path.home() / ".cache" / "geofig_engine" / "dem"`; per-tile files at
  `<cache>/terrarium/{z}/{x}/{y}.png`; module-level test override hook
  (`_DEM_CACHE_DIR` sentinel replaceable in tests).
- Import discipline: `numpy`/`pandas`/`pathlib` at module level only;
  `requests`/`PIL` imported inside functions (lazy) so a pure-offline
  `import geofig_engine.io.dem` succeeds without them.

### Tests (added in this WP; live in `tests/test_dem.py`)

Pure functions first — no network:

- `decode_terrarium` formula (0→-32768→NaN, 128/128/128→-32512, color ramp
  round-trip), nodata handling, clipping.
- Mercator closed forms: `tile_to_lonlat` corner round-trip,
  `lonlat_to_mercator` monotonicity, `tile_bounds` adjacency/ordering,
  latitude clamp.
- `auto_zoom_lonlat`: budget bounded, resolution target met, lat-clamped
  extents, explicit zoom passthrough.
- `dem_tile_range` at zoom 0/1 bounds.
- Stitch with a **fake tile fetch** (`fetch_dem` given a stub session whose
  `get` returns PIL-built terrarium PNGs): mosaic shape, lon/lat grid
  monotonicity, z values, NaN watermark; all-failed → `TileFetchError`;
  partial failure → warning + subset grid.
- Cache: reads hit the cache without re-fetching (monkeypatched session
  counts calls); cache-dir override honored.

## Acceptance criteria

- [ ] `io/dem.py` exposes decode/zoom/range/fetch as documented above with
      no `renderers.*` import (io-layer self-contained)
- [ ] Terrarium decode formula exact; nodata/water decode to `np.nan`;
      elevation band clipped
- [ ] 10% lon/lat buffer applied around the requested bbox (old-geomapper
      parity); zoom auto-selection stays within the tile budget
- [ ] Per-tile cache under `GEOFIG_DEM_CACHE` / `~/.cache/geofig_engine/dem`
      avoids re-fetching cached tiles; lookup keyed by `{z}/{x}/{y}`
- [ ] All-tiles-failed raises `TileFetchError`; partial failure warns and
      proceeds (both mirror basemap.py semantics)
- [ ] `requests`/`PIL` imports are lazy; importing the module works offline
- [ ] Full suite green after this WP