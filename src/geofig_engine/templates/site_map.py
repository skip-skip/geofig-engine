"""
Site map registry template (15_wp9).

Renders a ``CoordGeo`` site map from a duck-typed provider view: an optional
site boundary/context outline (``GeomBoundary``), sample points colored by a
grouping column (``GeomSitePoint``), and site/well name labels (``GeomLabel``).
No mapping is required — coordinate columns are detected from the frame by
candidate names, in order (default: ``longitude``/``latitude`` — the geodata
coordinate convention), a group-like column drives point coloring, and a
label-like column drives site-name text. The grouped legend comes from the
existing ``LegendAccumulator`` machinery: the point layer's ``color`` channel
is pre-bound to a canonical ``color`` column the stat produces, so a
``mapping={"color": <column>}`` override through ``render_template`` remaps it
onto any provider column and yields a legend section per unique value.

**Basemap tiles** (wp14): a Web-Mercator XYZ mosaic (default Esri WorldImagery,
matching ``geochemmapper.py``'s ``add_basemap`` default) is fetched by the
renderer for the axis extent and painted beneath this layer stack — the hook
this template reserved in wp9. No mapping or extra dependency is required
(``requests`` + ``Pillow`` only; ``xyzservices`` optional for provider
lookup). Disable tiles with ``settings={"basemap": None}``; override style
with ``settings={"basemap": {"provider": ..., "zoom": ..., "alpha": ...}}``.
An offline/HTTP failure (or a non-WGS84 ``coord.crs`` without the ``[geo]``
extra) warns and renders the boundary/points/labels tile-free.

**Elevation contours** (18.2): a default-on ``GeomContour`` layer derives
isolines from a lazy terrarium DEM fetch for the provider frame's lon/lat
extent (bbox from the detected coordinates, 10% buffer, bbox-keyed tile
cache — ``geofig_engine.io.dem``) at multiples of 10 m with the old-geomapper
line style (white, 0.5 pt, alpha 0.6). The whole line set shares that single
constant style — no legend interplay. An offline/HTTP failure or an all-NaN
DEM degrades with a ``UserWarning`` and no contour lines (basemap-degrade
parity). Disable with ``settings={"contours": None}`` or
``{"enabled": False}`` (the layer is then omitted from the recipe); override
with a dict such as ``settings={"contours": {"interval": 5, "alpha": 0.5}}``.
A ``dem_bounds`` entry (``west, south, east, north``) pins the DEM fetch extent
instead of deriving it from the frame. Contour lon/lat polylines project
through ``CoordGeo`` like every other geo layer.

**Streams** (18.3): a default-on ``GeomStreams`` layer queries the public USGS
National Map ``NHDPlus_HR`` REST service (layer 3, ``ftype = 460``) for the
provider frame's WGS84 lon/lat bbox — no buffer, old-geomapper parity — and
draws the returned LineString/MultiLineString polylines in one constant style
(blue, 0.7 pt, alpha 0.7) with no legend entry. Results are fetched lazily per
render via :func:`geofig_engine.io.streams.fetch_streams` (no API key, no new
dependency), paginated up to ``max_pages`` batches; a transport/HTTP/parse
failure or truncation warns and yields no lines, while an empty successful
query (US-only NHD coverage) is silent. Disable with
``settings={"streams": None}`` or ``{"enabled": False}``; override the style,
``service_url``, ``layer_id``, ``where``, ``max_pages``, or inject a
network-free ``streams_source(bbox)`` callable through the streams dict. The
callable is a test/downstream seam and is never recorded in JSON settings.

Optional boundary: when the provider frame carries a boundary-flag column
(name auto-detected from ``boundary``/``is_boundary``/``feature``/``ring``, or
set explicitly via ``mapping={"boundary": <column>}`` on a direct builder
call), the boundary layer plots exactly the flagged rows (NaN separator rows
between ring parts stay flagged so multipart outlines keep their gaps). With
no such column the boundary layer renders nothing.
"""

from __future__ import annotations

import math
import warnings
from typing import Any, Callable

import numpy as np
import pandas as pd

