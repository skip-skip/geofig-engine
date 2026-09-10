"""
Web-Mercator XYZ basemap tiles for geofig_engine (Phase 15 — M2 tiles, wp14).

A self-contained tile mosaic fetcher: ``requests`` + ``Pillow`` only (both
present in the base environment), closed-form Web-Mercator math, so basemap
tiles render even without the ``[geo]`` extra. ``xyzservices`` (when installed)
is used only for optional provider lookups; embedded URL/attribution defaults
keep the module functional without it.

This mirrors ``../geochemmapper.py``'s ``add_basemap`` semantics (mosaic for
the axis extent, painted beneath the vector layers) without the
geopandas/contextily/rasterio dependency stack:

    cx.add_basemap(self.ax, crs=self.crs, source=cx.providers.Esri.WorldImagery, ...)

The renderer hooks the fetched mosaic below the layer stack; the module itself
stays renderer-agnostic (pure math + fetch + mosaic assembly).
"""

from __future__ import annotations

import io
import math
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import numpy as np
import requests
from PIL import Image

from geofig_engine.core.coord import WGS84

TILE_SIZE = 256
"""XYZ tile edge length in pixels."""

MAX_LAT = 85.05112878
"""Web-Mercator latitude clamp (slippy-map spec)."""

WEB_MERCATOR_R = 6378137.0
"""Web-Mercator sphere radius (WGS84 semi-major axis, meters)."""

WORLD_MERCATOR_M = 2.0 * math.pi * WEB_MERCATOR_R
"""Full Web-Mercator world width/height in meters."""

USER_AGENT = "geofig-engine/0.2 (declarative site_map basemap)"

MAX_FETCH_WORKERS = 8

DEFAULT_PROVIDERS: dict[str, dict[str, str]] = {
    "esri_world_imagery": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/"
        "World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Tiles © Esri — Esri, Maxar, Earthstar Geographics, "
        "and the GIS User Community",
        "name": "esri_world_imagery",
    },
    "osm": {
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors",
        "name": "osm",
    },
}


class TileFetchError(RuntimeError):
    """Raised when a basemap tile mosaic cannot be fetched/assembled."""


@dataclass(frozen=True)
class BasemapTiles:
    """A fetched tile mosaic positioned in lon/lat (tile-aligned rectangle).

    ``extent`` is ``(west, south, east, north)`` in WGS84 degrees.
    """

    image: np.ndarray  # (H, W, 4) RGBA mosaic
    extent: tuple[float, float, float, float]
    zoom: int
    provider: dict[str, str]
    n_tiles: int


# ---------------------------------------------------------------------------
# Web-Mercator math (closed form — no pyproj required)
# ---------------------------------------------------------------------------


def _clamp_lat(lat: float) -> float:
    return min(max(lat, -MAX_LAT), MAX_LAT)


def lonlat_to_mercator(lon: float, lat: float) -> tuple[float, float]:
    """Project WGS84 lon/lat to Web-Mercator meters (x, y)."""
    x = math.radians(lon) * WEB_MERCATOR_R
    y = WEB_MERCATOR_R * math.log(
        math.tan(math.pi / 4.0 + math.radians(_clamp_lat(lat)) / 2.0)
    )
    return x, y


def tile_to_lonlat(x_tile: int, y_tile: int, zoom: int) -> tuple[float, float]:
    """Top-left corner (lon, lat) of an XYZ tile (slippy-map spec)."""
    n = 2 ** zoom
    lon = x_tile / n * 360.0 - 180.0
    lat = math.degrees(
        math.atan(math.sinh(math.pi * (1.0 - 2.0 * y_tile / n)))
    )
    return lon, lat


def tile_bounds(
    x_tile: int, y_tile: int, zoom: int
) -> tuple[float, float, float, float]:
    """(west, south, east, north) of an XYZ tile in lon/lat."""
    west, north = tile_to_lonlat(x_tile, y_tile, zoom)
    east, _ = tile_to_lonlat(x_tile + 1, y_tile, zoom)
    _, south = tile_to_lonlat(x_tile, y_tile + 1, zoom)
    return west, south, east, north


