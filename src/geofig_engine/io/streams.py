"""
USGS National Map NHDPlus_HR stream access for geofig_engine (Phase 18.3, wp1).

A self-contained stream fetcher that queries the public USGS National Map
``NHDPlus_HR`` ArcGIS REST service (NetworkNHDFlowline layer) for the frame
bbox and returns contour-frame-shaped multipart polylines:

    DEFAULT_STREAM_SERVICE_URL =
        https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/3/query

Request contract (verified live): ``f=geojson``, an envelope ``geometry``
(the WGS84 bbox as ``{"xmin","ymin","xmax","ymax","spatialReference":
{"wkid":4326}}``) with ``geometryType=esriGeometryEnvelope`` and
``inSR/outSR=4326``; a ``where`` filter (default ``ftype = 460`` —
Stream/River); and ``resultRecordCount``/``resultOffset`` pagination driven by
the service's ``exceededTransferLimit`` flag. The service publishes a
``MaxRecordCount`` of 2000; a query is capped at ``max_pages`` offset batches
and the returned ``truncated`` flag reports whether more results still exist.
Coverage is US-only (the NHD), so an empty result outside the US is an
expected, **silent** outcome — not an error. A truncated result, by contrast,
is incomplete and warns before degrading to an empty frame.

Parsing: every ``LineString``/``MultiLineString`` part is exploded into one
appended ``x``/``y`` vertex list with ``np.nan`` inserted between parts (and a
trailing separator trimmed) so ``render_boundary`` keeps every segment open —
the exact contour-frame / particle-overlay shape.

Layering: this is an **io-layer** module — no imports from ``renderers.*``
and no upstream/engine internals (mirrors ``io/dem.py``). ``requests`` is
imported lazily inside the functions, so a pure-offline
``import geofig_engine.io.streams`` succeeds without it.
"""

from __future__ import annotations

import json
import math
import warnings

import numpy as np
import pandas as pd

DEFAULT_STREAM_SERVICE_URL = (
    "https://hydro.nationalmap.gov/arcgis/rest/services/"
    "NHDPlus_HR/MapServer/3/query"
)
"""USGS NHDPlus_HR NetworkNHDFlowline query endpoint (EPSG:4326)."""

USER_AGENT = "geofig-engine/0.3 (declarative site_map streams)"

MAX_RECORD_COUNT = 2000
"""Service-side max records per query response (MaxRecordCount)."""

DEFAULT_MAX_PAGES = 5
"""Default cap on offset batches (``resultOffset`` pages) fetched per query."""

STREAM_WHERE = "ftype = 460"
"""Default feature-type filter: Stream/River."""

_ENVELOPE_WKID = 4326
"""Spatial reference of the query envelope / in- and outSR (WGS84)."""


class StreamsError(RuntimeError):
    """Raised when the stream REST query fails or the payload is unusable."""


# ---------------------------------------------------------------------------
# Bbox validation
# ---------------------------------------------------------------------------


def _norm_bbox(bbox):
    """Validate ``bbox`` and return ``(west, south, east, north)`` floats.

    Raises ``ValueError`` for non-sequence/wrong-length, non-numeric,
    non-finite, or degenerate (``west >= east`` / ``south >= north``) input.
    """
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise ValueError(
            "bbox must be a (west, south, east, north) sequence, "
            f"got {bbox!r}"
        )
    try:
        west, south, east, north = (float(v) for v in bbox)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"bbox values must be numbers, got {bbox!r}") from exc
    if not all(
        math.isfinite(v) for v in (west, south, east, north)
    ):
        raise ValueError(
            f"bbox values must be finite lon/lat numbers, got {bbox!r}"
        )
    if west >= east:
        raise ValueError(f"bbox west must be < east, got {bbox!r}")
    if south >= north:
        raise ValueError(f"bbox south must be < north, got {bbox!r}")
    return west, south, east, north


# ---------------------------------------------------------------------------
# REST query
# ---------------------------------------------------------------------------


