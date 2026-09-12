"""
Phase 15 wp9: site_map registry template.

Covers the coordinate/row-selection stat (candidate detection, boundary
flag filtering incl. NaN-separator rows, label detection, informative
errors), registry resolution + recipe shape, mapping-free rendering via
``render_template``, point coloring by group with grouped legend sections,
boundary ring drawing, default-on DEM elevation contours (synthetic-DEM
seam, opt-out), the no-geo identity fallback, and the optional
pyproj projection path (skipped when the ``[geo]`` extra is absent).
"""

from __future__ import annotations

import importlib.util

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest
import pandas as pd

from geofig_engine import TEMPLATES, get_template, render_template
from geofig_engine.core.coord import CoordGeo
from geofig_engine.core.geom import GeomSitePoint
from geofig_engine.engine.api import _apply_mapping_override, recipe_from
from geofig_engine.engine.generator import FigureGenerator
from geofig_engine.io.dem import DemGrid
from geofig_engine.provider import DataFrameProvider
from geofig_engine.renderers.matplotlib.legend import (
    LegendAccumulator,
    render_legend_figure,
)
from geofig_engine.templates.site_map import (
    SITE_MAP_DEFAULTS,
    StatSiteMap,
    settings_contours,
    site_map_builder,
)

GEO_INSTALLED = importlib.util.find_spec("pyproj") is not None

# Points-only geo view (geodata-style coordinate names) with a group column
# ("facility") and a name column.
SAMPLE_DF = pd.DataFrame(
    {
        "longitude": [-116.5, -116.4, -116.3, -116.2],
        "latitude": [41.2, 41.1, 41.0, 40.9],
        "facility": ["A", "A", "B", "B"],
        "name": ["MW-1", "MW-2", "MW-3", "MW-4"],
    }
)

# Closed boundary ring (square) + the sample rows above, tagged by a
# truthy "boundary" flag; ring rows carry no facility/name.
_RING = pd.DataFrame(
    {
        "longitude": [-116.6, -116.1, -116.1, -116.6],
        "latitude": [41.3, 41.3, 40.8, 40.8],
        "facility": [None] * 4,
        "name": [None] * 4,
        "boundary": [1, 1, 1, 1],
    }
)
_SAMPLES_TAGGED = SAMPLE_DF.copy()
_SAMPLES_TAGGED["boundary"] = 0
MERGED_DF = pd.concat([_RING, _SAMPLES_TAGGED], ignore_index=True)


def sample_frame_with(columns: dict[str, list]) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "longitude": [-116.5, -116.4],
            "latitude": [41.2, 41.1],
        }
    )
    for name, values in columns.items():
        frame[name] = values
    return frame


def _fake_dem(bbox):
    """Deterministic undulating DEM over the frame bbox (no network)."""
    west, south, east, north = (float(v) for v in bbox)
    lon = np.linspace(west, east, 24)
    lat = np.linspace(south, north, 24)
    lon_2d, lat_2d = np.meshgrid(lon, lat)
    u = (lon_2d - west) / (east - west)
    v = (lat_2d - south) / (north - south)
    z = 100.0 + 25.0 * np.sin(2.0 * np.pi * u) * np.cos(2.0 * np.pi * v)
    return DemGrid(lon=lon_2d, lat=lat_2d, z=z)


