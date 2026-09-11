"""
Phase 18.2 wp4: DEM contour stat/geom behavior + renderer integration.

Covers ``StatContour`` against a synthetic DEM source (frame columns, NaN
separators, level-set scan parity, flat/all-NaN/raising-source degradation,
missing-coordinate and interval validation, the ``dem_bounds`` override, and
the no-network invariant), ``GeomContour`` registration/defaults, the
renderer integration (a NaN-separated contour multipath drawn above the
zorder-0 basemap and below the boundary ring), and the pyproj-gated
projection paths (skipped when the ``[geo]`` extra is absent).
"""

from __future__ import annotations

import importlib.util

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from geofig_engine import render_template
from geofig_engine.core.coord import CoordGeo
from geofig_engine.core.geom import GeomContour
from geofig_engine.io.dem import DemGrid
from geofig_engine.templates.site_map import StatContour, site_map_builder

GEO_INSTALLED = importlib.util.find_spec("pyproj") is not None

# Synthetic DEM extent (the coordinate frame below spans it exactly).
_WEST, _SOUTH, _EAST, _NORTH = -117.0, 40.0, -116.0, 41.0

# The stat derives its bbox from the frame's lon/lat extent (no buffer —
# buffering happens inside ``fetch_dem``, not at the stat seam).
COORD_FRAME = pd.DataFrame(
    {
        "longitude": [_WEST, _EAST, _WEST, _EAST],
        "latitude": [_SOUTH, _SOUTH, _NORTH, _NORTH],
    }
)


def synthetic_dem(bbox):
    """Deterministic undulating DEM over ``bbox`` (no network, no I/O).

    Normalized ``sin(2πu)·cos(2πv)`` relief gives ~25 m amplitude across the
    extent — a 10 m interval lands several level-sets inside ``[75, 125]``.
    """
    west, south, east, north = (float(v) for v in bbox)
    lon = np.linspace(west, east, 48)
    lat = np.linspace(south, north, 48)
    lon_2d, lat_2d = np.meshgrid(lon, lat)
    u = (lon_2d - west) / (east - west)
    v = (lat_2d - south) / (north - south)
    z = 100.0 + 25.0 * np.sin(2.0 * np.pi * u) * np.cos(2.0 * np.pi * v)
    return DemGrid(lon=lon_2d, lat=lat_2d, z=z)


