# Phase 18.3: stream web-API I/O (`io/streams.py`)

**Status**: complete
**Phase**: 18.3
**Version target**: v0.3.1+ (patch — bump decision deferred to the epic review WP)
**Dependencies**: none (the open `18_3_epic` is a review ticket, not a
blocking implementation dependency)

## Description

The io-layer access contract for the stream overlay: a lazy, self-contained
module that queries the public USGS National Map `NHDPlus_HR` ArcGIS REST
service for the frame bbox and returns a contour-frame-shaped DataFrame
(NaN-separated open multipart `x`/`y` polylines). Mirrors `io/dem.py`'s
structure and failure posture: no renderer imports, lazy `requests`, degrade
never raising into the layer pipeline.

## Changes

### `src/geofig_engine/io/streams.py` (new)

- Module docstring: endpoint, params, pagination, degrade semantics (the
  `io/dem.py` docstring style).
- `DEFAULT_STREAM_SERVICE_URL = "https://hydro.nationalmap.gov/arcgis/rest/
  services/NHDPlus_HR/MapServer/3/query"` (NetworkNHDFlowline; verified live:
  `f=geojson`, `where=ftype=460`, `inSR/outSR=4326`, `exceededTransferLimit`
  pagination).
- `query_lines(bbox, service_url=DEFAULT_STREAM_SERVICE_URL, layer_id=3,
  where="ftype = 460", out_sr=4326, page_size=2000, max_pages=5, timeout=30)
  -> tuple[list[dict], bool]`:
  - GET with `geometry` (WGS84 envelope JSON `{"xmin","ymin","xmax","ymax",
    "spatialReference":{"wkid":4326}}`), `geometryType=esriGeometryEnvelope`,
    `inSR`/`outSR`, `f=geojson`, `returnGeometry=true`, `outFields=ftype`,
    and `resultRecordCount`/`resultOffset`;
  - loops pages while `exceededTransferLimit` and `offset < max_pages *
    page_size`; returns `(features, truncated)` — truncated is True when the
    last page still reported `exceededTransferLimit`;
  - raises `StreamsError` (module exception) on non-200 / malformed payload;
    bbox validation (4 real lon/lat numbers, `west < east`, `south < north`).
- `parse_lines(features) -> tuple[list[float], list[float]]` (pure): explodes
  every `LineString`/`MultiLineString` `coordinates` part (lon/lat) into one
  appended `x`/`y` vertex list, inserting `NaN` between parts (and trimming a
  trailing separator) so `render_boundary` keeps every segment open; skips
  degenerate (empty / <2 point) parts; non-array geometries → `StreamsError`.
- `fetch_streams(bbox, **kwargs) -> pd.DataFrame`:
  - returns `{"x": <float array>, "y": <float array>}` (exactly two columns,
    the StatContour/particle-overlay frame shape) — **never raises**:
    catches `requests` failures / `StreamsError` and warns
    (`UserWarning`, "streams unavailable") + returns an empty frame;
  - trivial/empty bbox → empty frame, no HTTP call; empty feature list →
    empty frame (US-only coverage produces this outside the US).

## Acceptance criteria

- [ ] `query_lines` builds a correct paginated REST query (URL params
      asserted; page loop driven by `exceededTransferLimit`; caps at
      `max_pages`; `truncated` flag truthful)
- [ ] `parse_lines` produces NaN-separated multipart x/y from canned
      LineString + MultiLineString fixtures; parts stay open; degenerate parts
      skipped; trailing NaN trimmed; non-polyline geometry raises
- [ ] `fetch_streams` warns + returns an empty frame on HTTP error /
      malformed JSON / `StreamsError` / empty features — never propagates
- [ ] io-layer constraints: lazy `requests` import; no renderer/engine imports
      (the `TestNoUpstreamImports`-style import guard passes for the module)
- [ ] All tests network-free (canned JSON fixtures + monkeypatched `requests`)
- [ ] Committed as a single commit
      (`geofig-engine: stream io -> v0.3.1`)