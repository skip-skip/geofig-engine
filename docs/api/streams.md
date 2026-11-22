# API Reference — Stream access

`geofig_engine.io.streams` is the standalone surface-water access layer behind
the `site_map` stream overlay (Phase 18.3). It queries the public USGS National
Map `NHDPlus_HR` ArcGIS REST service for the frame's WGS84 lon/lat bbox and
returns GeoJSON polylines in the same NaN-separated `x`/`y` multipart frame the
contour layer uses. It is an io-layer module (no renderer imports); `requests`
loads lazily inside the query, so `import geofig_engine.io.streams` succeeds
offline.

```python
from geofig_engine.io.streams import (
    DEFAULT_STREAM_SERVICE_URL,
    StreamsError,
    fetch_streams,
    parse_lines,
    query_lines,
)
```

## Access contract

- **Endpoint** — USGS `NHDPlus_HR` / NetworkNHDFlowline query:

  ```
  https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/3/query
  ```

  No API key or new dependency. `requests` + stdlib `json` only; `[geo]` is not
  required because the service returns EPSG:4326 geometry.

- **Request** — `f=geojson`, an `esriGeometryEnvelope` built from
  `(west, south, east, north)` with `spatialReference={"wkid": 4326}`,
  `inSR=outSR=4326`, `where="ftype = 460"` (Stream/River),
  `returnGeometry=true`, and `outFields=ftype`. A bare `MapServer` URL has
  `/{layer_id}/query` appended; the default URL already names layer 3.

- **Pagination** — `resultRecordCount`/`resultOffset` pages are fetched while
  the service reports `exceededTransferLimit`, capped at `max_pages` (default
  5) offset batches. `query_lines` returns `(features, truncated)`; `truncated`
  is True only when the cap was hit with more results still available.

- **Coverage** — US-only (NHD). An empty feature list for a non-US bbox is a
  normal, **silent** result; it is not an error.

## `query_lines(bbox, service_url=..., layer_id=3, where=..., out_sr=4326, page_size=2000, max_pages=5, timeout=30.0)`

Returns `(features, truncated)`. Raises `ValueError` for an invalid/degenerate
bbox (before any HTTP call) and `StreamsError` for a non-200 response,
malformed JSON, or a payload without a `features` list.

## `parse_lines(features)`

Explodes GeoJSON `LineString`/`MultiLineString` parts into parallel `x`/`y`
float lists with `np.nan` between parts (trailing separator trimmed), so
`render_boundary` keeps every segment open. Degenerate parts (<2 points) are
skipped; non-polyline or malformed geometries raise `StreamsError`.

## `fetch_streams(bbox, **kwargs)`

Convenience wrapper returning `pd.DataFrame({"x": float64, "y": float64})`.
Never raises:

| Outcome | Behavior |
| --- | --- |
| Invalid/degenerate bbox | empty frame, no HTTP call, silent |
| Empty successful query | empty frame, silent |
| Transport / HTTP / malformed payload / parse failure | `UserWarning` + empty frame |
| Pagination cap reached (`truncated`) | `UserWarning` + empty frame (a partial stream set is never rendered) |

## Integration

`StatStreams` (in `geofig_engine.templates.site_map`) calls
`fetch_streams(*bbox, service_url=…, layer_id=…, where=…, max_pages=…)` for the
provider frame's **unbuffered** lon/lat bbox when no `streams_source` seam is
injected. The `site_map` template renders streams **default-on** (blue, 0.7 pt,
alpha 0.7, no legend entry) in the zorder-1 band above the contour/boundary
linework and below the site points/labels. Disable with
`settings={"streams": None}` or `{"streams": {"enabled": False}}`; override
query knobs or inject a network-free `streams_source(bbox) -> DataFrame`
through the builder's `streams` dict. The callable is never recorded in the
recipe's JSON-safe settings.

---

*Next: [dem.md](dem.md) · [engine.md](engine.md) · [io.md](io.md)*