from geofig_engine.core.coord import Coord, CoordGeo
from geofig_engine.core.geom import (
    GeomBoundary,
    GeomContour,
    GeomLabel,
    GeomSitePoint,
    GeomStreams,
)
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import Stat
from geofig_engine.io.streams import (
    DEFAULT_MAX_PAGES,
    DEFAULT_STREAM_SERVICE_URL,
    STREAM_WHERE,
)

SITE_MAP_DEFAULTS: dict[str, Any] = {
    "figsize": (10, 8),
    "title": "Site Map",
    "xlabel": "Longitude",
    "ylabel": "Latitude",
    "basemap": {"provider": "esri_world_imagery", "alpha": 0.6},
    # ``contours["interval"]``: ``None`` (the default) is relief-aware —
    # StatContour derives the spacing from the DEM's elevation range
    # (10 m minimum, ~20 lines across the relief); an explicit number
    # (e.g. 10 for old-geomapper parity) is honored verbatim.
    "contours": {"interval": None, "color": "white", "linewidth": 0.5, "alpha": 0.6},
    "streams": {
        "enabled": True,
        "color": "blue",
        "linewidth": 0.7,
        "alpha": 0.7,
        "service_url": DEFAULT_STREAM_SERVICE_URL,
        "layer_id": 3,
        "where": STREAM_WHERE,
        "max_pages": DEFAULT_MAX_PAGES,
        "streams_source": None,
    },
}

#: Allowed keys for the ``streams`` settings dict (unknown keys are rejected).
STREAM_SETTING_KEYS = frozenset(SITE_MAP_DEFAULTS["streams"])


def settings_streams(recipe_settings: dict[str, Any]) -> dict[str, Any] | None:
    """Return the merged stream config, or ``None`` when streams are disabled.

    Mirrors :func:`settings_contours` but returns the config instead of a
    boolean so the builder can pass the seam/query knobs to ``StatStreams``.
    ``None``/``False``/``{"enabled": False}`` disable the layer; ``True`` or a
    dict enable it. Dict keys merge over ``SITE_MAP_DEFAULTS["streams"]`` and
    unknown keys are rejected (unlike the permissive basemap/contour settings).
    """
    value = recipe_settings.get("streams")
    if value is None or value is False:
        return None
    if value is True:
        value = {}
    if not isinstance(value, dict):
        raise ValueError(
            "streams settings must be None, a bool, or a dict, "
            f"got {value!r}"
        )
    unknown = set(value) - STREAM_SETTING_KEYS
    if unknown:
        raise ValueError(
            "unknown streams setting(s): " + ", ".join(sorted(unknown))
        )
    if not bool(value.get("enabled", True)):
        return None
    config = dict(SITE_MAP_DEFAULTS["streams"])
    config.update(value)
    return config


def settings_contours(recipe_settings: dict[str, Any]) -> bool:
    """Whether the recipe's ``contours`` setting enables the contour layer.

    Shared by the builder and tests. Operates on the **merged** recipe
    settings (``SITE_MAP_DEFAULTS`` overlaid with the user settings), where
    the ``contours`` key is always present: ``None``/``False``/
    ``{"enabled": False}`` disable; ``True`` or a config dict enable (dict
    keys merge over the defaults — unknown keys are tolerated, matching the
    basemap setting).
    """
    value = recipe_settings.get("contours")
    if value is None or value is False:
        return False
    if value is True:
        return True
    if isinstance(value, dict):
        return bool(value.get("enabled", True))
    return False

#: Coordinate-column candidate lists, in preference order (first present wins).
X_CANDIDATES: tuple[str, ...] = ("longitude", "x_coord", "x", "lon", "easting")
Y_CANDIDATES: tuple[str, ...] = ("latitude", "y_coord", "y", "lat", "northing")

#: Group-like column candidates for point coloring (first present wins).
GROUP_CANDIDATES: tuple[str, ...] = (
    "color", "group", "facility", "sample_group", "cluster", "type",
    "fraction", "analyte",
)

#: Label-like column candidates for site/well names (first present wins).
LABEL_CANDIDATES: tuple[str, ...] = (
    "label", "name", "well", "well_id", "location", "site",
)

#: Boundary-flag column candidates (first present wins).
BOUNDARY_CANDIDATES: tuple[str, ...] = (
    "boundary", "is_boundary", "feature", "ring",
)


