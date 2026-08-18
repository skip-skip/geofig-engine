"""
Coord: Coordinate system transformations for figures.

Coords transform visual-domain values to screen space. They are applied
after scale resolution and before rendering, forming the final step in
the spec-building pipeline.
"""

from __future__ import annotations

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


@dataclass(frozen=True)
class PiperCoord(Coord):
    left_tri: tuple[str, str, str] = ("Ca", "Mg", "Na+K")
    right_tri: tuple[str, str, str] = ("HCO3", "SO4", "Cl")

    def __init__(
        self,
        left_tri: tuple[str, str, str] = ("Ca", "Mg", "Na+K"),
        right_tri: tuple[str, str, str] = ("HCO3", "SO4", "Cl"),
    ) -> None:
        object.__setattr__(self, "left_tri", left_tri)
        object.__setattr__(self, "right_tri", right_tri)
        super().__init__(
            name="piper",
            params={
                "left_tri": list(left_tri),
                "right_tri": list(right_tri),
            },
        )


@dataclass(frozen=True)
class StiffCoord(Coord):
    ca: float = 0.0
    mg: float = 0.0
    na_k: float = 0.0
    cl: float = 0.0
    hco3: float = 0.0
    so4: float = 0.0
    sample_title: str = ""

    def __init__(
        self,
        ca: float = 0.0,
        mg: float = 0.0,
        na_k: float = 0.0,
        cl: float = 0.0,
        hco3: float = 0.0,
        so4: float = 0.0,
        sample_title: str = "",
    ) -> None:
        object.__setattr__(self, "ca", ca)
        object.__setattr__(self, "mg", mg)
        object.__setattr__(self, "na_k", na_k)
        object.__setattr__(self, "cl", cl)
        object.__setattr__(self, "hco3", hco3)
        object.__setattr__(self, "so4", so4)
        object.__setattr__(self, "sample_title", sample_title)
        max_val = max(ca, mg, na_k, cl, hco3, so4) or 1.0
        super().__init__(
            name="stiff",
            params={
                "ca": ca, "mg": mg, "na_k": na_k,
                "cl": cl, "hco3": hco3, "so4": so4,
                "sample_title": sample_title,
                "max_val": max_val,
            },
        )