def tile_range(
    west: float, south: float, east: float, north: float, zoom: int
) -> tuple[int, int, int, int]:
    """Inclusive XYZ tile index range ``(x0, x1, y0, y1)`` covering the bbox."""
    n = 2 ** zoom
    x0 = int(math.floor((west + 180.0) / 360.0 * n))
    x1 = int(math.floor((east + 180.0) / 360.0 * n))
    south_c = _clamp_lat(south)
    north_c = _clamp_lat(north)
    y0 = int(
        math.floor(
            (1.0 - math.asinh(math.tan(math.radians(north_c))) / math.pi)
            / 2.0 * n
        )
    )
    y1 = int(
        math.floor(
            (1.0 - math.asinh(math.tan(math.radians(south_c))) / math.pi)
            / 2.0 * n
        )
    )
    return (
        min(max(x0, 0), n - 1),
        min(max(x1, 0), n - 1),
        min(max(y0, 0), n - 1),
        min(max(y1, 0), n - 1),
    )


def auto_zoom(
    west: float,
    south: float,
    east: float,
    north: float,
    width_px: int = 800,
    height_px: int = 600,
    tile_px: int = TILE_SIZE,
    max_tiles: int = 256,
    max_zoom: int = 19,
    min_zoom: int = 0,
) -> int:
    """Finest zoom whose tile count stays within the budget.

    Iterates high→low so the returned zoom is the most detailed that keeps
    ``n_tiles <= max_tiles`` (and no axis wider than 16 tiles).
    """
    y_n, _ = lonlat_to_mercator(west, _clamp_lat(north))
    y_s, _ = lonlat_to_mercator(west, _clamp_lat(south))
    for zoom in range(max_zoom, min_zoom - 1, -1):
        n = 2.0 ** zoom
        nx = max(1, int(math.ceil((east - west) / 360.0 * n)))
        ny = max(1, int(math.ceil((y_n - y_s) / WORLD_MERCATOR_M * n)))
        if nx <= 16 and ny <= 16 and nx * ny <= max_tiles:
            return zoom
    return min_zoom


# ---------------------------------------------------------------------------
# Provider resolution
# ---------------------------------------------------------------------------


def resolve_provider(spec: Any) -> dict[str, str] | None:
    """Normalize a ``basemap`` setting into a ``{url, name, attribution}`` dict.

    Accepts: ``True`` (default Esri imagery), a provider-name string, a raw
    ``http(s)`` tile URL, a ``{url: ..., attribution: ...}`` dict, or a dict
    carrying a ``provider`` key. ``None``/``False`` disable the basemap.
    ``xyzservices`` (when installed) is consulted for named providers not in
    ``DEFAULT_PROVIDERS`` (e.g. ``"Esri.WorldImagery"``).
    """
    if spec is None or spec is False:
        return None
    if spec is True:
        return dict(DEFAULT_PROVIDERS["esri_world_imagery"])
    if isinstance(spec, str):
        key = spec.strip().lower().replace(" ", "_").replace("-", "_")
        if key in DEFAULT_PROVIDERS:
            return dict(DEFAULT_PROVIDERS[key])
        if spec.startswith(("http://", "https://")):
            return {"url": spec, "name": "custom", "attribution": ""}
        return _resolve_xyzservices(spec)
    if isinstance(spec, dict):
        spec = dict(spec)
        if "provider" in spec:
            inner = resolve_provider(spec["provider"])
            if inner is None:
                return None
            inner.update(
                {k: v for k, v in spec.items() if k not in ("provider", "zoom", "alpha")}
            )
            return inner
        url = spec.get("url")
        if not url:
            return None
        return {
            "url": url,
            "name": str(spec.get("name", "custom")),
            "attribution": str(spec.get("attribution", "")),
        }
    return None