def _first_present(candidates: tuple[str, ...], frame: pd.DataFrame) -> str | None:
    """First candidate that is a column of ``frame``, else ``None``."""
    for name in candidates:
        if name in frame.columns:
            return name
    return None


def _empty_with_columns(columns: list[str]) -> pd.DataFrame:
    """An empty frame that still exposes ``columns`` (0 rows)."""
    return pd.DataFrame({col: pd.Series(dtype="float64" if col in ("x", "y") else object)
                         for col in columns})


def _truthy_mask(frame: pd.DataFrame, column: str) -> pd.Series:
    """Rows where ``column`` is a truthy boundary flag (NaN/0/False/'' are not)."""
    return frame[column].notna() & frame[column].astype(bool)


class StatSiteMap(Stat):
    """Spec-build transform that derives the site-map layer channels.

    One stat instance is shared by the recipe's three geo layers via its
    ``mode``:

    - ``"boundary"`` — the (optional) site outline path. Selects the rows
      flagged by the boundary column (holding NaN separator rows for
      multipart rings) and exposes canonical ``x``/``y`` coordinates.
      Returns an empty ``x``/``y`` frame when no flag column exists, so the
      layer renders nothing.
    - ``"points"`` — the sample points. Never row-filters (the visual series
      must stay index-aligned with ``FigureSpec.data`` for legend
      accumulation); exposes canonical ``x``/``y`` plus a canonical ``color``
      column = the first group-like column (NaN values falling back to the
      geom group name ``Sites``), or the geom group name ``Sites`` when the
      frame has none.
    - ``"labels"`` — site/well name text. Exposes canonical ``x``/``y``/
      ``label`` from the first label-like column, keeping only name-bearing
      rows; returns an empty ``x``/``y``/``label`` frame when no label-like
      column exists.

    ``x_source``/``y_source`` override the coordinate detection (they are the
    ``x``/``y`` keys of a direct-builder mapping); missing columns raise an
    informative ``ValueError``.
    """

    def __init__(
        self,
        mode: str = "points",
        x_source: str | None = None,
        y_source: str | None = None,
        boundary_column: str | None = None,
        label_column: str | None = None,
    ) -> None:
        if mode not in ("boundary", "points", "labels"):
            raise ValueError(
                f"StatSiteMap mode must be 'boundary', 'points', or 'labels'; "
                f"got {mode!r}"
            )
        for name, value in (("x_source", x_source), ("y_source", y_source),
                            ("boundary_column", boundary_column),
                            ("label_column", label_column)):
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{name} must be a column name or None, got {value!r}")
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "x_source", x_source)
        object.__setattr__(self, "y_source", y_source)
        object.__setattr__(self, "boundary_column", boundary_column)
        object.__setattr__(self, "label_column", label_column)
        super().__init__(
            name="site_map",
            params={
                "mode": mode,
                "x_source": x_source,
                "y_source": y_source,
                "boundary_column": boundary_column,
                "label_column": label_column,
            },
        )

    # ------------------------------------------------------------------
    # Coordinate detection
    # ------------------------------------------------------------------

    def _coordinate_columns(self, data: pd.DataFrame) -> tuple[str, str]:
        x_col = self.x_source if self.x_source is not None else _first_present(
            X_CANDIDATES, data
        )
        y_col = self.y_source if self.y_source is not None else _first_present(
            Y_CANDIDATES, data
        )
        if x_col is None or y_col is None:
            raise ValueError(
                "site_map: no coordinate columns found in the provider. "
                f"Looked for x in {X_CANDIDATES} and y in {Y_CANDIDATES}; "
                "pass a mapping override (x=/y=) with the coordinate column names."
            )
        for col, axis in ((x_col, "x"), (y_col, "y")):
            if col not in data.columns:
                raise ValueError(
                    f"site_map: {axis} column '{col}' not found in the provider "
                    f"(available columns: {sorted(data.columns)})"
                )
        return x_col, y_col

    # ------------------------------------------------------------------
    # Mode-specific row selection
    # ------------------------------------------------------------------

    def _boundary_flag(self, data: pd.DataFrame) -> str | None:
        if self.boundary_column is not None:
            if self.boundary_column not in data.columns:
                raise ValueError(
                    f"site_map: boundary column '{self.boundary_column}' not "
                    f"found in the provider (available columns: "
                    f"{sorted(data.columns)})"
                )
            return self.boundary_column
        return _first_present(BOUNDARY_CANDIDATES, data)

    def _group_column(self, data: pd.DataFrame) -> str | None:
        return _first_present(GROUP_CANDIDATES, data)

    def _label_column(self, data: pd.DataFrame) -> str | None:
        if self.label_column is not None:
            if self.label_column not in data.columns:
                raise ValueError(
                    f"site_map: label column '{self.label_column}' not found in "
                    f"the provider (available columns: {sorted(data.columns)})"
                )
            return self.label_column
        return _first_present(LABEL_CANDIDATES, data)

    # ------------------------------------------------------------------
    # Stat contract
    # ------------------------------------------------------------------

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        x_col, y_col = self._coordinate_columns(data)

        if self.mode == "boundary":
            flag = self._boundary_flag(data)
            if flag is None:
                return _empty_with_columns(["x", "y"])
            out = data.loc[_truthy_mask(data, flag)].copy()
            if len(out) == 0:
                return _empty_with_columns(["x", "y"])
            out["x"] = out[x_col]
            out["y"] = out[y_col]
            return out[["x", "y"]]

        if self.mode == "points":
            # Deliberately no row filtering: the visual series must stay
            # index-aligned with FigureSpec.data for legend accumulation.
            out = data.copy()
            out["x"] = out[x_col]
            out["y"] = out[y_col]
            group = self._group_column(out)
            if group is not None:
                # NaN group values (e.g. boundary-flag rows sharing the points
                # frame) fall back to the geom's default group so the scatter
                # color sequence stays fully resolvable.
                out["color"] = out[group].fillna("Sites")
            else:
                out["color"] = "Sites"  # geom group name; single-entry legend
            return out

        # labels mode
        label_col = self._label_column(data)
        if label_col is None:
            return _empty_with_columns(["x", "y", "label"])
        out = data.loc[data[label_col].notna()].copy()
        out["x"] = out[x_col]
        out["y"] = out[y_col]
        out["label"] = out[label_col]
        return out[["x", "y", "label"]]


