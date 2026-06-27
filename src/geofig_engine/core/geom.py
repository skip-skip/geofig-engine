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
    jitter: float = 0.0
    dodge: float = 0.0

    def __init__(self, jitter: float = 0.0, dodge: float = 0.0) -> None:
        object.__setattr__(self, "jitter", jitter)
        object.__setattr__(self, "dodge", dodge)
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


@dataclass(frozen=True)
class GeomBox(Geom):
    showfliers: bool = True
    showmeans: bool = False
    show_n: bool = False
    min_box_n: int = 1
    is_horizontal: bool = False
    sort_mode: str = "none"
    smush: bool = False
    box_width: float = 0.8

    def __init__(
        self,
        showfliers: bool = True,
        showmeans: bool = False,
        show_n: bool = False,
        min_box_n: int = 1,
        is_horizontal: bool = False,
        sort_mode: str = "none",
        smush: bool = False,
        box_width: float = 0.8,
    ) -> None:
        object.__setattr__(self, "showfliers", showfliers)
        object.__setattr__(self, "showmeans", showmeans)
        object.__setattr__(self, "show_n", show_n)
        object.__setattr__(self, "min_box_n", min_box_n)
        object.__setattr__(self, "is_horizontal", is_horizontal)
        object.__setattr__(self, "sort_mode", sort_mode)
        object.__setattr__(self, "smush", smush)
        object.__setattr__(self, "box_width", box_width)
        super().__init__(
            name="box",
            required_channels=("x", "y"),
            optional_channels=("color", "alpha"),
        )


@dataclass(frozen=True)
class GeomViolin(Geom):
    show_medians: bool = True
    sort_mode: str = "none"
    smush: bool = False

    def __init__(
        self,
        show_medians: bool = True,
        sort_mode: str = "none",
        smush: bool = False,
    ) -> None:
        object.__setattr__(self, "show_medians", show_medians)
        object.__setattr__(self, "sort_mode", sort_mode)
        object.__setattr__(self, "smush", smush)
        super().__init__(
            name="violin",
            required_channels=("x", "y"),
            optional_channels=("color", "alpha"),
        )


@dataclass(frozen=True)
class GeomStepLine(Geom):
    where: str = "pre"

    def __init__(self, where: str = "pre") -> None:
        object.__setattr__(self, "where", where)
        super().__init__(
            name="step_line",
            required_channels=("x", "y"),
            optional_channels=("color", "style", "width", "alpha"),
        )
