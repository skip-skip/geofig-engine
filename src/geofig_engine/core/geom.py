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
    SHAPE = "shape"
    SIZE = "size"
    STYLE = "style"
    ALPHA = "alpha"
    WIDTH = "width"
    LABEL = "label"
    FUNC = "func"
    YMIN = "ymin"
    YMAX = "ymax"
    XMIN = "xmin"
    XMAX = "xmax"
    ANGLE = "angle"
    BBOX = "bbox"
    IMAGE = "image"


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
    position: str = "identity"

    def __init__(self, position: str = "identity") -> None:
        if position not in ("identity", "stack", "fill"):
            raise ValueError(f"position must be 'identity', 'stack', or 'fill', got {position!r}")
        object.__setattr__(self, "position", position)
        super().__init__(
            name="bar",
            required_channels=("x", "y"),
            optional_channels=("color", "alpha", "width", "label"),
        )


@dataclass(frozen=True)
class GeomArea(Geom):
    def __init__(self) -> None:
        super().__init__(
            name="area",
            required_channels=("x", "y"),
            optional_channels=("color", "alpha"),
        )


_VALID_EDGE_STYLES = {"solid", "dashed", "dashdot", "dotted", "-", "--", "-.", ":"}


def _normalize_edge_params(
    edgecolor: str,
    edgealpha: float | None,
    edgewidth: float,
    edgestyle: str,
) -> tuple[str, float | None, float, str]:
    """Validate and coerce polygon/boundary edge parameters (shared machinery)."""
    if not isinstance(edgecolor, str) or not edgecolor:
        raise ValueError(f"edgecolor must be a non-empty string, got {edgecolor!r}")
    if edgealpha is not None and (
        isinstance(edgealpha, bool) or not isinstance(edgealpha, (int, float))
    ):
        raise ValueError(f"edgealpha must be a real number or None, got {edgealpha!r}")
    if (
        isinstance(edgewidth, bool)
        or not isinstance(edgewidth, (int, float))
        or edgewidth <= 0
    ):
        raise ValueError(f"edgewidth must be a positive real number, got {edgewidth!r}")
    if edgestyle not in _VALID_EDGE_STYLES:
        raise ValueError(
            f"edgestyle must be one of {sorted(_VALID_EDGE_STYLES)}, got {edgestyle!r}"
        )
    return (
        edgecolor,
        float(edgealpha) if edgealpha is not None else None,
        float(edgewidth),
        edgestyle,
    )