class TestStatContour:
    def test_produces_xy_frame_only(self):
        out = StatContour(interval=10, dem_source=synthetic_dem).compute(COORD_FRAME)
        assert list(out.columns) == ["x", "y"]
        assert len(out) > 0

    def test_polylines_lie_on_dem_domain(self):
        out = StatContour(interval=10, dem_source=synthetic_dem).compute(COORD_FRAME)
        # level edges may interpolate a float-hair outside the grid extents
        # (NaN separator rows are not sample points and are excluded)
        finite = out.dropna()
        assert finite["x"].between(_WEST - 1e-9, _EAST + 1e-9).all()
        assert finite["y"].between(_SOUTH - 1e-9, _NORTH + 1e-9).all()

    def test_nan_separators_split_segments_and_trailing_trimmed(self):
        out = StatContour(interval=10, dem_source=synthetic_dem).compute(COORD_FRAME)
        x = out["x"].to_numpy()
        y = out["y"].to_numpy()
        nan_pos = np.flatnonzero(np.isnan(x))
        assert nan_pos.size >= 1
        # x/y break together (row-aligned separators)
        assert np.array_equal(np.isnan(x), np.isnan(y))
        # trailing separator trimmed -> last row is a finite point
        assert not np.isnan(x[-1]) and not np.isnan(y[-1])
        # n separators -> n + 1 distinct polyline runs
        assert len(np.flatnonzero(~np.isnan(x))) == len(x) - nan_pos.size
        runs = np.split(x, nan_pos)
        assert len(runs) == nan_pos.size + 1
        assert all(len(run) > 0 for run in runs)

    def test_level_scan_matches_matplotlib(self):
        grid = synthetic_dem((_WEST, _SOUTH, _EAST, _NORTH))
        z = grid.z
        # levels are multiples of the interval within [nanmin, nanmax)
        levels = np.arange(np.nanmin(z), np.nanmax(z), 10)
        assert len(levels) >= 4  # multiple closed loops at interval multiples

        from matplotlib.figure import Figure

        fig = Figure()
        ax = fig.add_subplot(111)
        try:
            cs = ax.contour(grid.lon, grid.lat, z, levels=levels)
            segments = [seg for level_segs in cs.allsegs for seg in level_segs]
        finally:
            del ax
            del fig
        total_points = sum(len(seg) for seg in segments)

        out = StatContour(interval=10, dem_source=synthetic_dem).compute(COORD_FRAME)
        assert out["x"].isna().sum() + 1 == len(segments)
        assert len(out) == total_points + len(segments) - 1
        # at least one level-set is a closed loop (first point == last point)
        closed = [
            seg
            for seg in segments
            if np.hypot(seg[0][0] - seg[-1][0], seg[0][1] - seg[-1][1]) < 1e-9
        ]
        assert closed

    def test_flat_dem_yields_empty_frame(self):
        def flat_dem(bbox):
            west, south, east, north = (float(v) for v in bbox)
            lon = np.linspace(west, east, 8)
            lat = np.linspace(south, north, 8)
            lon_2d, lat_2d = np.meshgrid(lon, lat)
            return DemGrid(lon=lon_2d, lat=lat_2d, z=np.full_like(lon_2d, 123.0))

        out = StatContour(interval=10, dem_source=flat_dem).compute(COORD_FRAME)
        assert out.empty
        assert list(out.columns) == ["x", "y"]

    def test_all_nan_dem_warns_and_empties(self):
        def nan_dem(bbox):
            west, south, east, north = (float(v) for v in bbox)
            lon = np.linspace(west, east, 8)
            lat = np.linspace(south, north, 8)
            lon_2d, lat_2d = np.meshgrid(lon, lat)
            return DemGrid(lon=lon_2d, lat=lat_2d, z=np.full_like(lon_2d, np.nan))

        with pytest.warns(UserWarning, match="contours unavailable"):
            out = StatContour(interval=10, dem_source=nan_dem).compute(COORD_FRAME)
        assert out.empty

    def test_raising_source_degrades_never_propagates(self):
        def boom(bbox):
            raise RuntimeError("terrain tiles unreachable")

        with pytest.warns(UserWarning, match="contours unavailable"):
            out = StatContour(interval=10, dem_source=boom).compute(COORD_FRAME)
        assert out.empty

    def test_missing_coordinates_skip_the_source(self):
        calls: list[tuple] = []

        def spy(bbox):
            calls.append(tuple(bbox))
            return synthetic_dem(bbox)

        out = StatContour(interval=10, dem_source=spy).compute(
            pd.DataFrame({"a": [1], "b": [2]})
        )
        assert out.empty
        assert calls == []  # no coordinate columns -> no DEM request

    def test_interval_validation(self):
        for bad in (0, -5, 0.0, True):
            with pytest.raises(ValueError, match="interval"):
                StatContour(interval=bad, dem_source=synthetic_dem)

    def test_dem_bounds_override_pins_source_bbox(self):
        calls: list[tuple] = []

        def spy(bbox):
            calls.append(tuple(float(v) for v in bbox))
            return synthetic_dem(bbox)

        bounds = (-119.0, 38.0, -118.0, 39.0)
        out = StatContour(
            interval=10, dem_source=spy, dem_bounds=bounds
        ).compute(pd.DataFrame({"a": [1]}))
        assert calls == [bounds]
        finite = out.dropna()
        assert finite["x"].between(bounds[0] - 1e-9, bounds[2] + 1e-9).all()
        assert finite["y"].between(bounds[1] - 1e-9, bounds[3] + 1e-9).all()


class TestGeomContour:
    def test_registration_name_and_channels(self):
        geom = GeomContour()
        assert geom.name == "contour"
        assert geom.required_channels == ("x", "y")
        assert geom.optional_channels == ("color", "alpha")

    def test_old_geomapper_defaults(self):
        geom = GeomContour()
        assert geom.edgecolor == "white"
        assert geom.edgealpha is None
        assert geom.edgewidth == 0.5
        assert geom.edgestyle == "-"


