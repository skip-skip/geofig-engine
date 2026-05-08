"""
Global line layer for templates. Creates a line across the entire plot based on a function of x.

Layers define reusable building blocks for constructing FigureSpecs within templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from geofig_engine.layers.base import FigureLayer
from enum import Enum

@dataclass(frozen=True)
class GlobalLineLayer(FigureLayer):
    func: str = ""            # function reference key
    color: str = "black"
    linestyle: str = "--"
    linewidth: float = 1.5
    label: str | None = None