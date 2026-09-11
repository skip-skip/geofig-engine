"""
AWS Terrain Tiles (terrarium) DEM access for geofig_engine (Phase 18.2, wp1).

A self-contained DEM fetcher replicating the old geomapper's DEM recipe
(``../geochemmapper.py`` ``MapBuilder.download_dem``: bounds → 10% lon/lat
buffer, extent-keyed local cache) **without** the elevation/GDAL/rasterio
stack: Web-Mercator XYZ elevation tiles from the AWS Open Data Terrain Tiles
bucket are fetched with ``requests`` + ``Pillow``, decoded to meters, and
stitched into a lon/lat grid.

    TERRAIN_URL = https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png

Terrarium encoding (per pixel, RGB):

    alt = (r * 256 + g + b / 256) - 32768        [meters]

Pixels that decode to exactly -32768 are the tiles' nodata/water marker and
become ``np.nan``; surviving values are clipped to a sane elevation band.

Layering: this is an **io-layer** module — no imports from ``renderers.*``
(the wp14 basemap module keeps its own copies of the closed-form Web-Mercator
math; equivalent local copies live here so ``io`` never depends on a
renderer). ``requests``/``PIL`` are imported lazily inside the functions, so
a pure-offline ``import geofig_engine.io.dem`` succeeds without them.
"""

from __future__ import annotations

import math
import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

TILE_SIZE = 256
"""XYZ tile edge length in pixels."""

MAX_LAT = 85.05112878
"""Web-Mercator latitude clamp (slippy-map spec)."""

WEB_MERCATOR_R = 6378137.0
"""Web-Mercator sphere radius (WGS84 semi-major axis, meters)."""

WORLD_MERCATOR_M = 2.0 * math.pi * WEB_MERCATOR_R
"""Full Web-Mercator world width/height in meters."""

USER_AGENT = "geofig-engine/0.3 (declarative site_map dem)"

TERRARIUM_URL = (
    "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
)
"""AWS Open Data terrain-tile endpoint (terrarium SRTM encoding)."""

TERRARIUM_NODATA = -32768.0
"""Decoded elevation marking nodata/water in terrarium tiles."""

ELEVATION_BAND = (-500.0, 9000.0)
"""Sane elevation band (m): decoded values are clipped to this range."""

DEM_TILE_BUDGET = 64
"""Default tile budget for :func:`auto_zoom_lonlat` / :func:`fetch_dem`."""

MIN_ZOOM = 6
"""Coarsest terrarium zoom considered by auto-zoom (SRTM useful range)."""

MAX_ZOOM = 15
"""Finest zoom the terrarium dataset publishes."""

_DEM_CACHE_DIR: Path | None = None
"""Module-level cache-dir override for tests (see :func:`dem_cache_dir`)."""


class TileFetchError(RuntimeError):
    """Raised when a DEM tile mosaic cannot be fetched/assembled."""


@dataclass(frozen=True)
class DemGrid:
    """A stitched DEM mosaic positioned on a lon/lat grid.

    ``lon``/``lat`` are 2-D grids (broadcast over the mosaic's pixels
    north→south, west→east) and ``z`` the elevation in meters with
    ``np.nan`` for nodata/water or failed tiles.
    """

    lon: np.ndarray
    lat: np.ndarray
    z: np.ndarray


def dem_cache_dir() -> Path:
    """Per-tile PNG cache root: env override, then ``~/.cache/geofig_engine/dem``.

    ``GEOFIG_DEM_CACHE`` (an env var) or the module-level ``_DEM_CACHE_DIR``
    sentinel (tests) override the home-directory default. Tile files live
    under ``<root>/terrarium/{z}/{x}/{y}.png`` (mirrors the XYZ URL layout).
    """
    if _DEM_CACHE_DIR is not None:
        return _DEM_CACHE_DIR
    env = os.environ.get("GEOFIG_DEM_CACHE")
    if env:
        return Path(env)
    return Path.home() / ".cache" / "geofig_engine" / "dem"


# ---------------------------------------------------------------------------
# Closed-form Web-Mercator math (local copies — no renderer imports)
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