class TestStatSiteMap:
    def test_points_detects_longitude_latitude(self):
        out = StatSiteMap(mode="points").compute(SAMPLE_DF)
        assert set(out.columns) >= {"x", "y", "color", "longitude", "latitude"}
        assert out["x"].tolist() == [-116.5, -116.4, -116.3, -116.2]
        assert out["y"].tolist() == [41.2, 41.1, 41.0, 40.9]
        # group-like column drives the canonical color channel
        assert out["color"].tolist() == ["A", "A", "B", "B"]

    def test_points_fallback_color_is_sites_group(self):
        out = StatSiteMap(mode="points").compute(sample_frame_with({}))
        assert out["color"].tolist() == ["Sites", "Sites"]

    def test_alternative_coordinate_names_detected(self):
        frame = sample_frame_with({})
        frame = frame.rename(columns={"longitude": "x_coord", "latitude": "y_coord"})
        out = StatSiteMap(mode="points").compute(frame)
        assert out["x"].tolist() == [-116.5, -116.4]
        assert out["y"].tolist() == [41.2, 41.1]

    def test_explicit_coordinate_override_wins(self):
        frame = pd.DataFrame({"my_lon": [1.0, 2.0], "my_lat": [3.0, 4.0]})
        out = StatSiteMap(mode="points", x_source="my_lon", y_source="my_lat").compute(
            frame
        )
        assert out["x"].tolist() == [1.0, 2.0]
        assert out["y"].tolist() == [3.0, 4.0]

    def test_missing_coordinates_raise_informative(self):
        with pytest.raises(ValueError, match="coordinate"):
            StatSiteMap(mode="points").compute(pd.DataFrame({"a": [1], "b": [2]}))

    def test_missing_explicit_x_raises(self):
        with pytest.raises(ValueError, match="'nope' not found"):
            StatSiteMap(mode="points", x_source="nope").compute(SAMPLE_DF)

    def test_boundary_filters_flagged_rows(self):
        out = StatSiteMap(mode="boundary").compute(MERGED_DF)
        assert list(out.columns) == ["x", "y"]
        assert len(out) == 4  # ring rows only, sample rows excluded
        assert out["x"].tolist() == [-116.6, -116.1, -116.1, -116.6]
        assert out["y"].tolist() == [41.3, 41.3, 40.8, 40.8]

    def test_boundary_keeps_nan_separator_rows(self):
        separator = pd.DataFrame([{"longitude": np.nan, "latitude": np.nan,
                                   "facility": None, "name": None,
                                   "boundary": 1}])
        frame = pd.concat(
            [MERGED_DF.iloc[:4], separator, MERGED_DF.iloc[4:]], ignore_index=True
        )
        out = StatSiteMap(mode="boundary").compute(frame)
        assert len(out) == 5  # ring rows + flagged NaN separator
        assert out["x"].isna().sum() == 1

    def test_boundary_renders_nothing_without_flag(self):
        out = StatSiteMap(mode="boundary").compute(SAMPLE_DF)
        assert list(out.columns) == ["x", "y"]
        assert len(out) == 0

    def test_missing_explicit_boundary_raises(self):
        with pytest.raises(ValueError, match="boundary column 'bm' not found"):
            StatSiteMap(mode="boundary", boundary_column="bm").compute(SAMPLE_DF)

    def test_labels_detects_name_column(self):
        out = StatSiteMap(mode="labels").compute(SAMPLE_DF)
        assert list(out.columns) == ["x", "y", "label"]
        assert out["label"].tolist() == ["MW-1", "MW-2", "MW-3", "MW-4"]
        assert out["x"].tolist() == [-116.5, -116.4, -116.3, -116.2]

    def test_labels_renders_nothing_without_name_column(self):
        out = StatSiteMap(mode="labels").compute(sample_frame_with({}))
        assert list(out.columns) == ["x", "y", "label"]
        assert len(out) == 0

    def test_labels_honors_explicit_override(self):
        frame = sample_frame_with({"well": ["W1", "W2"]})
        out = StatSiteMap(mode="labels", label_column="well").compute(frame)
        assert out["label"].tolist() == ["W1", "W2"]

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValueError, match="mode"):
            StatSiteMap(mode="nope")


class TestSiteMapTemplate:
    def test_registered_and_resolvable(self):
        assert "site_map" in TEMPLATES
        assert callable(get_template("site_map"))

    def test_builder_returns_recipe_with_defaults(self):
        # Contours pinned off so the canonical pre-18.2 shape stays intact;
        # the default 4-layer shape is covered by
        # test_default_settings_include_contours / test_contours_opt_out_omits_layer.
        recipe = site_map_builder(settings={"contours": None})
        assert recipe.name == "site_map"
        assert len(recipe.layers) == 3
        assert [layer.zorder for layer in recipe.layers] == [1, 2, 3]
        assert isinstance(recipe.coord, CoordGeo)
        assert recipe.default_settings == {**SITE_MAP_DEFAULTS, "contours": None}
        # points layer: pre-bound color channel + string x/y for overrides
        assert recipe.layers[1].mapping["color"] == "color"
        assert recipe.layers[1].mapping["x"] == "x"
        # boundary/labels bind the stat columns as strings too (their row
        # sets are filtered, so the stat short-circuit keeps them aligned)
        assert recipe.layers[0].mapping["x"] == "x"
        assert recipe.layers[2].mapping["label"] == "label"

    def test_coord_override(self):
        recipe = site_map_builder(coord=CoordGeo(aspect=1.0))
        assert recipe.coord.aspect == 1.0

    def test_default_settings_include_contours(self):
        recipe = get_template("site_map")()
        assert len(recipe.layers) == 4  # contour joined below the boundary ring
        assert recipe.layers[0].geom.name == "contour"
        assert recipe.layers[0].stat.params["interval"] is None  # relief-aware
        assert settings_contours(recipe.default_settings) is True
        assert recipe.default_settings["contours"] == {
            "interval": None,
            "color": "white",
            "linewidth": 0.5,
            "alpha": 0.6,
        }

    def test_contours_opt_out_omits_layer(self):
        # settings={"contours": None} restores the 3-layer recipe; the
        # omitted layer keeps the count at 3 (no fetch, no legend noise).
        recipe = site_map_builder(settings={"contours": None})
        assert len(recipe.layers) == 3
        assert settings_contours(recipe.default_settings) is False

        # {"enabled": False} disables within a config dict
        disabled = site_map_builder(settings={"contours": {"enabled": False}})
        assert len(disabled.layers) == 3
        assert settings_contours(disabled.default_settings) is False

        # an explicit dict keeps the layer, merged over the defaults
        overridden = site_map_builder(
            settings={"contours": {"interval": 5, "alpha": 0.5}}
        )
        assert len(overridden.layers) == 4
        assert overridden.layers[0].stat.params["interval"] == 5
        assert overridden.layers[0].geom.edgecolor == "white"  # default kept
        assert overridden.layers[0].geom.edgealpha == 0.5
        assert settings_contours(overridden.default_settings) is True

    def test_direct_mapping_consumed(self):
        recipe = site_map_builder(
            mapping={"x": "my_lon", "y": "my_lat", "boundary": "bm", "label": "nm"},
            settings={"contours": None},
        )
        assert recipe.layers[0].stat.x_source == "my_lon"
        assert recipe.layers[0].stat.boundary_column == "bm"
        assert recipe.layers[2].stat.label_column == "nm"

    def test_settings_merge(self):
        recipe = site_map_builder(settings={"title": "Pump Station"})
        assert recipe.default_settings["title"] == "Pump Station"
        assert recipe.default_settings["figsize"] == SITE_MAP_DEFAULTS["figsize"]

    def test_tile_hook_documented(self):
        doc = site_map_builder.__doc__ or ""
        assert "tile" in doc
        assert "Esri WorldImagery" in doc

    def test_default_settings_enable_imagery_basemap(self):
        recipe = get_template("site_map")()
        basemap = recipe.default_settings["basemap"]
        assert basemap["provider"] == "esri_world_imagery"
        assert 0 < basemap["alpha"] <= 1


