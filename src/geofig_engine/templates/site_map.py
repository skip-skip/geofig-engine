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
from geofig_engine.core.geom import GeomBoundary, GeomLabel, GeomSitePoint
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import Stat

SITE_MAP_DEFAULTS: dict[str, Any] = {
    "figsize": (10, 8),
    "title": "Site Map",
    "xlabel": "Longitude",
    "ylabel": "Latitude",
    "basemap": {"provider": "esri_world_imagery", "alpha": 0.6},
}

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


class StatContour(Stat):
    """Spec-build transform that derives DEM elevation contour lines.

    Acquires a DEM for the provider frame's lon/lat extent (via
    ``geofig_engine.io.dem.fetch_dem``, which applies the old-geomapper 10%
    lon/lat buffer), extracts isolines at multiples of ``interval`` meters,
    and emits a NaN-separated ``x``/``y`` frame — one continuous open
    polyline per contour segment, matching the ``StatParticleOverlay
    (mode="contours")`` frame shape that ``render_boundary`` draws as open
    multipart paths (handlers.py:1020).

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
        interval: float = 10,
        dem_source: Callable[[tuple[float, float, float, float]], Any] | None = None,
        dem_bounds: tuple[float, float, float, float] | None = None,
    ) -> None:
        if isinstance(interval, bool) or not isinstance(interval, (int, float)):
            raise ValueError(
                f"interval must be a positive real number, got {interval!r}"
            )
        if interval <= 0:
            raise ValueError(
                f"interval must be a positive real number, got {interval!r}"
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
                "interval": float(interval),
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

        try:
            if self.dem_source is not None:
                grid = self.dem_source(bbox)
            else:
                from geofig_engine.io.dem import fetch_dem

                grid = fetch_dem(*bbox, interval=self.params["interval"])
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

        levels = np.arange(np.nanmin(z), np.nanmax(z), self.params["interval"])
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


def site_map_builder(
    mapping: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
    coord: Coord | None = None,
    **_,
) -> "TemplateRecipe":
    """Pipeline registry builder for the ``site_map`` key (15_wp9).

    Returns the canonical recipe shape: a ``GeomBoundary`` basemap layer, a
    ``GeomSitePoint`` layer (with a pre-bound ``color`` channel the
    ``mapping={"color": ...}`` override remaps at ``render_template`` time),
    and a ``GeomLabel`` layer, all under a ``CoordGeo`` coord (default WGS84 —
    identity projection without the ``[geo]`` extra). Works with **no
    mapping**: coordinates, group coloring, and label columns auto-resolve
    from the provider frame by candidate names. A direct-builder mapping may
    pin ``x``/``y`` (coordinate columns), ``boundary`` (flag column),
    ``label`` (name column); ``color`` is a per-call override on the points
    layer.

    ``coord`` overrides the recipe's geographic coord (e.g. a non-WGS84
    ``crs`` activates the ``[geo]`` projection path). Basemap tiles are
    enabled by default (``SITE_MAP_DEFAULTS["basemap"]`` — Esri WorldImagery
    at alpha 0.6, fetched by the renderer below the layer stack; wp14).
    Disable with ``settings={"basemap": None}``, or override provider/zoom/
    alpha with a ``settings={"basemap": {...}}`` dict; an offline or
    ``[geo]``-less projected render degrades to tiles-off with a warning.

    The ``TemplateRecipe`` import is deferred to call time so this template
    module never depends on ``engine.api`` at import time.
    """
    from geofig_engine.engine.api import TemplateRecipe

    mapping = dict(mapping or {})

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

    return TemplateRecipe(
        name="site_map",
        layers=layers,
        coord=coord if coord is not None else CoordGeo(),
        default_settings={**SITE_MAP_DEFAULTS, **(settings or {})},
    )