def _resolve_xyzservices(name: str) -> dict[str, str] | None:
    try:
        import xyzservices.providers as xyz  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        obj: Any = xyz
        for part in name.split("."):
            obj = getattr(obj, part)
        url: Any = getattr(obj, "url", None)
        if not isinstance(url, str):
            url = obj["url"]  # type: ignore[index]
        attribution = getattr(obj, "attribution", "") or ""
        if not isinstance(attribution, str):
            attribution = str(attribution)
        if not isinstance(url, str) or "{z}" not in url:
            return None
        return {"url": url, "name": name, "attribution": attribution}
    except (AttributeError, KeyError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Fetch + mosaic
# ---------------------------------------------------------------------------


def _tile_url(provider: dict[str, str], zoom: int, x: int, y: int) -> str:
    return provider["url"].format(z=zoom, x=x, y=y)


def _fetch_tile(
    session: requests.Session, url: str, timeout: float
) -> np.ndarray:
    resp = session.get(
        url, timeout=timeout, headers={"User-Agent": USER_AGENT}
    )
    resp.raise_for_status()
    with Image.open(io.BytesIO(resp.content)) as img:
        return np.asarray(img.convert("RGBA"))


def fetch_basemap(
    west: float,
    south: float,
    east: float,
    north: float,
    zoom: int | None = None,
    provider: dict[str, str] | str | None = None,
    width_px: int = 800,
    height_px: int = 600,
    max_tiles: int = 256,
    session: requests.Session | None = None,
    timeout: float = 10.0,
) -> BasemapTiles:
    """Fetch and stitch an XYZ tile mosaic covering the lon/lat bbox.

    ``extent`` of the returned mosaic is a tile-aligned rectangle in lon/lat
    (WGS84 degrees), computed from the fetched tile indices — positionally
    exact for the WGS84 output path; `mosaic_in_output_crs` handles projected
    output CRSs.

    Raises:
        TileFetchError: HTTP/transport failure, budget overflow, or zero tiles
            successfully fetched.
    """
    provider_dict = resolve_provider(provider)
    if provider_dict is None:
        raise TileFetchError("no basemap provider resolved")
    west, east = min(west, east), max(west, east)
    south, north = min(south, north), max(south, north)
    if zoom is None:
        zoom = auto_zoom(
            west, south, east, north, width_px=width_px, height_px=height_px
        )
    x0, x1, y0, y1 = tile_range(west, south, east, north, zoom)
    n_tiles = (x1 - x0 + 1) * (y1 - y0 + 1)
    if n_tiles > max_tiles:
        raise TileFetchError(
            f"bbox needs {n_tiles} tiles at zoom {zoom} (budget {max_tiles}); "
            "pass an explicit lower zoom="
        )
    if session is None:
        session = requests.Session()

    fetched: list[tuple[int, int, np.ndarray]] = []
    errors: list[tuple[int, int, Exception]] = []
    jobs = [
        (x, y, _tile_url(provider_dict, zoom, x, y))
        for x in range(x0, x1 + 1)
        for y in range(y0, y1 + 1)
    ]
    if len(jobs) == 1:
        x, y, url = jobs[0]
        try:
            fetched.append((x, y, _fetch_tile(session, url, timeout)))
        except Exception as exc:  # noqa: BLE001 — transport/HTTP/decoding
            errors.append((x, y, exc))
    else:
        workers = min(MAX_FETCH_WORKERS, len(jobs))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_fetch_tile, session, url, timeout): (x, y)
                for x, y, url in jobs
            }
            for future in as_completed(futures):
                x, y = futures[future]
                try:
                    fetched.append((x, y, future.result()))
                except Exception as exc:  # noqa: BLE001
                    errors.append((x, y, exc))

    if not fetched:
        first = errors[0][2] if errors else RuntimeError("no tiles attempted")
        raise TileFetchError(
            f"all {n_tiles} basemap tile(s) failed (first error: {first}); "
            "is the tile server reachable?"
        )
    if errors:
        missing = sorted(errors)
        warnings.warn(
            f"{len(errors)}/{n_tiles} basemap tile(s) failed; "
            f"rendering with {len(fetched)} tile(s) "
            f"(first failure at tile {missing[0][0]},{missing[0][1]} at "
            f"zoom {zoom}: {missing[0][2]})",
            UserWarning,
            stacklevel=2,
        )

    width_px_total = (x1 - x0 + 1) * TILE_SIZE
    height_px_total = (y1 - y0 + 1) * TILE_SIZE
    mosaic = np.zeros((height_px_total, width_px_total, 4), dtype=np.uint8)
    for x, y, tile in fetched:
        xi, yi = x - x0, y - y0
        mosaic[
            yi * TILE_SIZE : (yi + 1) * TILE_SIZE,
            xi * TILE_SIZE : (xi + 1) * TILE_SIZE,
        ] = tile

    west_m, _ = tile_to_lonlat(x0, y1, zoom)
    east_m, _ = tile_to_lonlat(x1 + 1, y1, zoom)
    _, north_m = tile_to_lonlat(x0, y0, zoom)
    _, south_m = tile_to_lonlat(x0, y1 + 1, zoom)
    extent = (west_m, south_m, east_m, north_m)

    return BasemapTiles(
        image=mosaic,
        extent=extent,
        zoom=zoom,
        provider=provider_dict,
        n_tiles=n_tiles,
    )


