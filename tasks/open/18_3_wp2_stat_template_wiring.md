# Phase 18.3: stream geom + stat + `site_map` template wiring

**Status**: open
**Phase**: 18.3
**Version target**: v0.3.1+ (patch — bump decision deferred to the epic review WP)
**Dependencies**: `18_3_wp1_io_streams`

## Description

The declarative plumbing for the stream layer: a `GeomStreams` geom,
handler dispatch onto the existing open-multipart polyline renderer, a
`StatStreams` spec-build transform (bbox → NaN-separated `x`/`y` via the wp1
io module or the `streams_source` seam), and the default-on recipe wiring in
`site_map` (adjacent to the 18.2 contour layer).

## Changes

### `src/geofig_engine/core/geom.py`

- `GeomStreams(Geom)` — `name="streams"`, channels `x`/`y`, defaults
  `edgecolor="blue"`, `edgewidth=0.7`, `edgealpha=0.7`, `edgestyle="-"`
  (old-geomapper `add_streams` look).

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- `_GEOM_HANDLERS["streams"] = render_boundary` (open NaN-separated multipart
  paths — exactly the contour frame shape). No renderer/viewport change:
  streams are extent-bounded so they render in the normal data loop.

### `src/geofig_engine/templates/site_map.py`

- `StatStreams(Stat)` (mirror `StatContour`, l.306-440):
  - `__init__(streams_source: Callable[[bbox], DataFrame] | None = None,
    service_url: str = DEFAULT_STREAM_SERVICE_URL, layer_id: int = 3,
    where: str = "ftype = 460", max_pages: int = 5)` — validation (callable
    or None; layer_id int; where non-empty str; max_pages int ≥ 1), the
    callable seam stored as an attribute (not JSON-safe), everything else in
    `params`;
  - `compute(data) -> DataFrame` with `{"x": …, "y": …}` (NaN-separated open
    multipart): bbox from the detected lon/lat columns (or empty frame when
    coordinates are absent — no source call);
  - `streams_source` seam called with the bbox (dem-source parity);
  - default path (no seam): `fetch_streams(bbox, service_url=…, layer_id=…,
    where=…, max_pages=…)` — never raises; `UserWarning` + empty frame on any
    failure; empty result (non-US bbox) → empty frame, no warning beyond the
    existing degrade? → **warn only when the query itself fails/truncates**;
    an empty but successful result renders nothing silently.
- `SITE_MAP_DEFAULTS["streams"] = {"enabled": True, "color": "blue",
  "linewidth": 0.7, "alpha": 0.7, "service_url": DEFAULT_STREAM_SERVICE_URL,
  "layer_id": 3, "where": "ftype = 460", "max_pages": 5, "streams_source":
  None}` (the callable seam is never serialized).
- `settings_streams(settings) -> dict | None` merge-check mirroring
  `settings_contours`: `None` / `{"enabled": False}` → disabled; dict
  overrides merge onto defaults; unknown keys rejected.
- Builder: when enabled, emit a `Layer(geom=GeomStreams(...),
  stat=StatStreams(...), mapping={})` at **zorder=1** after the contour layer
  (above contour/boundary, below sites/labels — the equal-zorder `_children`
  insertion order handles the within-band stacking exactly as 18.2 contour
  does).
- Module docstring: add a **Streams** section (endpoint, default-on/settings
  keys, degrade, no-legend, US-only coverage).

## Acceptance criteria

- [ ] `GeomStreams` registered (name `"streams"`, channels, old defaults);
      renderer dispatch draws it exactly like a contour layer (open multipart
      lines via `render_boundary`)
- [ ] `StatStreams` seam produces the contour-frame shape; missing coordinate
      columns → empty frame with no seam call; bbox is the provider frame's
      lon/lat bbox (no 10% DEM buffer — old stream parity)
- [ ] Default path (no seam) routes through `io.streams.fetch_streams`; a
      failing fetch or truncated results warns + empty frame; empty-success
      renders nothing silently
- [ ] `site_map_builder(settings={})` includes the stream layer (5 layers
      with contours); `{"streams": None}` / `{"enabled": False}` omits it;
      styling overrides propagate (`color`/`linewidth`/`alpha`); unknown
      stream keys rejected
- [ ] `settings_streams` on `recipe.default_settings` reflects on/off and is
      JSON-safe (no callable recorded)
- [ ] Committed as a single commit
      (`geofig-engine: site_map stream wiring -> v0.3.1`)