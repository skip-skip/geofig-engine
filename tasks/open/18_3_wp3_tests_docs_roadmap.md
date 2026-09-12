# Phase 18.3: stream tests, docs, ROADMAP/ARCHITECTURE un-defer, example regen

**Status**: open
**Phase**: 18.3
**Version target**: v0.3.1+ (patch — bump decision deferred to the epic review WP)
**Dependencies**: `18_3_wp2_stat_template_wiring`

## Description

Behavioral coverage for the shipped stream stack (unit + renderer integration,
**all network-free** via the wp2 seam and canned JSON fixtures), the
documentation/ROADMAP un-defer of the stream geom, and the regression-guarded
recipe pins. Closes the epic.

## Changes

### `tests/test_streams.py` (new)

- io: `parse_lines` fixtures (LineString, MultiLineString, degenerate parts,
  trailing-NaN trim, non-polyline → `StreamsError`); `query_lines` URL
  building + pagination loop + `max_pages` cap + `truncated` flag against a
  fake `requests.get`; `fetch_streams` warn + empty on HTTP error / malformed
  JSON / empty features / invalid bbox (no HTTP call for empty bbox).
- `StatStreams` with the seam: two-column `x`/`y` frame; NaN separators split
  distinct segments and stay open; seam raising → `UserWarning` + empty frame
  (never propagates); missing coordinate columns → empty frame, no seam call;
  `layer_id`/`where`/`max_pages` validation (`ValueError`).
- Renderer integration: a site_map-style spec with a streams layer draws
  `ax.lines` above the contour/boundary band and below the site points;
  non-WGS84 projection (pyproj-gated both ways, the `test_site_map.py`
  pattern).

### `tests/test_site_map.py` / `tests/test_basemap.py` (network-free updates)

- `test_default_settings_include_contours` (l.207) → `len(recipe.layers)
  == 5`; the defaults pin includes the `streams` key (JSON-safe subset).
- `test_contours_opt_out_omits_layer` (l.220) → 3-layer with both
  contours+streams disabled; `settings_streams` on/off assertions.
- New: `test_streams_render_default_on_and_opt_out` via the seam
  (`settings={"streams": {"streams_source": <synthetic lines>}}`) →
  line artists; `{"streams": None}` → none; styling override test
  (blue/lw/alpha honored).
- **Existing render tests must stay network-free:** every
  `site_map_builder(settings={"contours": None})` use in `test_site_map.py`
  (l.189-438) and `test_basemap.py` (l.307-419) either adds
  `"streams": None` or a module-level autouse seam fixture — default-on
  streams must never trigger a real HTTP call in the suite.

### Docs

- `ROADMAP.md`: Phase 15 bullet (l.455) "**Deferred to M2:** stream geoms" →
  stream geoms **shipped via 18.3**; add `## ✅ Phase 18.3 — stream overlay
  (site_map)` (public USGS `NHDPlus_HR` REST source, default-on, pagination
  cap, seam, no-legend, WPs `tasks/closed/18_3_*.md`, suite count).
- `ARCHITECTURE.md`: l.80 row → contours **and streams implemented**; l.634
  note + l.641 deferred-geoms checkbox drop streams (leaving
  `GeomTable`/`GeomColorbar`); the geo geoms table (l.346-355) marks the
  stream geom implemented.
- `docs/api/streams.md` (new, small, mirrors `docs/api/dem.md`): the access
  contract — endpoint, params (`layer_id`, `where`, `max_pages`), bbox/−4326
  output, pagination/truncation, US-only coverage, degrade semantics.
- `docs/api/engine.md`: a `site_map` streams settings row.
- `site_map.py` module docstring streams section (added by wp2).

### Example

- `examples/site_map_example.py` regenerates (streams are default-on, same
  live-network character as the existing contour/basemap fetches); outputs in
  `examples/outputs/site_map_output*` refreshed.

## Acceptance criteria

- [ ] `tests/test_streams.py` covers io (parse/paginate/fetch-degrade) +
      stat seam + renderer integration; **no test in the suite hits the
      network**
- [ ] Every pre-existing `site_map` render test that would inherit default-on
      streams is pinned to `"streams": None` or an autouse seam; layer-count
      and defaults pins updated (4→5 / 3 with both disabled)
- [ ] ROADMAP Phase 18.3 entry added; Phase 15 deferral line and
      ARCHITECTURE deferral rows/checkboxes updated (streams shipped, only
      `GeomTable`/`GeomColorbar` deferred)
- [ ] `docs/api/streams.md` + `docs/api/engine.md` document the stream
      setting and the access contract
- [ ] Example regenerated with the streams layer present; outputs refreshed
- [ ] Full suite green (baseline 1440 passed / 7 skipped — pyproj-gated skips
      unchanged; no new skips from the warning policy)
- [ ] Committed as a single commit
      (`geofig-engine: stream tests + docs -> v0.3.1`)