# ---------------------------------------------------------------------------
# Output-CRS placement
# ---------------------------------------------------------------------------


def lonlat_bbox_for_crs(
    crs: str, xmin: float, xmax: float, ymin: float, ymax: float
) -> tuple[float, float, float, float] | None:
    """Convert an axis bbox in ``crs`` units to lon/lat, or ``None`` w/o [geo].

    WGS84 output is the identity (axis units are already lon/lat degrees).
    Any other CRS inverse-projects the four corners with pyproj; when pyproj
    is unavailable this returns ``None`` and the caller renders tile-free.
    """
    if crs == WGS84:
        return xmin, ymin, xmax, ymax
    try:
        from pyproj import Transformer  # type: ignore[import-not-found]
    except ImportError:
        return None
    transformer = Transformer.from_crs(crs, WGS84, always_xy=True)
    lons: list[float] = []
    lats: list[float] = []
    for x, y in ((xmin, ymin), (xmin, ymax), (xmax, ymin), (xmax, ymax)):
        lon, lat = transformer.transform(x, y)
        lons.append(lon)
        lats.append(lat)
    return min(lons), min(lats), max(lons), max(lats)


def mosaic_in_output_crs(
    image: np.ndarray,
    extent: tuple[float, float, float, float],
    crs: str,
) -> tuple[np.ndarray, tuple[float, float, float, float]] | None:
    """Express a lon/lat mosaic extent in ``crs`` units, or None without [geo].

    WGS84 output: the extent is already in data units. A projected output CRS
    gets the tile-aligned lon/lat extent projected through its corners and
    axis-aligned to ``(xmin, xmax, ymin, ymax)`` — positionally exact for the
    WGS84 path and an affine approximation for projected frames (fine at
    site extents; true reprojection is a later refinement).
    """
    if crs == WGS84:
        return image, extent
    try:
        from pyproj import Transformer  # type: ignore[import-not-found]
    except ImportError:
        return None
    west, south, east, north = extent
    transformer = Transformer.from_crs(WGS84, crs, always_xy=True)
    xs: list[float] = []
    ys: list[float] = []
    for lon, lat in (
        (west, south),
        (west, north),
        (east, south),
        (east, north),
    ):
        x, y = transformer.transform(lon, lat)
        xs.append(x)
        ys.append(y)
    return image, (min(xs), min(ys), max(xs), max(ys))