# Ring (truthy boundary flag) + sample points, mirroring test_site_map's view.
_RING = pd.DataFrame(
    {
        "longitude": [-116.6, -116.1, -116.1, -116.6],
        "latitude": [41.3, 41.3, 40.8, 40.8],
        "facility": [None] * 4,
        "name": [None] * 4,
        "boundary": [1, 1, 1, 1],
    }
)
_SAMPLES = pd.DataFrame(
    {
        "longitude": [-116.5, -116.4, -116.3, -116.2],
        "latitude": [41.2, 41.1, 41.0, 40.9],
        "facility": ["A", "A", "B", "B"],
        "name": ["MW-1", "MW-2", "MW-3", "MW-4"],
        "boundary": [0, 0, 0, 0],
    }
)
MERGED_DF = pd.concat([_RING, _SAMPLES], ignore_index=True)


def _contour_recipe(**contour_settings):
    return site_map_builder(
        settings={"contours": {"dem_source": synthetic_dem, **contour_settings}}
    )


class TestContourRender:
    def test_default_recipe_draws_contour_below_boundary(self):
        figures = render_template(
            data=MERGED_DF,
            template=_contour_recipe(),
            settings={"basemap": None},
        )
        ax = figures[0].axes[0]
        # contour multipath + boundary ring (points are a scatter collection)
        assert len(ax.lines) == 2
        contour = next(line for line in ax.lines if len(line.get_xdata()) > 20)
        ring = next(line for line in ax.lines if 3 < len(line.get_xdata()) < 10)
        # contour edits sit at zorder 1 — above the zorder-0 basemap image
        assert contour.get_zorder() == ring.get_zorder() == 1
        # the contour layer precedes the boundary layer -> drawn first (below)
        assert ax.lines.index(contour) < ax.lines.index(ring)
        # identity projection here: points stay on the DEM lon/lat domain
        x = np.asarray(contour.get_xdata(), dtype=float)
        assert np.nanmin(x) >= -116.6 - 1e-9 and np.nanmax(x) <= -116.1 + 1e-9

    def test_contours_opt_out_leaves_only_the_ring(self):
        figures = render_template(
            data=MERGED_DF,
            template=site_map_builder(settings={"contours": None}),
            settings={"basemap": None},
        )
        assert len(figures[0].axes[0].lines) == 1

    @pytest.mark.skipif(GEO_INSTALLED, reason="requires absent [geo] extra")
    def test_identity_fallback_warns_and_renders_lonlat(self):
        with pytest.warns(UserWarning, match="pyproj"):
            figures = render_template(
                data=MERGED_DF,
                template=_contour_recipe(),
                coord=CoordGeo(crs="EPSG:32612"),
                settings={"basemap": None},
            )
        ax = figures[0].axes[0]
        contour = next(line for line in ax.lines if len(line.get_xdata()) > 20)
        x = np.asarray(contour.get_xdata(), dtype=float)
        assert np.nanmin(x) >= -116.6 - 1e-9 and np.nanmax(x) <= -116.1 + 1e-9  # identity

    @pytest.mark.skipif(not GEO_INSTALLED, reason="requires [geo] extra")
    def test_contours_project_like_the_boundary(self):
        figures = render_template(
            data=MERGED_DF,
            template=_contour_recipe(),
            coord=CoordGeo(crs="EPSG:32612"),
            settings={"basemap": None},
        )
        ax = figures[0].axes[0]
        assert len(ax.lines) == 2
        contour = next(line for line in ax.lines if len(line.get_xdata()) > 20)
        ring = next(line for line in ax.lines if 3 < len(line.get_xdata()) < 10)
        contour_x = np.asarray(contour.get_xdata(), dtype=float)
        ring_x = np.asarray(ring.get_xdata(), dtype=float)
        # both layers land in UTM eastings, not lon degrees
        assert np.nanmin(contour_x) > 0
        assert np.nanmin(ring_x) > 0