def query_lines(
    bbox,
    service_url: str = DEFAULT_STREAM_SERVICE_URL,
    layer_id: int = 3,
    where: str = STREAM_WHERE,
    out_sr: int = 4326,
    page_size: int = MAX_RECORD_COUNT,
    max_pages: int = DEFAULT_MAX_PAGES,
    timeout: float = 30.0,
) -> tuple[list[dict], bool]:
    """Query the NHDPlus_HR REST service for stream polylines in ``bbox``.

    Sends a GET with the WGS84 bbox as an ``esriGeometryEnvelope``
    (``f=geojson``, ``returnGeometry=true``, ``outFields=ftype``) and pages
    through ``resultRecordCount``/``resultOffset`` batches while the service
    reports ``exceededTransferLimit``, capped at ``max_pages`` batches.

    Args:
        bbox: ``(west, south, east, north)`` in WGS84 degrees.
        service_url: REST query endpoint (already a layer ``/query`` URL, or a
            bare ``MapServer`` URL to which ``{layer_id}/query`` is appended).
        layer_id: layer number used only when ``service_url`` is a bare
            ``MapServer`` base (the default URL already points at layer 3,
            NetworkNHDFlowline).
        where: feature-type filter (default Stream/River).
        out_sr: output spatial reference (default WGS84).
        page_size: requested records per page (clamped to
            :data:`MAX_RECORD_COUNT`).
        max_pages: maximum offset batches fetched before giving up.
        timeout: per-request timeout in seconds.

    Returns:
        ``(features, truncated)`` — the accumulated ``features`` list from
        the GeoJSON payload and True only when the last fetched page still
        reported ``exceededTransferLimit`` (more results exist than were
        fetched).

    Raises:
        ValueError: invalid/degenerate ``bbox`` (validated before any HTTP).
        StreamsError: non-200 response, malformed JSON, or a payload without
            a ``features`` list.
    """
    west, south, east, north = _norm_bbox(bbox)
    if service_url.endswith("/query"):
        url = service_url
    else:
        url = f"{service_url.rstrip('/')}/{layer_id}/query"

    # Lazy: the io-layer import discipline allows a pure-offline import.
    import requests  # noqa: PLC0415

    features: list[dict] = []
    offset = 0
    pages = max(1, int(max_pages))
    page_size = max(1, min(int(page_size), MAX_RECORD_COUNT))
    truncated = False
    for _ in range(pages):
        params = {
            "f": "geojson",
            "geometry": json.dumps(
                {
                    "xmin": west,
                    "ymin": south,
                    "xmax": east,
                    "ymax": north,
                    "spatialReference": {"wkid": _ENVELOPE_WKID},
                }
            ),
            "geometryType": "esriGeometryEnvelope",
            "inSR": _ENVELOPE_WKID,
            "outSR": out_sr,
            "where": where,
            "returnGeometry": "true",
            "outFields": "ftype",
            "resultRecordCount": page_size,
            "resultOffset": offset,
        }
        resp = requests.get(
            url,
            params=params,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        if resp.status_code != 200:
            raise StreamsError(
                f"stream service returned HTTP {resp.status_code} for {url}"
            )
        try:
            payload = resp.json()
        except ValueError as exc:
            raise StreamsError(
                f"stream service returned malformed JSON for {url}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise StreamsError(
                f"stream service returned a non-object payload for {url}"
            )
        page_features = payload.get("features")
        if not isinstance(page_features, list):
            raise StreamsError(
                f"stream service payload missing a 'features' list for {url}"
            )
        features.extend(page_features)
        if not payload.get("exceededTransferLimit"):
            break
        offset += page_size
        if offset >= pages * page_size:
            truncated = True
            break
    return features, truncated


# ---------------------------------------------------------------------------
# Parse + fetch
# ---------------------------------------------------------------------------


def parse_lines(features: list[dict]) -> tuple[list[float], list[float]]:
    """Explode GeoJSON polylines into NaN-separated open multipart ``x``/``y``.

    Every ``LineString``/``MultiLineString`` part (lon/lat vertex pairs) is
    appended to a single ``x``/``y`` vertex list with ``np.nan`` inserted
    between parts (trailing separator trimmed), so ``render_boundary`` keeps
    each segment open. Degenerate parts (empty or <2 points) are skipped.
    Non-polyline / malformed geometries raise :class:`StreamsError`.

    Returns:
        ``(x, y)`` parallel float lists (empty for empty/degenerate input).
    """
    x: list[float] = []
    y: list[float] = []
    for feature in features:
        if not isinstance(feature, dict):
            raise StreamsError(
                f"malformed feature (expected a dict, got {feature!r})"
            )
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            raise StreamsError(
                f"non-array geometry {geometry!r} "
                "(expected a GeoJSON geometry dict)"
            )
        gtype = geometry.get("type")
        coordinates = geometry.get("coordinates")
        if gtype == "LineString":
            parts = [coordinates]
        elif gtype == "MultiLineString":
            if not isinstance(coordinates, list):
                raise StreamsError(
                    f"MultiLineString coordinates must be a list, "
                    f"got {coordinates!r}"
                )
            parts = coordinates
        else:
            raise StreamsError(
                f"unsupported geometry type {gtype!r} "
                "(expected LineString or MultiLineString)"
            )
        for part in parts:
            if not isinstance(part, list) or len(part) < 2:
                continue  # degenerate (empty / <2 points) → skip
            for vertex in part:
                if not isinstance(vertex, (list, tuple)) or len(vertex) < 2:
                    raise StreamsError(f"malformed vertex {vertex!r}")
                try:
                    x.append(float(vertex[0]))
                    y.append(float(vertex[1]))
                except (TypeError, ValueError) as exc:
                    raise StreamsError(f"malformed vertex {vertex!r}") from exc
            x.append(float("nan"))  # between-parts separator
            y.append(float("nan"))
    if x:  # trim the trailing separator
        x.pop()
        y.pop()
    return x, y


def fetch_streams(bbox, **kwargs) -> pd.DataFrame:
    """Fetch NHDPlus_HR streams for ``bbox`` as a contour-frame DataFrame.

    Returns a DataFrame with exactly two float64 columns, ``x`` and ``y``
    (NaN-separated open multipart polylines — the StatContour / particle
    overlay frame shape). **Never raises**: invalid/degenerate bbox input
    returns an empty frame without any HTTP call; transport/HTTP/parse
    failures and pagination truncation warn ``UserWarning`` ("streams
    unavailable") and return an empty frame. An empty but successful result
    (e.g. a non-US bbox) is silent and also returns an empty frame, so the
    layer pipeline always receives a plottable shape.

    Args:
        bbox: ``(west, south, east, north)`` in WGS84 degrees.
        **kwargs: forwarded to :func:`query_lines` (``service_url``,
            ``layer_id``, ``where``, ``out_sr``, ``page_size``, ``max_pages``,
            ``timeout``).

    Returns:
        ``pd.DataFrame({"x": float64 array, "y": float64 array})`` — empty
        (zero rows) on failure, truncation, or an empty result.
    """
    empty = pd.DataFrame(
        {
            "x": np.array([], dtype=np.float64),
            "y": np.array([], dtype=np.float64),
        }
    )
    try:
        features, truncated = query_lines(bbox, **kwargs)
        if truncated:
            # Returning a partial stream set would silently drop upstream
            # reaches, so keep the degrade visible and render nothing.
            warnings.warn(
                "streams unavailable: query exceeded max_pages; results were "
                "truncated",
                UserWarning,
                stacklevel=2,
            )
            return empty
        x, y = parse_lines(features)
    except ValueError:
        # Invalid/degenerate bbox: no HTTP call was made, stay silent.
        return empty
    except Exception as exc:  # noqa: BLE001 — transport/HTTP/parse degrade
        warnings.warn(f"streams unavailable: {exc}", UserWarning, stacklevel=2)
        return empty
    if not x:
        # An empty successful query (US-only coverage outside the NHD, or a
        # bbox with no streams) is expected — the empty layer renders nothing.
        return empty
    return pd.DataFrame(
        {
            "x": np.asarray(x, dtype=np.float64),
            "y": np.asarray(y, dtype=np.float64),
        }
    )