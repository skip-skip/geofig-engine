"""
Function line layer for templates. 
Creates a line across the entire plot based on a function of x or y.

Layers define reusable building blocks for constructing FigureSpecs within templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from geofig_engine.layers.base import FigureLayer
from geofig_engine.utils.typing import Channel

from dataclasses import dataclass, field

@dataclass(frozen=True)
class FunctionLineLayer(FigureLayer):
    
    func: str = ""            # function reference key
    label: str | None = None

    x: str = field(
        default="x",
        metadata={"channel": Channel.X},
    )
    color: str | None = field(
        default="blue",
        metadata={"channel": Channel.COLOR},
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