class TestSiteMapRender:
    def test_no_mapping_renders_points_and_labels(self):
        figures = render_template(
            data=SAMPLE_DF,
            template=site_map_builder(settings={"contours": None}),
            settings={"basemap": None},
        )
        assert len(figures) == 1
        ax = figures[0].axes[0]
        assert ax.get_title() == SITE_MAP_DEFAULTS["title"]
        assert len(ax.collections) == 1  # site-point scatter
        assert len(ax.lines) == 0  # no boundary flag -> nothing drawn
        texts = sorted(t.get_text() for t in ax.texts)
        assert texts == ["MW-1", "MW-2", "MW-3", "MW-4"]

    def test_alternative_coordinate_names_render(self):
        frame = SAMPLE_DF.rename(
            columns={"longitude": "x_coord", "latitude": "y_coord"}
        )
        figures = render_template(
            data=frame,
            template=site_map_builder(settings={"contours": None}),
            settings={"basemap": None},
        )
        assert len(figures) == 1
        offsets = figures[0].axes[0].collections[0].get_offsets()
        assert np.allclose(sorted(offsets[:, 0]), [-116.5, -116.4, -116.3, -116.2])

    def test_color_mapping_colors_points_by_group(self):
        figures = render_template(
            data=SAMPLE_DF,
            template=site_map_builder(settings={"contours": None}),
            mapping={"color": "facility"},
            settings={"basemap": None},
        )
        colors = figures[0].axes[0].collections[0].get_facecolors()
        assert len(colors) == 4
        assert np.allclose(colors[0], colors[1])  # A
        assert np.allclose(colors[2], colors[3])  # B
        assert not np.allclose(colors[0], colors[2])  # A != B

    def test_grouped_legend_sections(self):
        # Replicate render_template's spec path so the accumulator is fed
        # exactly what the engine accumulates for the color override.
        recipe = recipe_from(site_map_builder(settings={"contours": None}))
        layers = _apply_mapping_override(recipe.layers, {"color": "facility"})
        generator = FigureGenerator(
            provider=DataFrameProvider(SAMPLE_DF),
            layers=layers,
            coord=recipe.coord,
            settings=recipe.default_settings,
        )
        specs = generator.build_specs()
        accumulator = LegendAccumulator()
        for spec in specs:
            accumulator.add_from_spec(spec)

        assert len(accumulator.groups) == 1
        group = accumulator.groups[0]
        assert group.column == "facility"
        assert {entry.label for entry in group.entries} == {"A", "B"}
        assert len({entry.color for entry in group.entries}) == 2

        legend_fig = render_legend_figure(accumulator)
        legend_texts = [
            t.get_text()
            for ax in legend_fig.axes
            if ax.get_legend() is not None
            for t in ax.get_legend().get_texts()
        ]
        assert "facility" in legend_texts
        assert "A" in legend_texts
        assert "B" in legend_texts

    def test_boundary_draws_closed_ring(self):
        figures = render_template(
            data=MERGED_DF,
            template=site_map_builder(settings={"contours": None}),
            settings={"basemap": None},
        )
        assert len(figures) == 1
        ax = figures[0].axes[0]
        assert len(ax.lines) == 1
        xd = np.asarray(ax.lines[0].get_xdata(), dtype=float)
        yd = np.asarray(ax.lines[0].get_ydata(), dtype=float)
        assert len(xd) == 5  # 4 ring vertices + closure point
        assert xd[0] == xd[-1]
        assert yd[0] == yd[-1]
        # points render for every provider row (no filtering on the point layer)
        assert len(ax.collections[0].get_offsets()) == len(MERGED_DF)

    def test_default_path_lays_out_grouped_legend(self):
        # No-mapping merged render: the points color channel (canonical
        # "color" = facility, NaN ring rows -> "Sites") accumulates into one
        # grouped legend section with entries for the distinct sites.
        recipe = recipe_from(site_map_builder(settings={"contours": None}))
        generator = FigureGenerator(
            provider=DataFrameProvider(MERGED_DF),
            layers=recipe.layers,
            coord=recipe.coord,
            settings=recipe.default_settings,
        )
        accumulator = LegendAccumulator()
        for spec in generator.build_specs():
            accumulator.add_from_spec(spec)

        assert len(accumulator.groups) == 1
        assert accumulator.groups[0].column == "color"
        assert {entry.label for entry in accumulator.groups[0].entries} == {
            "A", "B", "Sites",
        }

    def test_color_override_with_nan_group_rows(self):
        # Boundary rows in the shared frame have NaN facility; a color
        # override on the points layer must still render (ungrouped rows get
        # the neutral color instead of an "Invalid RGBA argument: nan").
        figures = render_template(
            data=MERGED_DF,
            template=site_map_builder(settings={"contours": None}),
            mapping={"color": "facility"},
            settings={"basemap": None},
        )
        assert len(figures) == 1
        offsets = figures[0].axes[0].collections[0].get_offsets()
        assert len(offsets) == len(MERGED_DF)

    def test_labels_optional(self):
        frame = SAMPLE_DF.drop(columns=["name"])
        figures = render_template(
            data=frame,
            template=site_map_builder(settings={"contours": None}),
            settings={"basemap": None},
        )
        assert len(figures[0].axes[0].texts) == 0

    def test_contours_render_default_on_and_opt_out(self):
        # The wp3 seam: the default recipe draws contour line artists (the
        # synthetic DEM is injected via the contours setting — no network);
        # settings={"contours": None} leaves just the boundary ring.
        figures = render_template(
            data=MERGED_DF,
            template=site_map_builder(settings={"contours": {"dem_source": _fake_dem}}),
            settings={"basemap": None},
        )
        ax = figures[0].axes[0]
        # contour multipath + boundary ring (points are a scatter collection)
        assert len(ax.lines) == 2
        assert any(len(line.get_xdata()) > 20 for line in ax.lines)

        figures_off = render_template(
            data=MERGED_DF,
            template=site_map_builder(settings={"contours": None}),
            settings={"basemap": None},
        )
        assert len(figures_off[0].axes[0].lines) == 1  # ring only

    def test_default_identity_projection(self):
        recipe = recipe_from(get_template("site_map")())
        vm = {"x": pd.Series([-116.5, -116.4]), "y": pd.Series([41.2, 41.1])}
        out = recipe.coord.transform_visual_mapping(vm, GeomSitePoint())
        assert out["x"].tolist() == [-116.5, -116.4]
        assert out["y"].tolist() == [41.2, 41.1]

    @pytest.mark.skipif(GEO_INSTALLED, reason="requires absent [geo] extra")
    def test_no_geo_fallback_warns_and_renders_identity(self):
        with pytest.warns(UserWarning, match="pyproj"):
            figures = render_template(
                data=SAMPLE_DF,
                template=site_map_builder(settings={"contours": None}),
                coord=CoordGeo(crs="EPSG:32612"),
                settings={"basemap": None},
            )
        assert len(figures) == 1
        assert len(figures[0].axes[0].collections) == 1

    @pytest.mark.skipif(not GEO_INSTALLED, reason="requires [geo] extra")
    def test_honors_projection_with_pyproj(self):
        recipe = site_map_builder(coord=CoordGeo(crs="EPSG:32612"))
        x = pd.Series(SAMPLE_DF["longitude"].to_numpy())
        y = pd.Series(SAMPLE_DF["latitude"].to_numpy())
        out = recipe.coord.transform_visual_mapping({"x": x, "y": y}, GeomSitePoint())
        assert not np.allclose(out["x"].to_numpy(), SAMPLE_DF["longitude"].to_numpy())