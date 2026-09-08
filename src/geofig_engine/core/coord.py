"""
Coord: Coordinate system transformations for figures.

Coords transform visual-domain values to screen space. They are applied
after scale resolution and before rendering, forming the final step in
the spec-building pipeline.
"""

from __future__ import annotations

import math
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