def _auto_contour_interval(z: np.ndarray, minimum: float = 10.0, target_levels: float = 20.0) -> float:
    """Relief-derived contour spacing in meters.

    At least *minimum* meters (old-geomapper 10 m parity for
    modest-relief sites), coarsened for large-relief extents so the figure
    does not wall up with dozens of tightly-packed 10 m lines — roughly
    *target_levels* levels across the DEM's elevation range, rounded to a
    multiple of 5 m for readable level values. Deterministic per-grid.
    """
    relief = float(np.nanmax(z) - np.nanmin(z))
    return max(minimum, 5.0 * round(relief / target_levels / 5.0))


class StatContour(Stat):
    """Spec-build transform that derives DEM elevation contour lines.

    Acquires a DEM for the provider frame's lon/lat extent (via
    ``geofig_engine.io.dem.fetch_dem``, which applies the old-geomapper 10%
    lon/lat buffer), extracts isolines at multiples of the contour interval
    meters, and emits a NaN-separated ``x``/``y`` frame — one continuous open
    polyline per contour segment, matching the ``StatParticleOverlay
    (mode="contours")`` frame shape that ``render_boundary`` draws as open
    multipart paths (handlers.py:1020).

    The interval is relief-aware when left at the ``None`` default
    (``SITE_MAP_DEFAULTS["contours"]["interval"]``): at least the
    old-geomapper 10 m spacing, coarsened so a large-relief extent does not
    wall up with dozens of tightly-packed 10 m lines (~20 levels across the
    DEM's elevation range). An explicit ``interval`` is honored verbatim.

    M1 is constant-style: the whole line set shares the geom's single
    ``edgecolor``/``edgewidth``/``edgealpha``/``edgestyle`` (old-geomapper
    ``add_contours`` defaults); a per-level ``level`` channel is not added.

    The DEM acquisition never raises into the layer pipeline: a fetch
    failure or an all-NaN DEM warns (``UserWarning``) and yields an empty
    ``x``/``y`` frame, so the contour layer simply renders nothing (mirrors
    the basemap degrade).
    """

    def __init__(
        self,
        interval: float | None = None,
        dem_source: Callable[[tuple[float, float, float, float]], Any] | None = None,
        dem_bounds: tuple[float, float, float, float] | None = None,
    ) -> None:
        if interval is not None:
            if isinstance(interval, bool) or not isinstance(interval, (int, float)):
                raise ValueError(
                    f"interval must be a positive real number or None, got {interval!r}"
                )
            if interval <= 0:
                raise ValueError(
                    f"interval must be a positive real number or None, got {interval!r}"
                )
        if dem_source is not None and not callable(dem_source):
            raise TypeError(f"dem_source must be callable or None, got {dem_source!r}")
        if dem_bounds is not None:
            if not isinstance(dem_bounds, (tuple, list)) or len(dem_bounds) != 4:
                raise ValueError(
                    "dem_bounds must be a (west, south, east, north) tuple of "
                    f"four real numbers, got {dem_bounds!r}"
                )
            for value in dem_bounds:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(
                        "dem_bounds must be a (west, south, east, north) tuple "
                        f"of four real numbers, got {dem_bounds!r}"
                    )
        object.__setattr__(self, "dem_source", dem_source)
        object.__setattr__(self, "dem_bounds", dem_bounds)
        super().__init__(
            name="contour",
            params={
                "interval": None if interval is None else float(interval),
                # JSON-safe (the callable dem_source seam is not recorded).
                "dem_bounds": None if dem_bounds is None else tuple(dem_bounds),
            },
        )

    # ------------------------------------------------------------------
    # Coordinate detection (non-raising — contour renders nothing instead)
    # ------------------------------------------------------------------

    def _coordinate_columns_or_none(
        self, data: pd.DataFrame
    ) -> tuple[str | None, str | None]:
        x_col = _first_present(X_CANDIDATES, data)
        y_col = _first_present(Y_CANDIDATES, data)
        if (
            x_col is None
            or y_col is None
            or x_col not in data.columns
            or y_col not in data.columns
        ):
            return None, None
        return x_col, y_col

    @staticmethod
    def _empty_frame() -> pd.DataFrame:
        return _empty_with_columns(["x", "y"])

    def _unavailable(self, reason: str) -> pd.DataFrame:
        warnings.warn(
            f"site_map contours unavailable: {reason}",
            UserWarning,
            stacklevel=2,
        )
        return self._empty_frame()

    # ------------------------------------------------------------------
    # Stat contract
    # ------------------------------------------------------------------

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        if len(data) == 0:
            return self._empty_frame()

        if self.dem_bounds is not None:
            bbox = tuple(float(v) for v in self.dem_bounds)
        else:
            x_col, y_col = self._coordinate_columns_or_none(data)
            if x_col is None or y_col is None:
                return self._empty_frame()
            lon = data[x_col]
            lat = data[y_col]
            if lon.notna().sum() == 0 or lat.notna().sum() == 0:
                return self._empty_frame()
            bbox = (
                float(lon.min()),
                float(lat.min()),
                float(lon.max()),
                float(lat.max()),
            )
        if not all(math.isfinite(v) for v in bbox):
            return self._empty_frame()

        explicit_interval = self.params["interval"]
        # ``None`` resolves against the DEM's relief AFTER the fetch (the
        # auto-zoom resolution only needs a magnitude, so the fetch reuses
        # the old-geomapper 10 m default until the grid is in hand).
        fetch_interval = 10.0 if explicit_interval is None else explicit_interval

        try:
            if self.dem_source is not None:
                grid = self.dem_source(bbox)
            else:
                from geofig_engine.io.dem import fetch_dem

                grid = fetch_dem(*bbox, interval=fetch_interval)
            if grid is None:
                raise ValueError("DEM source returned nothing")
            z = np.asarray(grid.z, dtype=float)
            lon_2d = np.asarray(grid.lon, dtype=float)
            lat_2d = np.asarray(grid.lat, dtype=float)
        except Exception as exc:  # noqa: BLE001 — transport/HTTP/decoding degrade
            return self._unavailable(str(exc))

        if z.ndim != 2 or lon_2d.ndim != 2 or lat_2d.ndim != 2:
            return self._unavailable(f"DEM grid must be 2-D, got z {z.shape}")
        if np.isnan(z).all():
            return self._unavailable("DEM is all NaNs")
        if z.shape != lon_2d.shape or z.shape != lat_2d.shape:
            return self._unavailable(
                f"DEM lon/lat grids {lon_2d.shape} do not match z {z.shape}"
            )

        level_interval = (
            explicit_interval if explicit_interval is not None else _auto_contour_interval(z)
        )
        levels = np.arange(np.nanmin(z), np.nanmax(z), level_interval)
        if levels.size == 0:
            return self._empty_frame()
        return self._contour_frame(lon_2d, lat_2d, z, levels)

    def _contour_frame(
        self,
        lon: np.ndarray,
        lat: np.ndarray,
        z: np.ndarray,
        levels: np.ndarray,
    ) -> pd.DataFrame:
        """Flatten ``ax.contour`` segments into a NaN-separated x/y frame.

        Each level's polylines become one continuous row series: every
        polyline is followed by a NaN separator so ``render_boundary`` keeps
        the paths open (trailing separator trimmed, matching
        ``StatParticleOverlay._contours_frame``).
        """
        from matplotlib.figure import Figure

        fig = Figure()
        try:
            ax = fig.add_subplot(111)
            cs = ax.contour(lon, lat, z, levels=levels)
            allsegs = cs.allsegs
        finally:
            del ax
            del fig

        xs: list[float] = []
        ys: list[float] = []
        for level_segs in allsegs:
            for seg in level_segs:
                xs.extend(seg[:, 0].tolist())
                ys.extend(seg[:, 1].tolist())
                xs.append(float("nan"))
                ys.append(float("nan"))
        if not xs:
            return self._empty_frame()
        xs = xs[:-1]
        ys = ys[:-1]
        return pd.DataFrame({"x": xs, "y": ys})


