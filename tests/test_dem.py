"""
Phase 18.2 wp1: terrain-tile DEM module (`io/dem.py`).

Covers the terrarium decode formula (incl. nodata/water → NaN and the
elevation-band clip), the local closed-form Web-Mercator math, zoom/resolution
selection, the bbox buffer (old-geomapper parity), the stitched mosaic
fetcher (fake sessions — no network), the per-tile cache, and the
all-failed/partial-failure degrade semantics.
"""

from __future__ import annotations

import io
import math

import numpy as np
import pytest
import requests
from PIL import Image

import geofig_engine.io.dem as dem_mod
from geofig_engine.io.dem import (
    DemGrid,
    TileFetchError,
    auto_zoom_lonlat,
    decode_terrarium,
    dem_cache_dir,
    dem_tile_range,
    fetch_dem,
    lonlat_to_mercator,
    pixel_resolution,
    tile_bounds,
    tile_to_lonlat,
)


def _encode_meters(value: float) -> tuple[int, int, int]:
    """RGB tuple whose terrarium decode equals ``value`` (b channel = 0)."""
    t = int(round(value)) + 32768
    r = (t >> 8) & 0xFF
    g = t & 0xFF
    return r, g, 0


def _tile_png_bytes(rgb) -> bytes:
    """A 256x256 solid-color RGB tile as PNG bytes (PIL-built, offline)."""
    buf = io.BytesIO()
    Image.new("RGB", (dem_mod.TILE_SIZE, dem_mod.TILE_SIZE), rgb).save(
        buf, format="PNG"
    )
    return buf.getvalue()


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        pass


class FakeSession:
    """Returns a decoded-1000 m solid tile for every requested URL."""

    def __init__(self, value: float = 1000.0) -> None:
        self.rgb = _encode_meters(value)
        self.requested: list[str] = []

    def get(self, url, timeout=None, headers=None):
        self.requested.append(url)
        return FakeResponse(_tile_png_bytes(self.rgb))


def _site_bbox() -> tuple[float, float, float, float]:
    """A site-scale bbox around the example wells (~0.1° span)."""
    return -116.55, 41.18, -116.24, 41.36


def _single_tile_bbox() -> tuple[float, float, float, float]:
    """A bbox that lands inside exactly one tile at the test zooms."""
    return -116.55, 41.30, -116.48, 41.34


class TestDecode:
    def test_zero_pixel_is_nodata(self):
        z = decode_terrarium(np.zeros((2, 2, 3), dtype=np.uint8))
        assert np.isnan(z).all()

    def test_mid_gray_round_trip(self):
        # (128, 128, 128) decodes to 128*256 + 128 + 128/256 - 32768 = 128.5
        arr = np.full((1, 1, 3), 128, dtype=np.uint8)
        assert decode_terrarium(arr)[0, 0] == 128.5

    def test_color_ramp_round_trip(self):
        for value in (-500, 0, 500, 1000, 2500, 6000):
            rgb = _encode_meters(value)
            arr = np.array([[rgb]], dtype=np.uint8)
            assert decode_terrarium(arr)[0, 0] == value

    def test_rgba_accepted_alpha_ignored(self):
        rgb = _encode_meters(500)
        arr = np.array([[*rgb, 0]], dtype=np.uint8).reshape(1, 1, 4)
        assert decode_terrarium(arr)[0, 0] == 500

    def test_elevation_band_clip(self):
        rgb_low = _encode_meters(-800)  # below ELEVATION_BAND[0] = -500
        rgb_high = _encode_meters(12000)  # above ELEVATION_BAND[1] = 9000
        arr = np.array([[rgb_low], [rgb_high]], dtype=np.uint8).reshape(2, 1, 3)
        out = decode_terrarium(arr)
        assert out[0, 0] == -500.0
        assert out[1, 0] == 9000.0

    def test_wrong_ndim_rejected(self):
        with pytest.raises(ValueError, match="RGB"):
            decode_terrarium(np.zeros((3, 3), dtype=np.uint8))


