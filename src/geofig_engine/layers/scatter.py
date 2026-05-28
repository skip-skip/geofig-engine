"""
Scatter plot layer for templates.

Layers define reusable building blocks for constructing FigureSpecs within templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from geofig_engine.layers.base import FigureLayer
from geofig_engine.utils.typing import Channel

from dataclasses import dataclass, field

@dataclass(frozen=True)
class ScatterLayer(FigureLayer):
    x: str = field(
        default="x",
        metadata={"channel": Channel.X},
    )
    y: str = field(
        default="y",
        metadata={"channel": Channel.Y},
    )
    y2: str | None = field(
        default=None,
        metadata={"channel": Channel.Y2},
    )
    color: str | None = field(
        default="blue",
        metadata={"channel": Channel.COLOR},
    )
    marker: str | None = field(
        default="o",
        metadata={"channel": Channel.MARKER},
    )
    size: float | None = field(
        default=20.0,
        metadata={"channel": Channel.SIZE},
    )
    style: str | None = field(
        default="-",
        metadata={"channel": Channel.STYLE},
    )
    width: float | None = field(
        default=1.5,
        metadata={"channel": Channel.WIDTH},
    )
    alpha: float | None = field(
        default=0.8,
        metadata={"channel": Channel.ALPHA},
    )
