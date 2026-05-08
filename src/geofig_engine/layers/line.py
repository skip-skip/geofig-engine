"""
Line plot layer for templates.

Layers define reusable building blocks for constructing FigureSpecs within templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from geofig_engine.layers.base import FigureLayer

@dataclass(frozen=True)
class LineLayer(FigureLayer):
    x: str = 'x'
    y: str = 'y'
    y2: str | None = None
    color: str | None = 'blue'
    style: str | None = '-'
    width: float | None = 1.5
    alpha: float | None = 0.8