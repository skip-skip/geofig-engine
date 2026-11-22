"""
Phase 15 wp14: site_map basemap tiles.

Covers the closed-form Web-Mercator math, provider resolution, the mosaic
fetcher (fake session — no network), the renderer integration (monkeypatched
fetch), the opt-out path, and the pyproj gates for projected output CRSs.
"""

from __future__ import annotations

import importlib.util
import io
import math

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest
import requests
from PIL import Image

import geofig_engine.renderers.matplotlib.basemap as basemap_mod
from geofig_engine import render_template
from geofig_engine.core.coord import CoordFlipped, CoordGeo
from geofig_engine.templates.site_map import site_map_builder
from geofig_engine.renderers.matplotlib.basemap import (
    DEFAULT_PROVIDERS,
    BasemapTiles,
    TileFetchError,
    auto_zoom,
    fetch_basemap,
    lonlat_bbox_for_crs,
    lonlat_to_mercator,
    mosaic_in_output_crs,
    resolve_provider,
    tile_bounds,
    tile_range,
    tile_to_lonlat,
)

GEO_INSTALLED = importlib.util.find_spec("pyproj") is not None


class _FlippedGeo(CoordGeo, CoordFlipped):
    """Test coord that exercises the renderer's flipped-limit branch."""

    def __init__(self) -> None:
        object.__setattr__(self, "crs", "EPSG:4326")
        object.__setattr__(self, "bounds", None)
        object.__setattr__(self, "bounds_crs", None)
        object.__setattr__(self, "aspect", None)
        object.__setattr__(self, "name", "geo")
        object.__setattr__(self, "params", {"crs": "EPSG:4326"})


SAMPLE_DF = pd.DataFrame(
    {
        "longitude": [-116.5, -116.4, -116.3, -116.2],
        "latitude": [41.2, 41.1, 41.0, 40.9],
        "facility": ["A", "A", "B", "B"],
        "name": ["MW-1", "MW-2", "MW-3", "MW-4"],
    }
)


def _tile_png_bytes(rgb) -> bytes:
    """A 256x256 solid-color RGBA tile as PNG bytes (PIL-built, offline)."""
    buf = io.BytesIO()
    Image.new("RGB", (basemap_mod.TILE_SIZE, basemap_mod.TILE_SIZE), rgb).save(
        buf, format="PNG"
    )
    return buf.getvalue()


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        pass


class FakeSession:
    """Returns a solid tile for every requested URL."""

    def __init__(self, rgb=(200, 0, 0)) -> None:
        self.rgb = rgb
        self.requested: list[str] = []

    def get(self, url, timeout=None, headers=None):
        self.requested.append(url)
        return FakeResponse(_tile_png_bytes(self.rgb))