class StatStreams(Stat):
    """Spec-build transform that derives surface-water stream polylines.

    Acquires NHDPlus_HR stream geometry for the provider frame's lon/lat bbox
    (min/max of the detected coordinate columns — no DEM-style buffer) and
    emits the same NaN-separated ``x``/``y`` multipart frame as
    :class:`StatContour`, which ``render_boundary`` draws as open paths.
    ``streams_source(bbox)`` replaces the network fetch (the ``dem_source``
    seam pattern); the callable is held as an attribute and never serialized.
    JSON-safe query knobs live in ``params``.

    The default :func:`geofig_engine.io.streams.fetch_streams` path never
    raises: transport/HTTP/parse failures and pagination truncation warn and
    yield an empty frame; an empty but successful query (non-US coverage) is
    silent. A raising/invalid seam degrades the same way.
    """

    def __init__(
        self,
        streams_source: Callable[[tuple[float, float, float, float]], Any] | None = None,
        service_url: str = DEFAULT_STREAM_SERVICE_URL,
        layer_id: int = 3,
        where: str = STREAM_WHERE,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> None:
        if streams_source is not None and not callable(streams_source):
            raise TypeError(
                f"streams_source must be callable or None, got {streams_source!r}"
            )
        if not isinstance(service_url, str) or not service_url.strip():
            raise ValueError(f"service_url must be a non-empty string, got {service_url!r}")
        if isinstance(layer_id, bool) or not isinstance(layer_id, int):
            raise ValueError(f"layer_id must be an integer, got {layer_id!r}")
        if not isinstance(where, str) or not where.strip():
            raise ValueError(f"where must be a non-empty string, got {where!r}")
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages < 1:
            raise ValueError(f"max_pages must be an integer >= 1, got {max_pages!r}")
        object.__setattr__(self, "streams_source", streams_source)
        super().__init__(
            name="streams",
            params={
                "service_url": service_url,
                "layer_id": layer_id,
                "where": where,
                "max_pages": max_pages,
            },
        )

    @staticmethod
    def _empty_frame() -> pd.DataFrame:
        return _empty_with_columns(["x", "y"])

    def _unavailable(self, reason: str) -> pd.DataFrame:
        warnings.warn(
            f"site_map streams unavailable: {reason}",
            UserWarning,
            stacklevel=2,
        )
        return self._empty_frame()

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        if len(data) == 0:
            return self._empty_frame()

        x_col = _first_present(X_CANDIDATES, data)
        y_col = _first_present(Y_CANDIDATES, data)
        if x_col is None or y_col is None:
            return self._empty_frame()
        lon, lat = data[x_col], data[y_col]
        if lon.notna().sum() == 0 or lat.notna().sum() == 0:
            return self._empty_frame()
        bbox = (
            float(lon.min()),
            float(lat.min()),
            float(lon.max()),
            float(lat.max()),
        )
        if not all(math.isfinite(v) for v in bbox):
            return self._empty_frame()

        try:
            if self.streams_source is not None:
                frame = self.streams_source(bbox)
            else:
                from geofig_engine.io.streams import fetch_streams

                frame = fetch_streams(
                    bbox,
                    service_url=self.params["service_url"],
                    layer_id=self.params["layer_id"],
                    where=self.params["where"],
                    max_pages=self.params["max_pages"],
                )
        except Exception as exc:  # noqa: BLE001 — seam/network degrade
            return self._unavailable(str(exc))

        if frame is None:
            return self._unavailable("streams source returned nothing")
        if not isinstance(frame, pd.DataFrame) or not {"x", "y"}.issubset(frame.columns):
            return self._unavailable("streams source must return an x/y DataFrame")
        out = frame.loc[:, ["x", "y"]].copy()
        for column in ("x", "y"):
            out[column] = pd.to_numeric(out[column], errors="coerce")
        return out.reset_index(drop=True)


def site_map_builder(
    mapping: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
    coord: Coord | None = None,
    **_,
) -> "TemplateRecipe":
    """Pipeline registry builder for the ``site_map`` key (15_wp9).

    Returns the canonical recipe shape: a ``GeomContour`` elevation layer, a
    ``GeomBoundary`` boundary ring layer, a ``GeomSitePoint`` layer (with a
    pre-bound ``color`` channel the ``mapping={"color": ...}`` override
    remaps at ``render_template`` time), and a ``GeomLabel`` layer, all under
    a ``CoordGeo`` coord (default WGS84 — identity projection without the
    ``[geo]`` extra). Works with **no mapping**: coordinates, group coloring,
    and label columns auto-resolve from the provider frame by candidate
    names. A direct-builder mapping may pin ``x``/``y`` (coordinate columns),
    ``boundary`` (flag column), ``label`` (name column); ``color`` is a
    per-call override on the points layer.

    ``coord`` overrides the recipe's geographic coord (e.g. a non-WGS84
    ``crs`` activates the ``[geo]`` projection path). Basemap tiles are
    enabled by default (``SITE_MAP_DEFAULTS["basemap"]`` — Esri WorldImagery
    at alpha 0.6, fetched by the renderer below the layer stack; wp14).
    Disable with ``settings={"basemap": None}``, or override provider/zoom/
    alpha with a ``settings={"basemap": {...}}`` dict; an offline or
    ``[geo]``-less projected render degrades to tiles-off with a warning.

    Elevation contours are **on by default**
    (``SITE_MAP_DEFAULTS["contours"]`` — relief-aware interval (``None``:
    10 m minimum, ~20 lines across the DEM's elevation range; set an explicit
    ``interval`` for old-geomapper 10 m parity), white 0.5 pt at alpha 0.6,
    constant style): a ``GeomContour`` layer above the zorder-0 basemap image
    and below the boundary ring, fed by a lazy terrarium DEM fetch for the
    frame's lon/lat extent (10% buffer).
    ``settings={"contours": None}`` or ``{"enabled": False}`` omits the
    layer; a dict merges over the defaults (``interval``, ``color``,
    ``linewidth``, ``alpha``); ``dem_source`` may inject a synthetic DEM
    (test seam — no network). Offline/HTTP/DEM failures warn and render no
    contours.

    Surface-water streams are **on by default** too
    (``SITE_MAP_DEFAULTS["streams"]`` — blue 0.7 pt at alpha 0.7, no legend):
    a ``GeomStreams`` layer in the zorder-1 band above the contour/boundary
    linework and below the sites/labels, fed by a lazy USGS NHDPlus_HR query
    for the frame's unbuffered lon/lat bbox. Query knobs (``service_url``,
    ``layer_id``, ``where``, ``max_pages``) and the ``streams_source`` seam are
    set via ``settings={"streams": {...}}``; ``{"streams": None}`` or
    ``{"enabled": False}`` omits the layer and skips the HTTP query entirely.
    Failures/truncation warn and render no lines; an empty successful query is
    silent. The callable seam is never recorded in the JSON-safe settings.

    The ``TemplateRecipe`` import is deferred to call time so this template
    module never depends on ``engine.api`` at import time.
    """
    from geofig_engine.engine.api import TemplateRecipe

    mapping = dict(mapping or {})
    recipe_settings = {**SITE_MAP_DEFAULTS, **(settings or {})}
    streams_cfg = settings_streams(recipe_settings)

    # The injected callable is a real builder seam but must not leak into the
    # recipe's JSON-safe settings.
    default_settings = dict(recipe_settings)
    if streams_cfg is not None:
        safe_streams_cfg = dict(streams_cfg)
        if callable(safe_streams_cfg.get("streams_source")):
            safe_streams_cfg["streams_source"] = None
        default_settings["streams"] = safe_streams_cfg

    # All channels bind the stat-produced canonical columns ("x"/"y"/"color"/
    # "label") as plain strings, so render_template's per-layer override can
    # remap them onto provider columns; the boundary/labels stats row-filter,
    # so overriding their x/y with full-frame columns is an M1 edge (their
    # row sets must stay stat-aligned to keep the filtered series paired).
    layers = [
        Layer(
            geom=GeomBoundary(),
            stat=StatSiteMap(
                mode="boundary",
                x_source=mapping.get("x"),
                y_source=mapping.get("y"),
                boundary_column=mapping.get("boundary"),
            ),
            mapping={"x": "x", "y": "y"},
            zorder=1,
        ),
        Layer(
            geom=GeomSitePoint(),
            stat=StatSiteMap(
                mode="points",
                x_source=mapping.get("x"),
                y_source=mapping.get("y"),
            ),
            mapping={"x": "x", "y": "y", "color": "color"},
            zorder=2,
        ),
        Layer(
            geom=GeomLabel(),
            stat=StatSiteMap(
                mode="labels",
                x_source=mapping.get("x"),
                y_source=mapping.get("y"),
                label_column=mapping.get("label"),
            ),
            mapping={"x": "x", "y": "y", "label": "label"},
            zorder=3,
        ),
    ]

    if settings_contours(recipe_settings):
        contours_cfg = dict(SITE_MAP_DEFAULTS["contours"])
        if isinstance(recipe_settings["contours"], dict):
            contours_cfg.update(recipe_settings["contours"])
        contours_cfg.pop("enabled", None)
        layers.insert(
            0,
            Layer(
                geom=GeomContour(
                    edgecolor=contours_cfg["color"],
                    edgealpha=contours_cfg.get("alpha"),
                    edgewidth=contours_cfg["linewidth"],
                ),
                stat=StatContour(
                    interval=contours_cfg["interval"],
                    dem_source=contours_cfg.get("dem_source"),
                    dem_bounds=contours_cfg.get("dem_bounds"),
                ),
                mapping={"x": "x", "y": "y"},
                zorder=1,
            ),
        )

    if streams_cfg is not None:
        layers.insert(
            2,
            Layer(
                geom=GeomStreams(
                    edgecolor=streams_cfg["color"],
                    edgealpha=streams_cfg.get("alpha"),
                    edgewidth=streams_cfg["linewidth"],
                ),
                stat=StatStreams(
                    streams_source=streams_cfg.get("streams_source"),
                    service_url=streams_cfg["service_url"],
                    layer_id=streams_cfg["layer_id"],
                    where=streams_cfg["where"],
                    max_pages=streams_cfg["max_pages"],
                ),
                mapping={"x": "x", "y": "y"},
                zorder=1,
            ),
        )

    return TemplateRecipe(
        name="site_map",
        layers=layers,
        coord=coord if coord is not None else CoordGeo(),
        default_settings=default_settings,
    )