class TestMercatorMath:
    def test_mercator_origin(self):
        x, y = lonlat_to_mercator(0.0, 0.0)
        # Float noise only: tan(pi/4) is 0.9999999999999999 in IEEE754.
        assert abs(x) < 1e-12 and abs(y) < 1e-9

    def test_mercator_round_trip(self):
        lon, lat = 12.5, 41.2
        x, y = lonlat_to_mercator(lon, lat)
        lon_recovered = math.degrees(x / dem_mod.WEB_MERCATOR_R)
        assert abs(lon_recovered - lon) < 1e-9
        lat_recovered = math.degrees(
            2.0 * math.atan(math.exp(y / dem_mod.WEB_MERCATOR_R))
            - math.pi / 2.0
        )
        assert abs(lat_recovered - lat) < 1e-9

    def test_tile_to_lonlat_corners(self):
        west, north = tile_to_lonlat(0, 0, 0)
        assert west == -180.0
        assert abs(north - dem_mod.MAX_LAT) < 1e-9
        east, south = tile_to_lonlat(1, 1, 0)
        assert east == 180.0
        assert abs(south + dem_mod.MAX_LAT) < 1e-9

    def test_tile_bounds_shared_edges(self):
        _, south_upper, _, _ = tile_bounds(1, 2, 4)
        _, _, _, north_lower = tile_bounds(1, 3, 4)
        assert south_upper == north_lower

    def test_tile_range_world(self):
        assert dem_tile_range(-180.0, -85.0, 180.0, 85.0, 0) == (0, 0, 0, 0)
        assert dem_tile_range(-180.0, -85.0, 180.0, 85.0, 1) == (0, 1, 0, 1)

    def test_tile_range_bounds_contain_bbox(self):
        west, south, east, north = _site_bbox()
        x0, x1, y0, y1 = dem_tile_range(west, south, east, north, 12)
        w, s, _, _ = tile_bounds(x0, y1, 12)
        assert w <= west and s <= south
        _, _, e, n = tile_bounds(x1, y0, 12)
        assert e >= east and n >= north

    def test_lat_clamp(self):
        # 89°N clamps to the top row (y=0) at zoom 2.
        assert dem_tile_range(-10.0, 89.0, 10.0, 89.0, 2) == (1, 2, 0, 0)


class TestAutoZoom:
    def test_resolution_met_within_budget_for_tiny_extent(self):
        zoom = auto_zoom_lonlat(
            -0.005, -0.005, 0.005, 0.005, interval=10.0
        )
        # target = max(5, 10/3) = 5 m/px → the finest terrarium zoom (15,
        # ~4.8 m/px) fits a 0.01° bbox in one tile.
        assert zoom == 15
        assert pixel_resolution(zoom) <= 5.0

    def test_resolution_preferred_when_affordable(self):
        # Site-scale bbox with a generous budget (z15 fits 638 tiles): the
        # resolution-preference pass wins over the budget fallback.
        zoom = auto_zoom_lonlat(*_site_bbox(), max_tiles=700)
        assert zoom == 15

    def test_budget_bounded_when_resolution_infeasible(self):
        # World bbox within terrarium zoom 6..15: every zoom busts the 64-tile
        # budget before the 5 m/px target is met, so the documented fallback
        # (min_zoom=6) is returned.
        zoom = auto_zoom_lonlat(-179.0, -80.0, 179.0, 80.0, max_tiles=64)
        assert zoom == 6

    def test_site_scale_extent_stays_detailed(self):
        # ~0.31° x 0.18° extent: within the default 64-tile budget the finest
        # zoom that can be afforded (z14, ~30 tiles, ~9.6 m/px) is selected.
        zoom = auto_zoom_lonlat(*_site_bbox())
        assert 12 <= zoom <= 14
        x0, x1, y0, y1 = dem_tile_range(*_site_bbox(), zoom)
        assert (x1 - x0 + 1) * (y1 - y0 + 1) <= 64