@dataclass(frozen=True)
class GeomPolygon(Geom):
    edgecolor: str = "black"
    edgealpha: float | None = None
    edgewidth: float = 0.5
    edgestyle: str = "-"

    def __init__(
        self,
        edgecolor: str = "black",
        edgealpha: float | None = None,
        edgewidth: float = 0.5,
        edgestyle: str = "-",
    ) -> None:
        edgecolor, edgealpha, edgewidth, edgestyle = _normalize_edge_params(
            edgecolor, edgealpha, edgewidth, edgestyle
        )
        object.__setattr__(self, "edgecolor", edgecolor)
        object.__setattr__(self, "edgealpha", edgealpha)
        object.__setattr__(self, "edgewidth", edgewidth)
        object.__setattr__(self, "edgestyle", edgestyle)
        super().__init__(
            name="polygon",
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
            optional_channels=("color", "size", "alpha", "angle", "bbox"),
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


@dataclass(frozen=True)
class GeomAbline(Geom):
    slope: float | None = None
    intercept: float = 0.0
    x1: float | None = None
    y1: float | None = None
    x2: float | None = None
    y2: float | None = None

    def __init__(
        self,
        slope: float | None = None,
        intercept: float = 0.0,
        x1: float | None = None,
        y1: float | None = None,
        x2: float | None = None,
        y2: float | None = None,
    ) -> None:
        slope_provided = slope is not None
        two_point_provided = all(v is not None for v in (x1, y1, x2, y2))
        if slope_provided and two_point_provided:
            raise ValueError("GeomAbline: provide slope+intercept OR two-point, not both")
        if not slope_provided and not two_point_provided:
            raise ValueError("GeomAbline: provide either slope+intercept or x1/y1/x2/y2")
        object.__setattr__(self, "slope", slope)
        object.__setattr__(self, "intercept", intercept)
        object.__setattr__(self, "x1", x1)
        object.__setattr__(self, "y1", y1)
        object.__setattr__(self, "x2", x2)
        object.__setattr__(self, "y2", y2)
        super().__init__(
            name="abline",
            required_channels=(),
            optional_channels=("color", "style", "width", "alpha"),
        )


@dataclass(frozen=True)
class GeomHSpan(Geom):
    def __init__(self) -> None:
        super().__init__(
            name="hspan",
            required_channels=("ymin", "ymax"),
            optional_channels=("color", "alpha"),
        )


@dataclass(frozen=True)
class GeomVSpan(Geom):
    def __init__(self) -> None:
        super().__init__(
            name="vspan",
            required_channels=("xmin", "xmax"),
            optional_channels=("color", "alpha"),
        )


@dataclass(frozen=True)
class GeomRect(Geom):
    def __init__(self) -> None:
        super().__init__(
            name="rect",
            required_channels=("xmin", "xmax", "ymin", "ymax"),
            optional_channels=("color", "alpha"),
        )


# ---------------------------------------------------------------------------
# Geo geoms (Phase 15, wp8)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GeomSitePoint(Geom):
    """Site point on a geo figure: lon/lat ``x``/``y`` plus color/shape/size.

    ``group`` is the legend label used when no explicit ``label`` channel is
    mapped (grouped site-map legends build on it in later work packages).
    """

    group: str = "Sites"

    def __init__(self, group: str = "Sites") -> None:
        if not isinstance(group, str) or not group.strip():
            raise ValueError(f"group must be a non-empty string, got {group!r}")
        object.__setattr__(self, "group", group)
        super().__init__(
            name="site_point",
            required_channels=("x", "y"),
            optional_channels=("color", "shape", "size", "label", "alpha"),
        )


@dataclass(frozen=True)
class GeomBoundary(Geom):
    """Closed polygon outline from a ``x``/``y`` path (edge machinery shared
    with :class:`GeomPolygon`)."""

    edgecolor: str = "black"
    edgealpha: float | None = None
    edgewidth: float = 0.5
    edgestyle: str = "-"

    def __init__(
        self,
        edgecolor: str = "black",
        edgealpha: float | None = None,
        edgewidth: float = 0.5,
        edgestyle: str = "-",
    ) -> None:
        edgecolor, edgealpha, edgewidth, edgestyle = _normalize_edge_params(
            edgecolor, edgealpha, edgewidth, edgestyle
        )
        object.__setattr__(self, "edgecolor", edgecolor)
        object.__setattr__(self, "edgealpha", edgealpha)
        object.__setattr__(self, "edgewidth", edgewidth)
        object.__setattr__(self, "edgestyle", edgestyle)
        super().__init__(
            name="boundary",
            required_channels=("x", "y"),
            optional_channels=("color", "alpha"),
        )


@dataclass(frozen=True)
class GeomContour(Geom):
    """Level contours from the DEM stat (edge machinery shared with
    :class:`GeomPolygon`/:class:`GeomBoundary`).

    M1 is constant-style: the per-level ``level`` channel is intentionally
    **not** added — color/width/alpha are geometry params applied to the
    whole contour-line set.
    """

    edgecolor: str = "white"
    edgealpha: float | None = None
    edgewidth: float = 0.5
    edgestyle: str = "-"

    def __init__(
        self,
        edgecolor: str = "white",
        edgealpha: float | None = None,
        edgewidth: float = 0.5,
        edgestyle: str = "-",
    ) -> None:
        edgecolor, edgealpha, edgewidth, edgestyle = _normalize_edge_params(
            edgecolor, edgealpha, edgewidth, edgestyle
        )
        object.__setattr__(self, "edgecolor", edgecolor)
        object.__setattr__(self, "edgealpha", edgealpha)
        object.__setattr__(self, "edgewidth", edgewidth)
        object.__setattr__(self, "edgestyle", edgestyle)
        super().__init__(
            name="contour",
            required_channels=("x", "y"),
            optional_channels=("color", "alpha"),
        )


@dataclass(frozen=True)
class GeomStreams(Geom):
    """Surface-water stream polylines from the ``StatStreams`` source.

    One constant style is applied to the whole NaN-separated multipart line
    set (old-geomapper ``add_streams`` look); there is no per-feature channel
    and no legend entry. Rendering reuses the open-path boundary handler.
    """

    edgecolor: str = "blue"
    edgealpha: float | None = 0.7
    edgewidth: float = 0.7
    edgestyle: str = "-"

    def __init__(
        self,
        edgecolor: str = "blue",
        edgealpha: float | None = 0.7,
        edgewidth: float = 0.7,
        edgestyle: str = "-",
    ) -> None:
        edgecolor, edgealpha, edgewidth, edgestyle = _normalize_edge_params(
            edgecolor, edgealpha, edgewidth, edgestyle
        )
        object.__setattr__(self, "edgecolor", edgecolor)
        object.__setattr__(self, "edgealpha", edgealpha)
        object.__setattr__(self, "edgewidth", edgewidth)
        object.__setattr__(self, "edgestyle", edgestyle)
        super().__init__(
            name="streams",
            required_channels=("x", "y"),
            optional_channels=("color", "alpha"),
        )


@dataclass(frozen=True)
class GeomLabel(Geom):
    """Geo label text at ``x``/``y`` with a ``label`` channel; the geometry
    carries default ``size``/``rotation`` params (unlike the per-point
    channels of :class:`GeomText`)."""

    size: float = 10.0
    rotation: float = 0.0

    def __init__(self, size: float = 10.0, rotation: float = 0.0) -> None:
        if isinstance(size, bool) or not isinstance(size, (int, float)) or size <= 0:
            raise ValueError(f"size must be a positive real number, got {size!r}")
        if isinstance(rotation, bool) or not isinstance(rotation, (int, float)):
            raise ValueError(f"rotation must be a real number, got {rotation!r}")
        object.__setattr__(self, "size", float(size))
        object.__setattr__(self, "rotation", float(rotation))
        super().__init__(
            name="geo_label",
            required_channels=("x", "y", "label"),
            optional_channels=("color", "alpha"),
        )


@dataclass(frozen=True)
class GeomImageInset(Geom):
    """``OffsetImage``-style inset anchored at ``x``/``y``; the ``image``
    channel resolves to a 2-D/3-D array (per row or constant) and ``zoom``
    controls the display scale."""

    zoom: float = 0.1

    def __init__(self, zoom: float = 0.1) -> None:
        if isinstance(zoom, bool) or not isinstance(zoom, (int, float)) or zoom <= 0:
            raise ValueError(f"zoom must be a positive real number, got {zoom!r}")
        object.__setattr__(self, "zoom", float(zoom))
        super().__init__(
            name="image_inset",
            required_channels=("x", "y", "image"),
            optional_channels=(),
        )
