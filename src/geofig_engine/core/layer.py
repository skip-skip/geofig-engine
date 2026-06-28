"""
Layer: A composable unit binding Geom + Stat + mappings + scales.

A Layer represents one visual element in a figure (e.g., a scatter plot,
a line, a function reference line). Multiple layers are composed to create
a complete figure. Resolution of selectors and scales happens downstream
in the FigureGenerator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from geofig_engine.core.geom import Geom
from geofig_engine.core.stat import Stat, StatIdentity
from geofig_engine.core.scale import Scale
from geofig_engine.utils.typing import SourceType


@dataclass(frozen=True)
class Layer:
    geom: Geom
    stat: Stat = field(default_factory=StatIdentity)
    mapping: dict[str, SourceType] = field(default_factory=dict)
    scales: dict[str, Scale] | None = None
    data_override: str | None = None
    zorder: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.geom, Geom):
            raise TypeError("geom must be a Geom instance")
        if not isinstance(self.stat, Stat):
            raise TypeError("stat must be a Stat instance")
        if not isinstance(self.mapping, dict):
            raise TypeError("mapping must be a dict")

        if self.scales is not None and not isinstance(self.scales, dict):
            raise TypeError("scales must be a dict or None")

        if self.data_override is not None and not isinstance(self.data_override, str):
            raise TypeError("data_override must be a string or None")

        if self.zorder is not None and not isinstance(self.zorder, int):
            raise TypeError("zorder must be an int or None")


@dataclass(frozen=True)
class LayerSpec:
    geom: Geom
    stat: Stat
    visual_mapping: dict[str, Any]
    data_override: str | None = None
    coord: Any = None
    zorder: int | None = None
