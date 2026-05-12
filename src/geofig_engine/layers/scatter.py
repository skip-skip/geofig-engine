"""
Scatter plot layer for templates.

Layers define reusable building blocks for constructing FigureSpecs within templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from geofig_engine.layers.base import FigureLayer
from geofig_engine.utils.typing import ATTRIBUTE

from dataclasses import dataclass, field

@dataclass(frozen=True)
class ScatterLayer(FigureLayer):
    x: str = field(
        default="x",
        metadata={"attribute": ATTRIBUTE.X},
    )
    y: str = field(
        default="y",
        metadata={"attribute": ATTRIBUTE.Y},
    )
    y2: str | None = field(
        default=None,
        metadata={"attribute": ATTRIBUTE.Y2},
    )
    color: str | None = field(
        default="blue",
        metadata={"attribute": ATTRIBUTE.COLOR},
    )
    style: str | None = field(
        default="-",
        metadata={"attribute": ATTRIBUTE.STYLE},
    )
    width: float | None = field(
        default=1.5,
        metadata={"attribute": ATTRIBUTE.WIDTH},
    )
    alpha: float | None = field(
        default=0.8,
        metadata={"attribute": ATTRIBUTE.ALPHA},
    )