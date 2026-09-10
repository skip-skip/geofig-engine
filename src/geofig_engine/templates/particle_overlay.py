"""
Particle overlay registry template (15_wp10).

Per-photo QA overlay for ``ParticleImageModel``-style results (consumed
duck-typed — no ``geochemmodel``/``geodata`` import): the (downsampled)
source image as an ``OffsetImage`` inset behind the layer stack, the
segmentation edges (closed particle contours), classified particle centroids,
and a QA-stats caption. Mirrors the ``geochemmapper`` figure described in
``ARCHITECTURE.md`` Templates & Registry: "per-photo QA overlay: segmentation
edges on the (downsampled) source image, classified particles, per-photo QA
stats".

Data contract (one photo per frame; all column detection is by candidate
names, first present wins, and a builder ``mapping`` pins any of them):

- ``image`` (alias ``source`` — the upstream ``VisualizationEncoding`` binds
  the ``image`` channel to the ``"source"`` artifact): a 2-D gray or 3-D RGB
  ndarray **cell** holding the source image. Required — an absent image
  raises a clear ``ValueError`` instead of rendering a blank figure.
- ``x`` / ``y`` (aliases ``centroid_x``/``centroid_y``, ``cx``/``cy``): the
  particle centroid in image pixels (x = column, y = row — the cv2/contour
  convention). Required for the points layer.
- ``class`` (alias ``phase`` — the real upstream column): per-particle
  class/phase, bound to the point ``color`` channel (NaN falls back to the
  geom group name ``Particles``). Optional; without it all points share one
  neutral color and one legend entry.
- ``area_px`` (alias ``area``): measured area, bound to the point ``size``
  channel (NaN falls back to the default point size). Optional.
- ``contour_x`` / ``contour_y`` (aliases ``cx_ring``/``cy_ring``): per-row
  lists of the particle ring's vertex coordinates (closed rings). Optional;
  without them the contour layer renders nothing.
- QA caption columns (all optional): ``qa_flag`` (bool per particle →
  excluded fraction), ``excluded_fraction``, ``mean_intensity``.

The image layer uses the wp8 ``GeomImageInset`` (``OffsetImage`` anchor at
the data-centroid mean, ``zoom`` from the ``inset_zoom`` setting); contour
edges draw with ``GeomBoundary`` (white edges, so they read over the imagery);
centroids with ``GeomPoint`` (color by class, size by area); and the QA
caption with ``GeomText`` (fontsize from the ``qa_fontsize`` setting). All
derivation happens in the spec-build ``StatParticleOverlay`` (numpy/pandas
only), so spec building stays matplotlib-free.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from geofig_engine.core.coord import CoordCartesian
from geofig_engine.core.geom import GeomBoundary, GeomImageInset, GeomPoint, GeomText
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import Stat

PARTICLE_OVERLAY_DEFAULTS: dict[str, Any] = {
    "figsize": (6, 6),
    "title": "Particle Overlay",
    "xlabel": "x (px)",
    "ylabel": "y (px)",
    "inset_zoom": 2.0,
    "qa_fontsize": 9.0,
}

#: Centroid-column candidates, in preference order (first present wins).
X_CANDIDATES: tuple[str, ...] = ("x", "centroid_x", "cx")
Y_CANDIDATES: tuple[str, ...] = ("y", "centroid_y", "cy")

#: Class/phase-column candidates for point coloring (first present wins).
CLASS_CANDIDATES: tuple[str, ...] = ("class", "phase")

#: Measured-area candidates for point sizing (first present wins).
AREA_CANDIDATES: tuple[str, ...] = ("area_px", "area")

#: Contour vertex-list candidates (first present wins).
CONTOUR_X_CANDIDATES: tuple[str, ...] = ("contour_x", "cx_ring")
CONTOUR_Y_CANDIDATES: tuple[str, ...] = ("contour_y", "cy_ring")

#: Image-array cell candidates (the upstream encoding maps the image channel
#: to the "source" artifact).
IMAGE_CANDIDATES: tuple[str, ...] = ("image", "source")

#: Neutral color-group name when the frame has no class column (mirrors the
#: site_map "Sites" fallback).
PARTICLE_GROUP = "Particles"

DEFAULT_POINT_SIZE = 20.0


def _first_present(candidates: tuple[str, ...], frame: pd.DataFrame) -> str | None:
    """First candidate that is a column of ``frame``, else ``None``."""
    for name in candidates:
        if name in frame.columns:
            return name
    return None


def _empty_with_columns(columns: list[str]) -> pd.DataFrame:
    """An empty frame that still exposes ``columns`` (0 rows)."""
    return pd.DataFrame(
        {
            col: pd.Series(dtype="float64" if col in ("x", "y") else object)
            for col in columns
        }
    )


class StatParticleOverlay(Stat):
    """Spec-build transform that derives the particle-overlay layer channels.

    One stat instance is shared by the recipe's four layers via its ``mode``:

    - ``"image"`` — extracts the source-image array cell and anchors an
      ``OffsetImage`` at the data-centroid mean. An absent image column (or
      all-NaN cells) raises a clear ``ValueError``.
    - ``"contours"`` — explodes the per-row ``contour_x``/``contour_y`` vertex
      lists into one NaN-broken ``x``/``y`` polyline, closing each ring by
      repeating its first vertex. Returns an empty x/y frame when no contour
      columns exist, so the layer renders nothing.
    - ``"points"`` — the particle centroids. Never row-filters (the visual
      series must stay index-aligned with ``FigureSpec.data`` for legend
      accumulation); exposes canonical ``x``/``y`` plus a canonical ``color``
      column = the class column (NaN values falling back to the geom group
      name ``Particles``) and a canonical ``size`` column = the measured area
      (NaN falling back to the default point size).
    - ``"qa"`` — one row: the QA caption text anchored at the top-left of the
      centroid extent, with a ``size`` constant for the caption fontsize.

    The original frame columns are preserved on the ``"points"`` output, so a
    ``mapping={"color": <column>}`` override through ``render_template`` can
    remap the point color onto any provider column (exactly the site_map
    pattern).

    Every ``*_source`` parameter pins the corresponding detector (they are the
    per-key values of a direct-builder mapping); missing required columns
    raise an informative ``ValueError``.
    """

    def __init__(
        self,
        mode: str = "points",
        x_source: str | None = None,
        y_source: str | None = None,
        class_source: str | None = None,
        area_source: str | None = None,
        contour_x_source: str | None = None,
        contour_y_source: str | None = None,
        image_source: str | None = None,
        qa_fontsize: float = 9.0,
    ) -> None:
        if mode not in ("image", "contours", "points", "qa"):
            raise ValueError(
                "StatParticleOverlay mode must be 'image', 'contours', "
                f"'points', or 'qa'; got {mode!r}"
            )
        for name, value in (
            ("x_source", x_source),
            ("y_source", y_source),
            ("class_source", class_source),
            ("area_source", area_source),
            ("contour_x_source", contour_x_source),
            ("contour_y_source", contour_y_source),
            ("image_source", image_source),
        ):
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{name} must be a column name or None, got {value!r}")
        if isinstance(qa_fontsize, bool) or not isinstance(qa_fontsize, (int, float)):
            raise ValueError(f"qa_fontsize must be a real number, got {qa_fontsize!r}")
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "x_source", x_source)
        object.__setattr__(self, "y_source", y_source)
        object.__setattr__(self, "class_source", class_source)
        object.__setattr__(self, "area_source", area_source)
        object.__setattr__(self, "contour_x_source", contour_x_source)
        object.__setattr__(self, "contour_y_source", contour_y_source)
        object.__setattr__(self, "image_source", image_source)
        object.__setattr__(self, "qa_fontsize", float(qa_fontsize))
        super().__init__(
            name="particle_overlay",
            params={
                "mode": mode,
                "x_source": x_source,
                "y_source": y_source,
                "class_source": class_source,
                "area_source": area_source,
                "contour_x_source": contour_x_source,
                "contour_y_source": contour_y_source,
                "image_source": image_source,
                "qa_fontsize": float(qa_fontsize),
            },
        )

    # ------------------------------------------------------------------
    # Column detection
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
                "particle_overlay: no centroid columns found in the provider. "
                f"Looked for x in {X_CANDIDATES} and y in {Y_CANDIDATES}; "
                "pass a mapping override with the centroid column names."
            )
        for col, axis in ((x_col, "x"), (y_col, "y")):
            if col not in data.columns:
                raise ValueError(
                    f"particle_overlay: {axis} column '{col}' not found in the "
                    f"provider (available columns: {sorted(data.columns)})"
                )
        return x_col, y_col

    def _image_column(self, data: pd.DataFrame) -> str | None:
        if self.image_source is not None:
            if self.image_source not in data.columns:
                raise ValueError(
                    f"particle_overlay: image column '{self.image_source}' not "
                    f"found in the provider (available columns: "
                    f"{sorted(data.columns)})"
                )
            return self.image_source
        return _first_present(IMAGE_CANDIDATES, data)

    def _class_column(self, data: pd.DataFrame) -> str | None:
        if self.class_source is not None:
            if self.class_source not in data.columns:
                raise ValueError(
                    f"particle_overlay: class column '{self.class_source}' not "
                    f"found in the provider (available columns: "
                    f"{sorted(data.columns)})"
                )
            return self.class_source
        return _first_present(CLASS_CANDIDATES, data)

    def _area_column(self, data: pd.DataFrame) -> str | None:
        if self.area_source is not None:
            if self.area_source not in data.columns:
                raise ValueError(
                    f"particle_overlay: area column '{self.area_source}' not "
                    f"found in the provider (available columns: "
                    f"{sorted(data.columns)})"
                )
            return self.area_source
        return _first_present(AREA_CANDIDATES, data)

    def _contour_columns(self, data: pd.DataFrame) -> tuple[str | None, str | None]:
        cx = self.contour_x_source if self.contour_x_source is not None else (
            _first_present(CONTOUR_X_CANDIDATES, data)
        )
        cy = self.contour_y_source if self.contour_y_source is not None else (
            _first_present(CONTOUR_Y_CANDIDATES, data)
        )
        if cx is not None and cx not in data.columns:
            raise ValueError(
                f"particle_overlay: contour column '{cx}' not found in the "
                f"provider (available columns: {sorted(data.columns)})"
            )
        if cy is not None and cy not in data.columns:
            raise ValueError(
                f"particle_overlay: contour column '{cy}' not found in the "
                f"provider (available columns: {sorted(data.columns)})"
            )
        return (cx, cy) if cx is not None and cy is not None else (None, None)

    # ------------------------------------------------------------------
    # Stat contract
    # ------------------------------------------------------------------

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        if self.mode == "image":
            return self._image_frame(data)

        x_col, y_col = self._coordinate_columns(data)

        if self.mode == "contours":
            return self._contours_frame(data)

        if self.mode == "points":
            return self._points_frame(data, x_col, y_col)

        # qa mode
        return self._qa_frame(data, x_col, y_col)

    # ------------------------------------------------------------------
    # Mode frames
    # ------------------------------------------------------------------

    def _image_frame(self, data: pd.DataFrame) -> pd.DataFrame:
        img_col = self._image_column(data)
        if img_col is None:
            raise ValueError(
                "particle_overlay: no image column found in the provider. The "
                "source image must arrive as a 2-D/3-D array in a cell of the "
                f"frame (looked for {IMAGE_CANDIDATES}); pass a mapping "
                "override with the image column name."
            )
        cells = [c for c in data[img_col].tolist() if c is not None]
        if not cells:
            raise ValueError(
                f"particle_overlay: image column '{img_col}' has no array cell "
                "(all values are null); cannot render a blank figure."
            )
        image = cells[0]
        x_col, y_col = self._coordinate_columns(data)
        x = float(data[x_col].mean())
        y = float(data[y_col].mean())
        return pd.DataFrame({"x": [x], "y": [y], "image": [image]})

    def _contours_frame(self, data: pd.DataFrame) -> pd.DataFrame:
        cx_col, cy_col = self._contour_columns(data)
        if cx_col is None:
            return _empty_with_columns(["x", "y"])

        xs: list[float] = []
        ys: list[float] = []
        for _, row in data.iterrows():
            cx = row[cx_col]
            cy = row[cy_col]
            if cx is None or cy is None:
                continue
            if isinstance(cx, pd.Series) or not hasattr(cx, "__iter__"):
                continue
            if isinstance(cy, pd.Series) or not hasattr(cy, "__iter__"):
                continue
            ring_x = [float(v) for v in cx]
            ring_y = [float(v) for v in cy]
            if len(ring_x) < 3 or len(ring_y) < 3:
                continue
            # Close the ring, then NaN-separate it from the next ring so the
            # single boundary line keeps every particle's path open.
            ring_x.append(ring_x[0])
            ring_y.append(ring_y[0])
            xs.extend(ring_x)
            ys.extend(ring_y)
            xs.append(float("nan"))
            ys.append(float("nan"))
        if not xs:
            return _empty_with_columns(["x", "y"])
        # Trim the trailing separator.
        xs = xs[:-1]
        ys = ys[:-1]
        return pd.DataFrame({"x": xs, "y": ys})

    def _points_frame(
        self, data: pd.DataFrame, x_col: str, y_col: str
    ) -> pd.DataFrame:
        # Deliberately no row filtering: the visual series must stay
        # index-aligned with FigureSpec.data for legend accumulation.
        out = data.copy()
        out["x"] = out[x_col]
        out["y"] = out[y_col]
        class_col = self._class_column(out)
        if class_col is not None:
            # NaN class values fall back to the geom group name so the scatter
            # color sequence stays fully resolvable.
            out["color"] = out[class_col].fillna(PARTICLE_GROUP)
        else:
            out["color"] = PARTICLE_GROUP  # single-entry legend
        area_col = self._area_column(out)
        if area_col is not None:
            out["size"] = out[area_col].fillna(DEFAULT_POINT_SIZE)
        else:
            out["size"] = DEFAULT_POINT_SIZE
        return out

    def _qa_frame(
        self, data: pd.DataFrame, x_col: str, y_col: str
    ) -> pd.DataFrame:
        n = len(data)
        parts = [f"n={n} particles"]
        area_col = self._area_column(data)
        if area_col is not None:
            area = data[area_col].dropna()
            if len(area):
                parts.append(f"mean area {float(area.mean()):.0f} px²")
        if "mean_intensity" in data.columns:
            intensity = data["mean_intensity"].dropna()
            if len(intensity):
                parts.append(f"mean intensity {float(intensity.mean()):.1f}")
        if "qa_flag" in data.columns:
            flags = data["qa_flag"].dropna()
            if len(flags):
                excluded = float(flags.astype(bool).mean())
                parts.append(f"excluded {excluded:.0%}")
        elif "excluded_fraction" in data.columns:
            fracs = data["excluded_fraction"].dropna()
            if len(fracs):
                parts.append(f"excluded {float(fracs.mean()):.0%}")

        x = data[x_col].dropna()
        y = data[y_col].dropna()
        if len(x) and len(y):
            x_min, x_max = float(x.min()), float(x.max())
            y_min, y_max = float(y.min()), float(y.max())
            span_x = max(x_max - x_min, 1.0)
            span_y = max(y_max - y_min, 1.0)
            anchor_x = x_min + 0.03 * span_x
            anchor_y = y_max - 0.05 * span_y
        else:
            anchor_x, anchor_y = 0.0, 1.0
        return pd.DataFrame(
            {
                "x": [anchor_x],
                "y": [anchor_y],
                "label": [" · ".join(parts)],
                "size": [self.qa_fontsize],
            }
        )


def particle_overlay_builder(
    mapping: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
    **_,
) -> "TemplateRecipe":
    """Pipeline registry builder for the ``particle_overlay`` key (15_wp10).

    Returns the canonical recipe shape: an ``GeomImageInset`` background layer
    (the source image anchored at the data-centroid mean — wp8), a
    ``GeomBoundary`` layer for the closed particle contours (white edges so
    they read over the imagery), a ``GeomPoint`` layer (color by class, size
    by measured area), and a ``GeomText`` QA-stats caption, all under a plain
    ``CoordCartesian`` (image-pixel coordinates). Works with **no mapping**:
    image cell, centroids, class, area, and contour columns auto-resolve from
    the provider frame by candidate names. A direct-builder mapping may pin
    ``x``/``y`` (centroid columns), ``class`` (color column), ``area`` (size
    column), ``image`` (array-cell column), and ``contour_x``/``contour_y``
    (vertex-list columns); ``color`` is a per-call override on the points
    layer. An absent image column raises a clear ``ValueError`` rather than
    rendering a blank figure.

    The ``TemplateRecipe`` import is deferred to call time so this template
    module never depends on ``engine.api`` at import time.
    """
    from geofig_engine.engine.api import TemplateRecipe

    mapping = dict(mapping or {})
    merged = {**PARTICLE_OVERLAY_DEFAULTS, **(settings or {})}
    inset_zoom = float(merged.get("inset_zoom", 2.0))
    qa_fontsize = float(merged.get("qa_fontsize", 9.0))

    # All channels bind the stat-produced canonical columns ("x"/"y"/"color"/
    # "size"/"label"/"image") as plain strings, so render_template's per-layer
    # override can remap them onto provider columns; the image/contours/qa
    # stats row-filter, so overriding their x/y with full-frame columns is an
    # M1 edge (their row sets must stay stat-aligned to keep the filtered
    # series paired) — mirroring the site_map boundary/labels layers.
    layers = [
        Layer(
            geom=GeomImageInset(zoom=inset_zoom),
            stat=StatParticleOverlay(
                mode="image",
                x_source=mapping.get("x"),
                y_source=mapping.get("y"),
                image_source=mapping.get("image"),
            ),
            mapping={"x": "x", "y": "y", "image": "image"},
            zorder=1,
        ),
        Layer(
            geom=GeomBoundary(edgecolor="white", edgewidth=0.6),
            stat=StatParticleOverlay(
                mode="contours",
                contour_x_source=mapping.get("contour_x"),
                contour_y_source=mapping.get("contour_y"),
            ),
            mapping={"x": "x", "y": "y"},
            zorder=2,
        ),
        Layer(
            geom=GeomPoint(),
            stat=StatParticleOverlay(
                mode="points",
                x_source=mapping.get("x"),
                y_source=mapping.get("y"),
                class_source=mapping.get("class"),
                area_source=mapping.get("area"),
            ),
            mapping={"x": "x", "y": "y", "color": "color", "size": "size"},
            zorder=3,
        ),
        Layer(
            geom=GeomText(),
            stat=StatParticleOverlay(
                mode="qa",
                x_source=mapping.get("x"),
                y_source=mapping.get("y"),
                qa_fontsize=qa_fontsize,
            ),
            mapping={"x": "x", "y": "y", "label": "label", "size": "size"},
            zorder=4,
        ),
    ]

    return TemplateRecipe(
        name="particle_overlay",
        layers=layers,
        coord=CoordCartesian(),
        default_settings=merged,
    )