def dem_tile_range(
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


def pixel_resolution(zoom: int) -> float:
    """Web-Mercator meters per tile pixel at ``zoom`` (SRTM-ish metric)."""
    return (WORLD_MERCATOR_M / (2.0 ** zoom)) / TILE_SIZE


def auto_zoom_lonlat(
    west: float,
    south: float,
    east: float,
    north: float,
    interval: float = 10.0,
    max_tiles: int = DEM_TILE_BUDGET,
    max_zoom: int = MAX_ZOOM,
    min_zoom: int = MIN_ZOOM,
) -> int:
    """Finest zoom whose tile count is affordable, preferring the resolution.

    The resolution target is ``max(5, interval / 3)`` meters per pixel (a
    contour-sourced preference; the SRTM source is ~30 m). Scan high→low:

    1. return the most detailed zoom meeting **both** the resolution target
       and the ``max_tiles`` budget;
    2. otherwise return the most detailed zoom within the budget alone (the
       budget is the binding constraint — a site-scale extent still gets the
       finest affordable detail even when the target resolution is
       infeasible in-budget);
    3. degrade to ``min_zoom`` only when even that exceeds the budget.
    """
    target = max(5.0, float(interval) / 3.0)
    west, east = min(west, east), max(west, east)
    south, north = min(south, north), max(south, north)
    budget_zoom: int | None = None
    for zoom in range(max_zoom, min_zoom - 1, -1):
        x0, x1, y0, y1 = dem_tile_range(west, south, east, north, zoom)
        count = (x1 - x0 + 1) * (y1 - y0 + 1)
        if count <= max_tiles:
            if pixel_resolution(zoom) <= target:
                return zoom
            if budget_zoom is None:  # first (finest) affordable hit
                budget_zoom = zoom
    if budget_zoom is not None:
        return budget_zoom
    return min_zoom


# ---------------------------------------------------------------------------
# Terrarium decoding
# ---------------------------------------------------------------------------


def decode_terrarium(image: np.ndarray) -> np.ndarray:
    """Decode a terrarium RGB(A) tile to meters (2-D ``float64``).

    ``alt = (r * 256 + g + b / 256) - 32768`` per pixel; decoded ``-32768``
    (nodata/water) becomes ``np.nan``, then values are clipped to
    :data:`ELEVATION_BAND`.
    """
    arr = np.asarray(image)
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise ValueError(
            "decode_terrarium expects an (H, W, 3+) RGB(A) array, "
            f"got shape {arr.shape}"
        )
    rgb = arr[..., :3].astype(np.float64)
    z = rgb[..., 0] * 256.0 + rgb[..., 1] + rgb[..., 2] / 256.0 - 32768.0
    z = np.where(z == TERRARIUM_NODATA, np.nan, z)
    lo, hi = ELEVATION_BAND
    return np.clip(z, lo, hi)


# ---------------------------------------------------------------------------
# Fetch + mosaic
# ---------------------------------------------------------------------------


def _load_tile_image(data: bytes) -> np.ndarray:
    """PNG bytes → (H, W, 4) RGBA uint8 array (lazy PIL import)."""
    import io

    from PIL import Image

    with Image.open(io.BytesIO(data)) as img:
        return np.asarray(img.convert("RGBA"))


def _grid_for_range(
    x0: int, x1: int, y0: int, y1: int, zoom: int
) -> tuple[np.ndarray, np.ndarray]:
    """2-D lon/lat grids for the mosaic covering tile range ``(x0..x1, y0..y1)``.

    Lon is linear across the mosaic (Web-Mercator x is linear in lon); the
    lat grid uses the slippy-map inverse per pixel row (lat is *not* linear
    in pixel row — the closed form is evaluated per row, not interpolated).
    """
    n = 2.0 ** zoom
    width = (x1 - x0 + 1) * TILE_SIZE
    height = (y1 - y0 + 1) * TILE_SIZE

    px = np.arange(width, dtype=np.float64) + x0 * TILE_SIZE + 0.5
    lon_1d = px / (n * TILE_SIZE) * 360.0 - 180.0

    py = np.arange(height, dtype=np.float64) + y0 * TILE_SIZE + 0.5
    frac = py / (n * TILE_SIZE)
    lat_1d = np.degrees(np.arctan(np.sinh(math.pi * (1.0 - 2.0 * frac))))

    lon = np.broadcast_to(lon_1d, (height, width))
    lat = np.broadcast_to(lat_1d[:, None], (height, width))
    return np.ascontiguousarray(lon), np.ascontiguousarray(lat)


def fetch_dem(
    west: float,
    south: float,
    east: float,
    north: float,
    interval: float = 10.0,
    zoom: int | None = None,
    session: Any | None = None,
    timeout: float = 10.0,
    cache_dir: Path | str | None = None,
) -> DemGrid:
    """Fetch and stitch a terrarium DEM covering the lon/lat bbox.

    Applies a **10% lon/lat buffer** around the requested bbox (old-geomapper
    parity), resolves ``zoom`` (:func:`auto_zoom_lonlat` with ``interval``
    unless given), and fetches missing tiles only — per-tile PNGs are cached
    under ``cache_dir or dem_cache_dir()/terrarium/{z}/{x}/{y}.png``, so a
    cached tile is read from disk instead of the network.

    Args:
        west/south/east/north: bbox in WGS84 degrees (order-agnostic).
        interval: contour interval in meters (drives auto-zoom resolution).
        zoom: explicit XYZ zoom (default auto).
        session: ``requests.Session``-like object (any object with a
            ``get(url, timeout=, headers=)`` returning
            ``{content, raise_for_status()}``); a real session is created
            when ``None``.
        timeout: per-tile request timeout in seconds.
        cache_dir: cache root override (defaults to :func:`dem_cache_dir`).

    Returns:
        :class:`DemGrid` with 2-D lon/lat grids and the elevation mosaic
        (``np.nan`` for nodata/water and failed tiles).

    Raises:
        ValueError: degenerate bbox (zero width and height).
        TileFetchError: every requested tile failed to load/fetch.
    """
    west, east = min(west, east), max(west, east)
    south, north = min(south, north), max(south, north)
    if (east - west) < 1e-12 and (north - south) < 1e-12:
        raise ValueError(
            "fetch_dem requires a non-degenerate lon/lat bbox "
            f"(got {west},{south},{east},{north})"
        )

    # Old-geomapper parity: buffer the fetch extent by 10% of its span.
    lon_buf = max(0.001, (east - west) * 0.1)
    lat_buf = max(0.001, (north - south) * 0.1)
    west -= lon_buf
    east += lon_buf
    south -= lat_buf
    north += lat_buf

    if zoom is None:
        zoom = auto_zoom_lonlat(
            west, south, east, north, interval=float(interval)
        )
    x0, x1, y0, y1 = dem_tile_range(west, south, east, north, zoom)
    cache = Path(cache_dir) if cache_dir is not None else dem_cache_dir()

    if session is None:
        import requests

        session = requests.Session()

    n_tiles = (x1 - x0 + 1) * (y1 - y0 + 1)
    height = (y1 - y0 + 1) * TILE_SIZE
    width = (x1 - x0 + 1) * TILE_SIZE
    z = np.full((height, width), np.nan, dtype=np.float64)

    errors: list[tuple[int, int, Exception]] = []
    fetched = 0
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            url = TERRARIUM_URL.format(z=zoom, x=tx, y=ty)
            tile_path = cache / "terrarium" / str(zoom) / str(tx) / f"{ty}.png"
            try:
                if tile_path.exists():
                    data = tile_path.read_bytes()
                else:
                    resp = session.get(
                        url, timeout=timeout, headers={"User-Agent": USER_AGENT}
                    )
                    resp.raise_for_status()
                    data = resp.content
                    tile_path.parent.mkdir(parents=True, exist_ok=True)
                    tile_path.write_bytes(data)
                decoded = decode_terrarium(_load_tile_image(data))
                rows = (ty - y0) * TILE_SIZE
                cols = (tx - x0) * TILE_SIZE
                z[rows : rows + TILE_SIZE, cols : cols + TILE_SIZE] = decoded
                fetched += 1
            except Exception as exc:  # noqa: BLE001 — transport/HTTP/decoding
                errors.append((tx, ty, exc))

    if fetched == 0:
        first = errors[0][2] if errors else RuntimeError("no tiles attempted")
        raise TileFetchError(
            f"all {n_tiles} DEM tile(s) failed (first error: {first}); "
            "is the terrain-tile server reachable?"
        )
    if errors:
        missing = sorted((x, y) for x, y, _ in errors)
        warnings.warn(
            f"{len(errors)}/{n_tiles} DEM tile(s) failed; "
            f"using {fetched} tile(s) (first failure at tile "
            f"{missing[0][0]},{missing[0][1]} at zoom {zoom}: "
            f"{errors[0][2]})",
            UserWarning,
            stacklevel=2,
        )

    lon, lat = _grid_for_range(x0, x1, y0, y1, zoom)
    return DemGrid(lon=lon, lat=lat, z=z)