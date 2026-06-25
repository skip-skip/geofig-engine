"""
Geom: Geometric object types for visual marks.

Geoms define what kind of mark to draw (point, line, bar, etc.)
and which visual channels they require or accept. They are purely
declarative — no rendering logic, no data transformation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Channel(Enum):
    X = "x"
    Y = "y"
    Y2 = "y2"
    COLOR = "color"
    MARKER = "marker"
    SIZE = "size"
    STYLE = "style"
    ALPHA = "alpha"
    WIDTH = "width"
    LABEL = "label"
    FUNC = "func"
    YMIN = "ymin"
    YMAX = "ymax"


@dataclass(frozen=True)
class Geom:
    name: str
    required_channels: tuple[str, ...]
    optional_channels: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Geom name must be a non-empty string")
        if not isinstance(self.required_channels, tuple):
            raise TypeError("required_channels must be a tuple")
        if not isinstance(self.optional_channels, tuple):
            raise TypeError("optional_channels must be a tuple")
        all_channels = set(self.required_channels) | set(self.optional_channels)
        valid = {c.value for c in Channel}
        invalid = all_channels - valid
        if invalid:
            raise ValueError(f"Invalid channel(s): {invalid}. Must be one of {valid}")


@dataclass(frozen=True)
class GeomPoint(Geom):
    def __init__(self) -> None:
        super().__init__(
            name="point",
            required_channels=("x", "y"),
            optional_channels=("color", "marker", "size", "alpha"),
        )


@dataclass(frozen=True)
class GeomLine(Geom):
    def __init__(self) -> None:
        super().__init__(
            name="line",
            required_channels=("x", "y"),
            optional_channels=("color", "style", "width", "alpha"),
        )


@dataclass(frozen=True)
class GeomFunctionLine(Geom):
    func: str = ""
    label: str | None = None

    def __init__(self, func: str = "", label: str | None = None) -> None:
        object.__setattr__(self, "func", func)
        object.__setattr__(self, "label", label)
        super().__init__(
            name="function_line",
            required_channels=("x",),
            optional_channels=("color", "style", "width", "alpha", "label"),
        )


@dataclass(frozen=True)
class GeomBar(Geom):
    def __init__(self) -> None:
        super().__init__(
            name="bar",
            required_channels=("x", "y"),
            optional_channels=("color", "alpha", "width"),
        )


@dataclass(frozen=True)
class GeomArea(Geom):
    def __init__(self) -> None:
        super().__init__(
            name="area",
            required_channels=("x", "y"),
            optional_channels=("color", "alpha"),
        )


@dataclass(frozen=True)
class GeomRibbon(Geom):
    def __init__(self) -> None:
        super().__init__(
            name="ribbon",
            required_channels=("x", "ymin", "ymax"),
            optional_channels=("color", "alpha"),
        )


@dataclass(frozen=True)
class GeomText(Geom):
    def __init__(self) -> None:
        super().__init__(
            name="text",
            required_channels=("x", "y", "label"),
            optional_channels=("color", "size", "alpha"),
        )


@dataclass(frozen=True)
class GeomErrorbar(Geom):
    def __init__(self) -> None:
        super().__init__(
            name="errorbar",
            required_channels=("x", "y", "ymin", "ymax"),
            optional_channels=("color", "width", "alpha"),
        )
