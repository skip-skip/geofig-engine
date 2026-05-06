"""
Scatter plot layer for templates.

Layers define reusable building blocks for constructing FigureSpecs within templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from geofig_engine.layers.base import FigureLayer

@dataclass(frozen=True)
class ScatterLayer(FigureLayer):
    x: str = 'x'
    y: str = 'y'
    color: str | None = 'blue'
    marker: str | None = 'o'
    size: float | None = 36
    alpha: float | None = 0.8