class TestFetchDem:
    @pytest.fixture(autouse=True)
    def _isolated_cache(self, monkeypatch, tmp_path):
        # Each test gets a fresh cache dir: previously-written tiles must not
        # satisfy later network assertions across test runs.
        monkeypatch.setattr(dem_mod, "_DEM_CACHE_DIR", tmp_path)

    def test_single_tile_mosaic(self):
        session = FakeSession(value=1000.0)
        grid = fetch_dem(*_single_tile_bbox(), zoom=10, session=session)
        assert isinstance(grid, DemGrid)
        assert grid.z.shape == (dem_mod.TILE_SIZE, dem_mod.TILE_SIZE)
        assert len(session.requested) == 1
        assert np.allclose(grid.z, 1000.0)
        # lon increases west→east, lat decreases north→south
        assert grid.lon[0, -1] > grid.lon[0, 0]
        assert grid.lat[0, 0] > grid.lat[-1, 0]

    def test_grid_dimensions_2d(self):
        session = FakeSession()
        grid = fetch_dem(*_single_tile_bbox(), zoom=10, session=session)
        assert grid.lon.ndim == 2 and grid.lat.ndim == 2 and grid.z.ndim == 2
        assert grid.lon.shape == grid.z.shape == (256, 256)

    def test_multi_tile_mosaic_aligned(self):
        session = FakeSession(value=2500.0)
        grid = fetch_dem(-180.0, -85.0, 180.0, 85.0, zoom=1, session=session)
        assert grid.z.shape == (512, 512)
        assert len(session.requested) == 4  # 2x2 world at zoom 1
        assert np.allclose(grid.z, 2500.0)
        assert grid.lon[0, 0] < grid.lon[0, -1]

    def test_zoom_passthrough_used_in_url(self):
        session = FakeSession()
        fetch_dem(*_site_bbox(), zoom=7, session=session)
        assert all("/7/" in url for url in session.requested)

    def test_bbox_buffer_applied(self, monkeypatch):
        # Old-geomapper parity: fetch_dem buffers the bbox by 10% of its span
        # before resolving the tile range. Record what the range sees.
        seen = {}

        def recorder(west, south, east, north, zoom):
            seen["bbox"] = (west, south, east, north)
            return orig_range(west, south, east, north, zoom)

        orig_range = dem_mod.dem_tile_range
        monkeypatch.setattr(dem_mod, "dem_tile_range", recorder)
        session = FakeSession()
        fetch_dem(-116.5, 41.20, -116.4, 41.25, zoom=10, session=session)
        west, south, east, north = seen["bbox"]
        assert abs(west - (-116.5 - 0.01)) < 1e-9
        assert abs(east - (-116.4 + 0.01)) < 1e-9
        assert abs(south - (41.20 - 0.005)) < 1e-9
        assert abs(north - (41.25 + 0.005)) < 1e-9

    def test_degenerate_bbox_raises(self):
        with pytest.raises(ValueError, match="non-degenerate"):
            fetch_dem(-116.5, 41.2, -116.5, 41.2, zoom=10, session=FakeSession())

    def test_all_tiles_failed_raises(self):
        class ExplodingSession(FakeSession):
            def get(self, url, timeout=None, headers=None):
                self.requested.append(url)
                raise requests.RequestException("boom")

        session = ExplodingSession()
        with pytest.raises(TileFetchError, match="all"):
            fetch_dem(*_site_bbox(), zoom=10, session=session)
        assert session.requested

    def test_partial_failure_warns_and_keeps_survivors(self):
        class PartialSession(FakeSession):
            def get(self, url, timeout=None, headers=None):
                self.requested.append(url)
                if len(self.requested) % 3 == 0:
                    raise requests.RequestException("sporadic")
                return FakeResponse(_tile_png_bytes(_encode_meters(500.0)))

        with pytest.warns(UserWarning, match="tile"):
            grid = fetch_dem(-180.0, -85.0, 180.0, 85.0, zoom=1,
                             session=PartialSession())
        assert grid.z.shape == (512, 512)
        assert np.isnan(grid.z).any()  # failed tile(s) left as NaN
        assert np.nanmax(grid.z) == 500.0  # survivors painted


class TestCache:
    def test_cached_tiles_skip_network(self, tmp_path):
        session = FakeSession(value=1000.0)
        first = fetch_dem(
            *_single_tile_bbox(), zoom=10, session=session, cache_dir=tmp_path
        )
        assert len(session.requested) == 1
        cached = (tmp_path / "terrarium" / "10").glob("*/*.png")
        assert sum(1 for _ in cached) == 1

        counting = FakeSession()
        second = fetch_dem(
            *_single_tile_bbox(), zoom=10, session=counting, cache_dir=tmp_path
        )
        assert counting.requested == []  # all tiles served from cache
        assert np.array_equal(first.z, second.z, equal_nan=True)

    def test_cache_dir_override_sentinel(self, tmp_path):
        dem_mod._DEM_CACHE_DIR = tmp_path
        try:
            assert dem_cache_dir() == tmp_path
        finally:
            dem_mod._DEM_CACHE_DIR = None

    def test_cache_dir_env_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEOFIG_DEM_CACHE", str(tmp_path))
        dem_mod._DEM_CACHE_DIR = None
        try:
            assert dem_cache_dir() == tmp_path
        finally:
            dem_mod._DEM_CACHE_DIR = None

    def test_requests_and_pil_imports_are_lazy(self):
        # The module must import cleanly without requests/PIL — it does (this
        # import already ran at collection); the fetch path alone touches them.
        assert "requests" not in dem_mod.__dict__
        assert "PIL" not in dem_mod.__dict__