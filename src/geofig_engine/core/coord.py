"""
Coord: Coordinate system transformations for figures.

Coords transform visual-domain values to screen space. They are applied
after scale resolution and before rendering, forming the final step in
the spec-building pipeline.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Coord:
    name: str
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Coord name must be a non-empty string")
        if not isinstance(self.params, dict):
            raise TypeError("params must be a dict")

    def aspect_ratio(self) -> float | None:
        return None

    def transform_visual_mapping(self, visual_mapping: dict, geom: Any) -> dict:
        """Transform visual mapping values according to this coordinate system.

        Called after filtering but before rendering. The default is a no-op;
        subclasses override to convert channel values (e.g. categories to angles).
        """
        return visual_mapping


@dataclass(frozen=True)
class CoordCartesian(Coord):
    def __init__(self) -> None:
        super().__init__(name="cartesian")


@dataclass(frozen=True)
class CoordFlipped(Coord):
    def __init__(self) -> None:
        super().__init__(name="flipped")


@dataclass(frozen=True)
class CoordPolar(Coord):
    theta: str = "x"
    start: float = 0.0
    end: float = 360.0

    def __init__(
        self, theta: str = "x", start: float = 0.0, end: float = 360.0
    ) -> None:
        super().__init__(
            name="polar",
            params={"theta": theta, "start": start, "end": end},
        )

    def aspect_ratio(self) -> float | None:
        return 1.0

    def transform_visual_mapping(self, visual_mapping: dict, geom: Any) -> dict:
        """Convert categorical x values to angular positions on [0, 2π)."""
        vm = dict(visual_mapping)
        x = vm.get("x")
        if x is not None and isinstance(x, pd.Series) and not pd.api.types.is_numeric_dtype(x):
            categories = x.unique()
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False)
            angle_map = dict(zip(categories, angles))
            vm["x"] = x.map(angle_map).astype(float)
        return vm


@dataclass(frozen=True)
class CoordFixed(Coord):
    ratio: float = 1.0

    def __init__(self, ratio: float = 1.0) -> None:
        if ratio <= 0:
            raise ValueError("aspect ratio must be positive")
        super().__init__(name="fixed", params={"ratio": ratio})

    def aspect_ratio(self) -> float | None:
        return float(self.params["ratio"])


# ---------------------------------------------------------------------------
# Ternary projection (Phase 14.5)
# ---------------------------------------------------------------------------

TERNARY_HEIGHT: float = math.sqrt(3.0) / 2.0
"""Height of the local ternary triangle with unit base (equilateral)."""


def _validate_ternary_channels(channels) -> tuple[str, str, str]:
    if isinstance(channels, str) or not isinstance(channels, (tuple, list)):
        raise TypeError("channels must be a sequence of three channel names")
    if len(channels) != 3:
        raise ValueError(f"channels must contain exactly three names, got {channels!r}")
    for ch in channels:
        if not isinstance(ch, str) or not ch.strip():
            raise ValueError(f"channel names must be non-empty strings, got {channels!r}")
    if len(set(channels)) != 3:
        raise ValueError(f"channel names must be distinct, got {channels!r}")
    return tuple(channels)


def _validate_handedness(handedness) -> str:
    if handedness not in ("left", "right"):
        raise ValueError(f"handedness must be 'left' or 'right', got {handedness!r}")
    return handedness


def ternary_project(a, b, c, handedness: str = "left"):
    """
    Project ternary fractions onto local triangle coordinates.

    Local space is an equilateral triangle with unit base: apex at
    ``(0.5, sqrt(3)/2)``, bottom-left corner ``(0, 0)``, bottom-right corner
    ``(1, 0)``. A point's position is the fraction-weighted corner average
    ``a*apex + b*bottom_left + c*bottom_right``.

    ``handedness="right"`` mirrors the triangle horizontally (b and c swap
    corners), matching Piper anion-triangle reading direction; ``"left"``
    keeps b at bottom-left.

    Inputs are normalized by their row sum, so fractions need not sum to
    exactly 1; rows whose total is zero (or contains NaN) produce NaN.
    """
    handedness = _validate_handedness(handedness)
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    c = np.asarray(c, dtype=float)
    x = 0.5 * a + c
    y = TERNARY_HEIGHT * a
    if handedness == "right":
        x = 1.0 - x
    return x, y


@dataclass(frozen=True)
class TernaryCoord(Coord):
    """
    Ternary projection for linked axes (Phase 14.5).

    Consumes three fraction channels from a layer's visual mapping and
    rewrites them into local ``x``/``y`` positions on the equilateral
    triangle described by :func:`ternary_project`. Non-fraction mapping
    entries (color, style, ...) pass through untouched, keeping geoms
    projection-agnostic.

    Attributes:
        channels: Names of the three fraction channels in the visual
            mapping, ordered (apex, bottom-left, bottom-right).
        handedness: "left" or "right"; mirrors the triangle horizontally.
        labels: Optional display labels for the three vertices (defaults to
            ``channels``, so data column names can differ from the rendered
            label — e.g. charge-bearing superscripts like ``$Ca^{++}$``).

    Rows are normalized by their fraction sum; zero-total rows become NaN.
    """

    channels: tuple[str, str, str] = ("a", "b", "c")
    handedness: str = "left"
    labels: tuple[str, str, str] | None = None

    def __init__(
        self,
        channels: tuple[str, str, str] = ("a", "b", "c"),
        handedness: str = "left",
        labels: tuple[str, str, str] | None = None,
    ) -> None:
        chans = _validate_ternary_channels(channels)
        _validate_handedness(handedness)
        object.__setattr__(self, "channels", chans)
        object.__setattr__(self, "handedness", handedness)
        labs = chans if labels is None else self._validate_labels(labels)
        object.__setattr__(self, "labels", labs)
        params: dict[str, Any] = {"channels": list(chans), "handedness": handedness}
        if labels is not None:
            params["labels"] = list(labs)
        super().__init__(name="ternary", params=params)

    @staticmethod
    def _validate_labels(labels) -> tuple[str, str, str]:
        if not isinstance(labels, (tuple, list)) or len(labels) != 3:
            raise ValueError(
                f"Ternary labels must be a 3-tuple of strings, got {labels!r}"
            )
        if not all(isinstance(l, str) for l in labels):
            raise ValueError(f"Ternary labels must be 3 strings, got {labels!r}")
        return tuple(labels)

    def transform_visual_mapping(self, visual_mapping: dict, geom: Any) -> dict:
        """Rewrite the three fraction channels into local x/y positions."""
        vm = dict(visual_mapping)
        missing = [ch for ch in self.channels if ch not in vm]
        if missing:
            raise ValueError(
                f"TernaryCoord requires mapping channels {missing!r} "
                f"(configured channels: {list(self.channels)})"
            )
        series_list = []
        for ch in self.channels:
            val = vm[ch]
            if not isinstance(val, pd.Series):
                raise TypeError(
                    f"ternary channel {ch!r} must map to a data column "
                    f"(pd.Series), got {type(val).__name__}"
                )
            series_list.append(val)
        frame = pd.concat(series_list, axis=1)
        values = frame.to_numpy(dtype=float)
        totals = values.sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            frac = np.where(
                totals[:, None] > 0, values / totals[:, None], np.nan
            )
        x, y = ternary_project(*frac.T, handedness=self.handedness)
        vm["x"] = pd.Series(x, index=frame.index)
        vm["y"] = pd.Series(y, index=frame.index)
        for ch in self.channels:
            del vm[ch]
        return vm


# ---------------------------------------------------------------------------
# Geographic coordinate (Phase 15, wp8)
# ---------------------------------------------------------------------------

WGS84 = "EPSG:4326"
"""Default geographic CRS — lon/lat, for which no projection is applied."""


def _import_geo_transformer():
    """Return the ``pyproj.Transformer`` callable, or None without [geo]."""
    try:
        from pyproj import Transformer  # type: ignore[import-not-found]

        return Transformer
    except ImportError:
        return None


def _validate_bounds(bounds) -> tuple[float, float, float, float]:
    if not isinstance(bounds, (tuple, list)) or len(bounds) != 4:
        raise ValueError(
            f"bounds must be a 4-tuple (min_lon, min_lat, max_lon, max_lat), "
            f"got {bounds!r}"
        )
    vals: list[float] = []
    for v in bounds:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"bounds entries must be real numbers, got {bounds!r}")
        vals.append(float(v))
    if vals[0] >= vals[2] or vals[1] >= vals[3]:
        raise ValueError(
            "bounds must satisfy min_lon < max_lon and min_lat < max_lat, "
            f"got {bounds!r}"
        )
    return tuple(vals)


@dataclass(frozen=True)
class CoordGeo(Coord):
    """Geographic coordinate system: lon/lat -> projected CRS.

    The data is assumed to be WGS84 lon/lat. ``crs`` declares the figure's
    output CRS (default ``WGS84`` — identity, no projection). When a non-WGS84
    ``crs`` is requested, :meth:`transform_visual_mapping` projects lon/lat
    into that CRS via the ``[geo]`` extra (pyproj); without it the mapping
    falls back to an identity (lon/lat -> x/y) projection with a clear note.
    ``bounds`` (in ``bounds_crs``, defaulting to ``crs``) and ``aspect`` are
    declared and validated here; their axis-level application is M2 polish.
    """

    crs: str = WGS84
    bounds: tuple[float, float, float, float] | None = None
    bounds_crs: str | None = None
    aspect: float | None = None

    def __init__(
        self,
        crs: str = WGS84,
        bounds: tuple[float, float, float, float] | None = None,
        bounds_crs: str | None = None,
        aspect: float | None = None,
    ) -> None:
        if not isinstance(crs, str) or not crs.strip():
            raise ValueError(f"crs must be a non-empty CRS string, got {crs!r}")
        if bounds is not None:
            bounds = _validate_bounds(bounds)
            if bounds_crs is None:
                bounds_crs = crs
            if not isinstance(bounds_crs, str) or not bounds_crs.strip():
                raise ValueError(
                    f"bounds_crs must be a non-empty CRS string, got {bounds_crs!r}"
                )
        if aspect is not None and (
            isinstance(aspect, bool)
            or not isinstance(aspect, (int, float))
            or aspect <= 0
        ):
            raise ValueError(
                f"aspect must be a positive real number or None, got {aspect!r}"
            )
        object.__setattr__(self, "crs", crs)
        object.__setattr__(self, "bounds", bounds)
        object.__setattr__(self, "bounds_crs", bounds_crs)
        object.__setattr__(self, "aspect", float(aspect) if aspect is not None else None)
        params: dict[str, Any] = {"crs": crs}
        if bounds is not None:
            params["bounds"] = list(bounds)
            params["bounds_crs"] = bounds_crs
        if aspect is not None:
            params["aspect"] = float(aspect)
        super().__init__(name="geo", params=params)

    def aspect_ratio(self) -> float | None:
        return self.aspect

    def transform_visual_mapping(self, visual_mapping: dict, geom: Any) -> dict:
        """Project lon/lat ``x``/``y`` into ``crs``; identity fallback without pyproj."""
        x = visual_mapping.get("x")
        y = visual_mapping.get("y")
        if self.crs == WGS84 or x is None or y is None:
            return dict(visual_mapping)
        Transformer = _import_geo_transformer()
        if Transformer is None:
            warnings.warn(
                "pyproj is not installed; CoordGeo falls back to an identity "
                f"(lon/lat -> x/y) projection for crs={self.crs!r}. Install the "
                "'[geo]' extra for projected output.",
                UserWarning,
                stacklevel=3,
            )
            return dict(visual_mapping)

        vm = dict(visual_mapping)
        x_vals = x.values if isinstance(x, pd.Series) else np.asarray(x)
        y_vals = y.values if isinstance(y, pd.Series) else np.asarray(y)
        transformer = Transformer.from_crs(WGS84, self.crs, always_xy=True)
        px, py = transformer.transform(
            np.asarray(x_vals, dtype=float), np.asarray(y_vals, dtype=float)
        )
        if isinstance(x, pd.Series):
            vm["x"] = pd.Series(np.asarray(px), index=x.index)
            vm["y"] = pd.Series(np.asarray(py), index=y.index)
        else:
            vm["x"] = np.asarray(px)
            vm["y"] = np.asarray(py)
        return vm
