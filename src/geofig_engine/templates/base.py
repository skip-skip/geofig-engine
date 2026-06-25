"""
Base template abstractions for FigEngine.

Templates define the contract between resolved data mappings and a FigureSpec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from geofig_engine.core.coord import Coord, CoordCartesian
from geofig_engine.core.layer import Layer


@dataclass(frozen=True)
class FigureTemplate:
    layers: list[Layer]
    default_settings: dict[str, Any] = field(default_factory=dict)
    coord: Coord = field(default_factory=CoordCartesian)

    def __post_init__(self) -> None:
        if not isinstance(self.layers, list) or not self.layers:
            raise ValueError("FigureTemplate requires at least one Layer")
        if not all(isinstance(l, Layer) for l in self.layers):
            raise TypeError("All items in layers must be Layer instances")
        if not isinstance(self.default_settings, dict):
            raise TypeError("default_settings must be a dict")
        if not isinstance(self.coord, Coord):
            raise TypeError("coord must be a Coord instance")
