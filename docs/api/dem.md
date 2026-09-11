# API Reference — DEM access

`geofig_engine.io.dem` is the standalone DEM access layer behind the
`site_map` elevation contours (Phase 18.2): AWS Terrain Tiles (terrarium)
are fetched over a lon/lat extent, decoded to meters, and stitched into a
lon/lat grid — **without** the elevation/GDAL/rasterio stack. It is an
io-layer module (no renderer imports); `requests`/`PIL` load lazily inside
the functions, so `import geofig_engine.io.dem` succeeds offline.

```python
from geofig_engine.io.dem import fetch_dem, DemGrid, dem_cache_dir
```

## Access contract

- **Endpoint** — AWS Open Data Terrain Tiles (terrarium SRTM), Web-Mercator
  XYZ tiles:

  ```
  https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png
  ```

- **Decode formula** — per pixel, meters from the RGB channels:

  ```
  alt = (r * 256 + g + b / 256) - 32768        [meters]
  ```

  Pixels decoding to exactly `-32768` mark nodata/water and become `np.nan`;
  surviving values are clipped to `ELEVATION_BAND = (-500, 9000)` m.

- **Cache layout** — per-tile PNGs under `dem_cache_dir()/terrarium/{z}/{x}/{y}.png`
  (mirrors the XYZ URL layout), keyed by zoom + tile indices; a cached tile
  is read from disk instead of the network. The cache root is
  `~/.cache/geofig_engine/dem`, overridable via the `GEOFIG_DEM_CACHE` env
  var.

- **Zoom selection** — `auto_zoom_lonlat` picks the finest zoom meeting the
  tile budget (`DEM_TILE_BUDGET = 64`) while preferring a resolution of
  `max(5, interval / 3)` m/px; bounds: `MIN_ZOOM = 6` … `MAX_ZOOM = 15`.

- **Fail / degrade semantics** — all tiles failing raises `TileFetchError`
  (the caller degrades); a partial mosaic warns and returns the fetched
  tiles with `np.nan` fill; the stat layer (`StatContour`) turns any of
  these (plus HTTP/DEM decode errors) into a `UserWarning` + a contour-free
  render — never an exception.

## `fetch_dem(west, south, east, north, interval=10.0, zoom=None, session=None, timeout=10.0, cache_dir=None)`

Fetches and stitches a terrarium DEM covering the WGS84 bbox.

| Param | Type | Description |
| --- | --- | --- |
| `west`/`south`/`east`/`north` | `float` | Bbox in degrees, order-agnostic. |
| `interval` | `float` | Contour interval in meters (drives auto-zoom resolution). |
| `zoom` | `int \| None` | Explicit XYZ zoom (default: auto). |
| `session` | `Any \| None` | `requests.Session`-like object (`get(url, timeout=, headers=)`); a real session is created when `None`. |
| `timeout` | `float` | Per-tile request timeout in seconds. |
| `cache_dir` | `Path \| str \| None` | Cache root override (defaults to `dem_cache_dir()`). |

Applies a **10% lon/lat buffer** around the bbox (old-geomapper parity);
fetches missing tiles only; returns a `DemGrid`.

**Raises:** `ValueError` — degenerate bbox (zero width and height);
`TileFetchError` — every requested tile failed to load/fetch.

## `DemGrid` (frozen dataclass)

A stitched DEM mosaic: `lon`/`lat` are 2-D grids (broadcast over the mosaic's
pixels, north→south / west→east) and `z` the elevation in meters with
`np.nan` for nodata/water or failed tiles.

## `dem_cache_dir()`

`GEOFIG_DEM_CACHE` env var, then `~/.cache/geofig_engine/dem`.

## Integration

`StatContour` (in `geofig_engine.templates.site_map`) calls
`fetch_dem(*bbox, interval=…)` for the frame's lon/lat extent when no
`dem_source` is injected; the `site_map` template renders contours
**default-on** (old-geomapper 10 m white 0.5 pt at alpha 0.6, above the
basemap, below the boundary ring). `settings={"contours": None}` on the
builder disables the layer; a dict can override `interval`/`color`/
`linewidth`/`alpha` and supply a synthetic `dem_source` (test seam — no
network).

---

*Next: [io.md](io.md) · [engine.md](engine.md) · [core.md](core.md) · [templates.md](templates.md)*