# Phase 18.3: Surface-water stream overlay for the site map template

**Status**: open
**Phase**: 18.3
**Version target**: v0.3.1+ (patch — bump decision deferred to the epic review WP)
**Dependencies**: none (phase overview)

## Description

Pull the still-M2-deferred **stream geom** forward and wire it into the
`site_map` template as a **default-on, single-colored surface-water layer**
(`ARCHITECTURE.md` line 80: "| DEM contour (site_map, 18.2) / stream geoms |
contour implemented, streams deferred |"; line 353; line 634; line 641
"Deferred geoms (streams, `GeomTable`/`GeomColorbar`)"; `ROADMAP.md` line 455:
"**Deferred to M2:** stream geoms").

Reference implementation: `../geochemmapper.py` `MapBuilder.download_streams`
(l.496) + `add_streams` (l.779):

- old source: local 3DHP GPKG, layer `hydro_3dhp_all_flowline`, CRS-space
  bbox-keyed GPKG cache, keep-intersecting features, reproject to map CRS,
  optional `FType==460` filter
- `add_streams(color="blue", linewidth=0.7, alpha=0.7, in_legend=True,
  label="3DHP Streams", group="Streams", zorder=3)` — one `ax.plot` per
  LineString/MultiLineString segment; no source → `ValueError`

**Decisions locked (with the requester):**

- **Data source: public USGS web API, not a local file.** The USGS National
  Map `NHDPlus_HR` ArcGIS REST service
  (`https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/3/query`)
  — verified live: `f=geojson` + envelope geometry + `inSR/outSR=4326` + `where
  = ftype = 460` (Stream/River) returns WGS84 `LineString` polylines with no
  API key; `exceededTransferLimit` requires `resultOffset`/`resultRecordCount`
  pagination (`maxRecordCount` 2000). Coverage is US-only — a non-US bbox
  returns no features (documented degrade, same as an empty result).
  `3DHP_all` (the service matching the legacy `hydro_3dhp_all_flowline` name)
  is a configurable alternative, but its Flowline layer's `featuretype`
  vocabulary has **no Stream/River code** (Channel Line=1/Canal=2/Drainageway=3
  /connectors 4-7) — so the default stays `NHDPlus_HR` layer 3.
- **No new dependency.** GeoJSON is parsed with stdlib `json`; `requests` is
  imported lazily (the `io/dem.py` pattern). **No geopandas/fiona**, no `[geo]`
  extra requirement; because the service is queried with `outSR=4326` the
  result is already lon/lat — no reprojection machinery.
- **Default state: on.** The stream layer is part of the `site_map` recipe and
  the query is lazy per render. Offline/HTTP failure, a non-200, malformed
  JSON, or an empty result warns (`UserWarning`) and yields an empty stream
  layer (basemap/DEM contour degrade parity). Disable with
  `settings={"streams": None}` or `{"streams": {"enabled": False}}`.
- **Seam:** `streams_source: Callable[[bbox], DataFrame]` (the `dem_source`
  pattern, site_map.py l.336) injects synthetic/network-free lines for tests
  and downstream callers; JSON-safe settings (`service_url`, `layer_id`,
  `where`, `max_pages`) drive the default fetch path and are recorded in
  `StatStreams.params`.
- **Styling: constant** — single color/linewidth/alpha for the whole line set,
  old-geomapper defaults (`color="blue"`, `linewidth=0.7`, `alpha=0.7`); **no
  legend entry** (requester decision — diverges from old `in_legend=True`,
  stays aligned with the contour layer's no-legend stance).
- **Filter:** default `where="ftype = 460"` (old `FType==460` parity),
  overridable via settings; pagination capped at `max_pages=5` (~10k
  features) with a `UserWarning` on truncation.
- **Projection/stacking:** result lon/lat feeds the NaN-separated open
  multipart frame `render_boundary` already draws (handlers.py:1020); the
  layer joins the **zorder-1 band** (above contour/boundary, below
  sites/labels) and is extent-bounded (clipped to the frame bbox, no buffer —
  old parity) so it renders in the normal data loop with **no viewport
  change**.

Rendering reuses the shipped NaN-separated multipath machinery
(`StatContour`/`StatParticleOverlay(mode="contours")` frame shape +
`render_boundary` — open paths at NaN). The status quo post-18.2 pins
`site_map_builder(settings={"contours": None})` recipes to 3 layers / 4 with
contours; streams adds a 5th.

## Phase-level acceptance criteria

- [ ] `render_template(data, template="site_map")` renders blue stream lines
      by default (lazy USGS query, `ftype=460`, US-only coverage), painted
      above the contour/boundary band and below the site points
- [ ] `settings={"streams": None}` (or `{"enabled": False}`) renders the
      previous stream-free figure with no HTTP query attempt
- [ ] Stream lines draw under a constant style with old-geomapper defaults
      (`color="blue"`, `linewidth=0.7`, `alpha=0.7`); **no legend entry**;
      styling overridable via `settings={"streams": {...}}`
- [ ] Offline/HTTP failure, malformed payload, or empty result is non-fatal:
      `UserWarning` + empty stream layer (render proceeds)
- [ ] Pagination cap: `exceededTransferLimit` pages looped up to
      `max_pages`; truncation warns
- [ ] No new required dependency (`requests` + stdlib `json` only, lazy
      import); works without the `[geo]` extra (service returns WGS84 already)
- [ ] `streams_source` seam (dem-style callable) keeps the entire test suite
      network-free, including every existing `site_map` render test that would
      otherwise inherit the default-on fetch
- [ ] Non-WGS84 `CoordGeo` `crs` projects the lon/lat stream polylines via the
      existing `transform_visual_mapping` path (contour/boundary parity)
- [ ] Full suite green (post-18.2-contour-fix baseline 1440 passed / 7
      skipped, 0 warning skips) after every WP
- [ ] Commits labeled `geofig-engine: <scope> → v0.3.1` (target finalized at
      epic review)

## Ticket map

| Ticket file | Scope | Depends |
| --- | --- | --- |
| `18_3_wp1_io_streams.md` | `io/streams.py`: REST query + pagination + GeoJSON parse + fetch + degrade | epic (context) |
| `18_3_wp2_stat_template_wiring.md` | `GeomStreams` + handler + `StatStreams` (bbox → NaN-separated x/y) + default-on recipe wiring | `18_3_wp1_io_streams` |
| `18_3_wp3_tests_docs_roadmap.md` | `test_streams.py` + network-free suite updates + ROADMAP/ARCHITECTURE un-defer + example regen | `18_3_wp2_stat_template_wiring` |

## Files

- `src/geofig_engine/io/streams.py` (new)
- `src/geofig_engine/core/geom.py`
- `src/geofig_engine/templates/site_map.py`
- `src/geofig_engine/renderers/matplotlib/renderer.py` (handler registration)
- `tests/test_streams.py` (new), `tests/test_site_map.py`, `tests/test_basemap.py`
- `examples/site_map_example.py` (+ outputs), `docs/api/engine.md`,
  `docs/api/streams.md` (new), `ARCHITECTURE.md`, `ROADMAP.md`
- this ticket list (`tasks/open/18_3_*.md`)