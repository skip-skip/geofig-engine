# Phase 15: site_map basemap tiles

**Status**: complete
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_wp6_base_templates`, `15_wp8_coordgeo_geoms`, `15_wp9_site_map`

## Description

Pull the M2-deferred **basemap tiles** forward for the `site_map` template:
render a Web-Mercator XYZ tile mosaic beneath the boundary/point/label layer
stack (`ARCHITECTURE.md` `## Templates & Registry`: "CoordGeo site map:
basemap + point layers + grouped legend"; `ROADMAP.md` line 439: "Deferred to
M2: tile basemaps ...").

Reference implementation: `../geochemmapper.py` `MapBuilder.add_basemap`
(contextily `cx.add_basemap`, `Esri.WorldImagery` default). This work package
reproduces that behavior **without** the contextily/geopandas/rasterio stack:
a self-contained XYZ fetcher built on `requests` + `Pillow` (both present in
the base environment) with closed-form Web-Mercator math, so tiles work even
without the `[geo]` extra. `xyzservices` is used only for optional provider
lookup when installed.

The basemap is painted by the renderer **below the layer stack** (the hook the
wp9 docstring reserved) and contributes nothing to the legend.

## Changes

### `src/geofig_engine/renderers/matplotlib/basemap.py` (new)

- Closed-form Web-Mercator math: `lonlat_to_mercator` / `tile_to_lonlat` /
  `tile_range` (lat clamped to ±85.0511° per the slippy-map spec).
- `auto_zoom(west, south, east, north, width_px, height_px, ...)` — finest
  zoom that stays within a tile budget (used when no explicit `zoom` given).
- `resolve_provider(spec)` — `True` → default provider; name string →
  `DEFAULT_PROVIDERS` (`esri_world_imagery`, `osm`) or (best-effort)
  xyzservices attribute walk; `{url: ...}` / `{provider: ...}` dict; raw http
  URL; `None`/`False` → disabled.
- `fetch_basemap(west, south, east, north, zoom=None, provider=None,
  width_px=800, height_px=600, max_tiles=256, session=None, timeout=10.0)
  -> BasemapTiles` — fetches the tile range (thread pool, ≤8 workers, bounded
  by `max_tiles`), stitches an RGBA mosaic, returns
  `BasemapTiles(image, extent=(west, south, east, north), zoom, provider,
  n_tiles)` in **lon/lat** (tile-aligned rectangle).
- `TileFetchError` for transport/HTTP/all-tiles-failed conditions.
- `mosaic_in_output_crs(image, extent, crs)` — passthrough for WGS84;
  otherwise projects the mosaic corners into `crs` via pyproj (`None` when
  pyproj is unavailable).
- `lonlat_bbox_for_crs(crs, xmin, xmax, ymin, ymax)` — identity for WGS84;
  inverse-projects the corners otherwise (`None` without `[geo]`).

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- `_render_axes`: after the layer loop captures `xlim_data`/`ylim_data` and
  before `ax.autoscale(False)`, when `spec.settings.get("basemap")` is truthy
  and `spec.coord` is `CoordGeo`, call a new `_render_basemap(...)`.
- `_render_basemap(ax, coord, setting, limits)`:
  - Resolves the provider; computes the lon/lat bbox for the axis extent
    (`lonlat_bbox_for_crs`); `requests`-independent zoom/alpha from the
    setting dict (`zoom`, `alpha`).
  - Fetches the mosaic, positions it with
    `ax.imshow(image, extent=..., zorder=0, alpha=alpha, aspect="auto")`, then
    the captured data limits are re-applied by the existing tail of
    `_render_axes`.
  - Non-WGS84 `crs` without pyproj, or any fetch failure → `UserWarning`
    ("site_map basemap tiles unavailable: ..." / pyproj note) and render
    proceeds tile-free (non-fatal, mirrors `transform_visual_mapping`).

### `src/geofig_engine/templates/site_map.py`

- `SITE_MAP_DEFAULTS["basemap"] = {"provider": "esri_world_imagery",
  "alpha": 0.6}` (Esri WorldImagery, matching `geochemmapper.py`'s default).
- Docstring updates: replace the "tiles deferred to M2 / future tile hook"
  note (wp9) with the implemented behavior: default imagery tiles, opt-out
  via `settings={"basemap": None}`, tile attribution string surfacing via the
  provider dict, offline/`[geo]`-less degrade path.

### `tests/test_site_map.py`

- Existing render tests that must stay network-free/deterministic pass
  `settings={"basemap": None}`.
- New `test_default_settings_enable_imagery_basemap` asserts the recipe
  default carries the Esri provider + alpha.

### `tests/test_basemap.py` (new)

- Pure-math tests (offline): mercator round-trip; `tile_range` at zoom 0/1
  bounds; `tile_bounds` adjacency/ordering; `auto_zoom` budget + lat clamp.
- `fetch_basemap` with a fake `session` (PIL-built tile PNGs): mosaic
  dimensions/color, extent tile-alignment, `n_tiles`; all-failed →
  `TileFetchError`.
- Renderer integration with `fetch_basemap` monkeypatched (no network):
  - success → `ax.images` has one `AxesImage` at `zorder == 0` with expected
    `extent`/`alpha`; points/labels still rendered;
  - `TileFetchError` → `UserWarning` + figure renders tile-free;
  - `settings={"basemap": None}` → no image artist, no fetch;
  - non-WGS84 `crs` without pyproj → pyproj `UserWarning` + tile-free
    (`skipif(GEO_INSTALLED)`);
  - non-WGS84 `crs` with pyproj → image extent in projected units
    (`skipif(not GEO_INSTALLED)`).

### `examples/site_map_example.py`

- Pass explicit `settings={"basemap": {...}}` (provider defaulted; alpha
  override) so the example demonstrates the tile path; note the offline
  degrade behavior in a comment.

## Acceptance criteria

- [ ] `render_template(..., template="site_map")` shows Esri WorldImagery
      tiles behind boundary + points + labels by default (mosaic at
      `zorder == 0`, alpha from the default settings)
- [ ] `settings={"basemap": None}` renders the previous tile-free figure
      (no network attempt); `settings={"basemap": {"provider": "...",
      "zoom": ..., "alpha": ...}}` overrides provider/zoom/alpha
- [ ] Tiles work without the `[geo]` extra (closed-form Web-Mercator); a
      non-WGS84 `CoordGeo` `crs` projects the mosaic corners via pyproj when
      `[geo]` is installed and warns + renders tile-free when it is not
- [ ] Offline/failed tile fetch is non-fatal: `UserWarning` + normal figure
- [ ] Basemap contributes nothing to the legend and is not a spec layer
- [ ] No new required dependencies (`requests` + `Pillow` only; `xyzservices`
      optional lookup); no live network access in the test suite (mocked
      sessions/`fetch_basemap`)
- [ ] New `tests/test_basemap.py` covers math, mocked fetch, renderer
      integration, and the pyproj gates; full suite green
- [ ] Committed as a single commit
      (`geofig-engine: site_map basemap tiles → v0.2.0`)

## Files

- `src/geofig_engine/renderers/matplotlib/basemap.py` (new)
- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `src/geofig_engine/templates/site_map.py`
- `tests/test_basemap.py` (new)
- `tests/test_site_map.py`
- `examples/site_map_example.py`
- `tasks/closed/15_wp9_site_map.md` (historical — wp9's "no tile-service
  requests" AC is superseded by this work package; the wp12 docs ticket owns
  any ROADMAP/ARCHITECTURE rewording)