def _tile_center_bbox(zoom: int) -> tuple[float, float, float, float]:
    """A bbox strictly inside the central tile at ``zoom`` (seam-free)."""
    n = 2**zoom
    lon, lat = tile_to_lonlat(n // 2 + 0.5, n // 2 + 0.5, zoom)
    return lon - 0.0001, lat - 0.0001, lon + 0.0001, lat + 0.0001


class TestMercatorMath:
    def test_mercator_origin(self):
        x, y = lonlat_to_mercator(0.0, 0.0)
        # Float noise only: tan(pi/4) is 0.9999999999999999 in IEEE754.
        assert abs(x) < 1e-12 and abs(y) < 1e-9

    def test_mercator_round_trip(self):
        lon, lat = 12.5, 41.2
        x, y = lonlat_to_mercator(lon, lat)
        # x is radians * R: recover lon via x / (R * pi/180)
        lon_recovered = math.degrees(x / basemap_mod.WEB_MERCATOR_R)
        assert abs(lon_recovered - lon) < 1e-9
        # y = R * ln(tan(pi/4 + phi/2)); inverse recovers latitude
        lat_recovered = math.degrees(
            2.0 * math.atan(math.exp(y / basemap_mod.WEB_MERCATOR_R))
            - math.pi / 2.0
        )
        assert abs(lat_recovered - lat) < 1e-9

    def test_tile_range_world(self):
        assert tile_range(-180.0, -85.0, 180.0, 85.0, 0) == (0, 0, 0, 0)
        x0, x1, y0, y1 = tile_range(-180.0, -85.0, 180.0, 85.0, 1)
        assert (x0, x1, y0, y1) == (0, 1, 0, 1)

    def test_tile_range_bounds_contain_bbox(self):
        west, south, east, north = -116.6, 40.8, -116.1, 41.3
        x0, x1, y0, y1 = tile_range(west, south, east, north, 12)
        w, s, _, _ = tile_bounds(x0, y1, 12)
        assert w <= west and s <= south
        _, _, e, n = tile_bounds(x1, y0, 12)
        assert e >= east and n >= north

    def test_tile_bounds_adjacent_tiles_share_edges(self):
        # Vertical neighbors: the SOUTH edge of the y=2 tile is the NORTH
        # edge of the y=3 tile (y grows southward in XYZ notation).
        _, south_upper, _, _ = tile_bounds(1, 2, 4)
        _, _, _, north_lower = tile_bounds(1, 3, 4)
        assert south_upper == north_lower

    def test_auto_zoom_respects_budget(self):
        west, south, east, north = -116.6, 40.8, -116.1, 41.3
        zoom = auto_zoom(west, south, east, north, width_px=800, height_px=600)
        x0, x1, y0, y1 = tile_range(west, south, east, north, zoom)
        assert (x1 - x0 + 1) * (y1 - y0 + 1) <= 256
        assert zoom >= 10  # site-scale extent gets a detailed zoom

    def test_auto_zoom_coarse_for_large_extent(self):
        assert auto_zoom(-179.0, -80.0, 179.0, 80.0, 800, 600) <= 4

    def test_lat_clamp(self):
        x0, x1, y0, y1 = tile_range(-10.0, 89.0, 10.0, 89.0, 2)
        assert y0 == 0  # clamped to the top row
        assert y1 == 0


class TestProviderResolution:
    def test_true_resolves_default_esri(self):
        prov = resolve_provider(True)
        assert prov["name"] == "esri_world_imagery"
        assert "{z}" in prov["url"]

    def test_named_provider(self):
        assert resolve_provider("osm")["name"] == "osm"

    def test_xyzservices_lookup_lenient(self):
        # "Esri.WorldImagery" resolves only when xyzservices is importable;
        # otherwise it degrades to the None/no-tile path.
        prov = resolve_provider("Esri.WorldImagery")
        assert prov is None or "{z}" in prov["url"]

    def test_raw_url_and_dict(self):
        url = "https://example.test/tiles/{z}/{x}/{y}.png"
        assert resolve_provider(url)["url"] == url
        assert resolve_provider({"url": url, "attribution": "X"})["url"] == url

    def test_provider_dict_form(self):
        prov = resolve_provider({"provider": "osm", "zoom": 14, "alpha": 0.5})
        assert prov["name"] == "osm"
        assert "zoom" not in prov and "alpha" not in prov

    def test_disabled(self):
        assert resolve_provider(None) is None
        assert resolve_provider(False) is None


class TestFetchBasemap:
    @pytest.mark.parametrize("zoom", [1, 8, 14])
    def test_mosaic_single_tile(self, zoom):
        session = FakeSession(rgb=(0, 128, 255))
        bbox = _tile_center_bbox(zoom)
        tiles = fetch_basemap(
            *bbox, zoom=zoom, provider="osm", session=session
        )
        assert isinstance(tiles, BasemapTiles)
        assert tiles.image.shape == (
            basemap_mod.TILE_SIZE,
            basemap_mod.TILE_SIZE,
            4,
        )
        assert tiles.n_tiles == 1
        assert len(session.requested) == 1
        assert tiles.image[0, 0].tolist()[:3] == [0, 128, 255]
        west, south, east, north = tiles.extent
        assert west < east and south < north

    def test_mosaic_multiple_tiles_aligned(self):
        session = FakeSession(rgb=(10, 20, 30))
        tiles = fetch_basemap(
            0.0, 0.0, 100.0, 60.0, zoom=4, provider="osm", session=session
        )
        assert tiles.n_tiles > 1
        assert tiles.n_tiles <= 256  # within the default budget
        assert tiles.image.shape[0] % basemap_mod.TILE_SIZE == 0
        assert tiles.image.shape[1] % basemap_mod.TILE_SIZE == 0
        w, s, e, n = tiles.extent
        assert w <= 0.0 and e >= 100.0 and s <= 0.0 and n >= 60.0

    def test_auto_zoom_large_bbox_raises_before_fetch(self):
        # World-scale bbox at max zoom would need an absurd tile count: the
        # budget guard must fire without any network attempt.
        session = FakeSession()
        with pytest.raises(TileFetchError, match="budget"):
            fetch_basemap(
                -179.0,
                -80.0,
                179.0,
                80.0,
                zoom=19,
                provider="osm",
                session=session,
                max_tiles=64,
            )
        assert session.requested == []

    def test_all_tiles_failed_raises(self):
        class ExplodingSession(FakeSession):
            def get(self, url, timeout=None, headers=None):
                self.requested.append(url)
                raise requests.RequestException("boom")

        session = ExplodingSession()
        with pytest.raises(TileFetchError, match="all"):
            fetch_basemap(
                -0.01,
                -0.01,
                0.01,
                0.01,
                zoom=10,
                provider="osm",
                session=session,
            )
        assert session.requested

    def test_partial_failure_warns_and_renders_rest(self):
        class PartialSession(FakeSession):
            def get(self, url, timeout=None, headers=None):
                self.requested.append(url)
                if len(self.requested) % 3 == 0:
                    raise requests.RequestException("sporadic")
                return FakeResponse(_tile_png_bytes((0, 200, 0)))

        with pytest.warns(UserWarning, match="tile"):
            tiles = fetch_basemap(
                0.0, 0.0, 100.0, 60.0, zoom=4, provider="osm", session=PartialSession()
            )
        assert tiles.n_tiles > 1
        assert tiles.image.any()  # surviving tiles still painted


class TestOutputCrs:
    def test_wgs84_identity(self):
        img = np.zeros((2, 2, 4), dtype=np.uint8)
        extent = (-1.0, 1.0, 2.0, 3.0)
        out = mosaic_in_output_crs(img, extent, "EPSG:4326")
        assert out == (img, extent)
        assert lonlat_bbox_for_crs("EPSG:4326", 1, 2, 3, 4) == (1, 3, 2, 4)

    @pytest.mark.skipif(GEO_INSTALLED, reason="requires absent [geo] extra")
    def test_projected_without_pyproj_returns_none(self):
        assert lonlat_bbox_for_crs("EPSG:32612", 1, 2, 3, 4) is None
        assert (
            mosaic_in_output_crs(
                np.zeros((2, 2, 4), dtype=np.uint8), (0, 0, 1, 1), "EPSG:32612"
            )
            is None
        )

    @pytest.mark.skipif(not GEO_INSTALLED, reason="requires [geo] extra")
    def test_projected_with_pyproj_projects_corners(self):
        bbox = lonlat_bbox_for_crs(
            "EPSG:32612", 500000.0, 510000.0, 4500000.0, 4510000.0
        )
        assert bbox is not None
        west, south, east, north = bbox
        assert west < east and south < north
        img = np.zeros((2, 2, 4), dtype=np.uint8)
        out = mosaic_in_output_crs(img, (west, south, east, north), "EPSG:32612")
        assert out is not None
        x_min, y_min, x_max, y_max = out[1]
        assert x_min < x_max and y_min < y_max


class TestRendererIntegration:
    def _fake_tiles(self):
        img = np.zeros((512, 512, 4), dtype=np.uint8)
        img[..., 0] = 120
        img[..., 3] = 255
        return BasemapTiles(
            image=img,
            extent=(-116.6, 40.8, -116.1, 41.3),
            zoom=12,
            provider=dict(DEFAULT_PROVIDERS["esri_world_imagery"]),
            n_tiles=4,
        )

    def test_basemap_painted_below_layers(self, monkeypatch):
        monkeypatch.setattr(
            basemap_mod, "fetch_basemap", lambda *a, **k: self._fake_tiles()
        )
        figures = render_template(
            data=SAMPLE_DF,
            template=site_map_builder(settings={"contours": None}),
            settings={"basemap": {"zoom": 12, "alpha": 0.5}},
        )
        assert len(figures) == 1
        ax = figures[0].axes[0]
        assert len(ax.images) == 1
        image = ax.images[0]
        assert image.get_zorder() == 0
        assert image.get_alpha() == 0.5
        assert np.allclose(
            np.asarray(image.get_extent()),
            [-116.6, -116.1, 40.8, 41.3],
        )
        # vector layers still present above the imagery
        assert len(ax.collections) == 1
        assert len(ax.lines) == 0

    def test_default_recipe_settings_drive_tiles(self, monkeypatch):
        # No explicit basemap settings: the recipe default (Esri, alpha 0.6)
        # must flow all the way onto the AxesImage.
        seen = {}

        def capture(west, south, east, north, **kwargs):
            seen["provider"] = kwargs.get("provider")
            return self._fake_tiles()

        monkeypatch.setattr(basemap_mod, "fetch_basemap", capture)
        figures = render_template(
            data=SAMPLE_DF, template=site_map_builder(settings={"contours": None})
        )
        assert seen["provider"]["name"] == "esri_world_imagery"
        ax = figures[0].axes[0]
        assert len(ax.images) == 1
        assert ax.images[0].get_alpha() == 0.6
        assert ax.images[0].get_zorder() == 0

    def test_fetch_bbox_honors_declared_limits(self, monkeypatch):
        # A declared xlim/ylim (the square site-map viewport) must drive the
        # tile-fetch bbox, not the narrow data auto-window captured before the
        # global settings limits are applied.
        seen = {}

        def capture(west, south, east, north, **kwargs):
            seen["bbox"] = (west, south, east, north)
            return self._fake_tiles()

        monkeypatch.setattr(basemap_mod, "fetch_basemap", capture)
        xlim, ylim = (-116.7, -116.1), (40.8, 41.3)
        render_template(
            data=SAMPLE_DF,
            template=site_map_builder(settings={"contours": None, "streams": None}),
            settings={
                "basemap": {"zoom": 12},
                "xlim": xlim,
                "ylim": ylim,
            },
        )
        assert seen["bbox"] == (xlim[0], ylim[0], xlim[1], ylim[1])

    def test_fetch_bbox_partial_limit_uses_data_for_other_axis(self, monkeypatch):
        seen = {}

        def capture(west, south, east, north, **kwargs):
            seen["bbox"] = (west, south, east, north)
            return self._fake_tiles()

        monkeypatch.setattr(basemap_mod, "fetch_basemap", capture)
        xlim = (-116.7, -116.1)
        render_template(
            data=SAMPLE_DF,
            template=site_map_builder(settings={"contours": None, "streams": None}),
            settings={"basemap": {"zoom": 12}, "xlim": xlim},
        )
        west, south, east, north = seen["bbox"]
        assert (west, east) == xlim
        assert south < north
        # The data-derived latitude window must remain in the fetch request.
        assert south <= SAMPLE_DF["latitude"].min()
        assert north >= SAMPLE_DF["latitude"].max()

    def test_fetch_bbox_swaps_declared_limits_for_flipped_coord(self, monkeypatch):
        seen = {}

        def capture(west, south, east, north, **kwargs):
            seen["bbox"] = (west, south, east, north)
            return self._fake_tiles()

        monkeypatch.setattr(basemap_mod, "fetch_basemap", capture)
        xlim, ylim = (-116.7, -116.1), (40.8, 41.3)
        render_template(
            data=SAMPLE_DF,
            template=site_map_builder(settings={"contours": None, "streams": None}),
            coord=_FlippedGeo(),
            settings={
                "basemap": {"zoom": 12},
                "xlim": xlim,
                "ylim": ylim,
            },
        )
        assert seen["bbox"] == (ylim[0], xlim[0], ylim[1], xlim[1])

    def test_partial_options_keep_default_provider(self, monkeypatch):
        # {"basemap": {"alpha": 0.3}} must still resolve the default Esri
        # provider rather than silently skipping the basemap.
        seen = {}

        def capture(west, south, east, north, **kwargs):
            seen["zoom"] = kwargs.get("zoom")
            seen["provider"] = kwargs.get("provider")
            return self._fake_tiles()

        monkeypatch.setattr(basemap_mod, "fetch_basemap", capture)
        figures = render_template(
            data=SAMPLE_DF,
            template=site_map_builder(settings={"contours": None}),
            settings={"basemap": {"alpha": 0.3}},
        )
        assert seen["provider"]["name"] == "esri_world_imagery"
        assert seen["zoom"] is None  # auto-zoom path
        assert figures[0].axes[0].images[0].get_alpha() == 0.3

    def test_fetch_failure_warns_and_renders_tile_free(self, monkeypatch):
        def boom(*a, **k):
            raise TileFetchError("tile server 502")

        monkeypatch.setattr(basemap_mod, "fetch_basemap", boom)
        with pytest.warns(UserWarning, match="basemap tiles unavailable"):
            figures = render_template(
                data=SAMPLE_DF,
                template=site_map_builder(settings={"contours": None}),
                settings={"basemap": True},
            )
        assert len(figures) == 1
        ax = figures[0].axes[0]
        assert len(ax.images) == 0
        assert len(ax.collections) == 1

    def test_disabled_setting_fetches_nothing(self, monkeypatch):
        def boom(*a, **k):
            raise AssertionError("fetch must not be called")

        monkeypatch.setattr(basemap_mod, "fetch_basemap", boom)
        figures = render_template(
            data=SAMPLE_DF,
            template=site_map_builder(settings={"contours": None}),
            settings={"basemap": None},
        )
        assert len(figures[0].axes[0].images) == 0

    @pytest.mark.skipif(GEO_INSTALLED, reason="requires absent [geo] extra")
    def test_projected_crs_without_pyproj_warns_tile_free(self, monkeypatch):
        def boom(*a, **k):
            raise AssertionError("fetch must not be called")

        monkeypatch.setattr(basemap_mod, "fetch_basemap", boom)
        with pytest.warns(UserWarning, match="pyproj"):
            figures = render_template(
                data=SAMPLE_DF,
                template=site_map_builder(settings={"contours": None}),
                coord=CoordGeo(crs="EPSG:32612"),
                settings={"basemap": True},
            )
        assert len(figures[0].axes[0].images) == 0

    @pytest.mark.skipif(not GEO_INSTALLED, reason="requires [geo] extra")
    def test_projected_crs_with_pyproj_paints_image(self, monkeypatch):
        monkeypatch.setattr(
            basemap_mod, "fetch_basemap", lambda *a, **k: self._fake_tiles()
        )
        figures = render_template(
            data=SAMPLE_DF,
            template=site_map_builder(settings={"contours": None}),
            coord=CoordGeo(crs="EPSG:32612"),
            settings={"basemap": {"zoom": 12, "alpha": 0.8}},
        )
        ax = figures[0].axes[0]
        assert len(ax.images) == 1
        x_min, y_min, x_max, y_max = np.asarray(ax.images[0].get_extent())
        assert x_min < x_max and y_min < y_max
        # UTM 12N northing for a ~41N site is meters > 1e6; data coords, not
        # degrees, are what the mosaic sits in.
        assert y_min > 1e6 and y_max > 1e6
        assert ax.images[0].get_alpha() == 0.8