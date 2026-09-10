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

**Basemap tiles are deferred to M2** (per the roadmaps) — the "basemap" here
is the boundary/context geometry rendered from the provider. The future tile
hook (M2) will sit below this layer stack and fetch/attach tile imagery; no
tile-service request is made or prepared by this template.

Optional boundary: when the provider frame carries a boundary-flag column
(name auto-detected from ``boundary``/``is_boundary``/``feature``/``ring``, or
set explicitly via ``mapping={"boundary": <column>}`` on a direct builder
call), the boundary layer plots exactly the flagged rows (NaN separator rows
between ring parts stay flagged so multipart outlines keep their gaps). With
no such column the boundary layer renders nothing.
"""

from __future__ import annotations

from typing import Any

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
    ``crs`` activates the ``[geo]`` projection path). Basemap tile basemaps
    are deferred to M2 — the future tile hook sits below this layer stack and
    makes no requests today.

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