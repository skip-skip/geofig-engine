"""
AxisFormat: declarative axis-formatting spec for the unified frame pipeline.

A single, shared formatting model consumed by the **unified frame-drawing
pipeline** (Phase 14.54). Both the top-level path and the linked-axes
child-frame path use the exact same formatting specification, declared with
flat top-level settings keys::

    settings = {
        "title": "My plot",
        "xlim": (0, 100),
        "ylim": (0, 100),
        "grid": True,
        "grid_step": 20,
        "tick_step": 10,
        "axis_arrows": True,
        "x_reversed": False,
        "y_reversed": False,
        "label_policy": "upright",
        "tick_format": ":g",
        # per-coordinate extension (polar toggles, etc.):
        "hide_spine": True,
        "polar_tick_labels": True,
    }

The model is a **common core + per-coordinate ``options`` extension**: each
coordinate type (cartesian, ternary, polar) can carry unique declarations while
sharing the common axis fields. Alongside the common fields it carries
**appearance-preserving style knobs** whose defaults reproduce the current
native/custom matplotlib look, so switching top-level cartesian/ternary/polar
onto the unified custom frame does not visibly regress existing templates.

Following the :class:`~geofig_engine.core.secondary_axis.SecondaryAxis`
precedent, this module is intentionally matplotlib-free so it can be unit-tested
directly and reused by the frame renderer and both the top-level and child
paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

VALID_LABEL_POLICIES = ("upright", "parallel")

# Flat (legacy) keys mapped into AxisFormat.options, per coordinate.
_LEGACY_POLAR_OPTIONS = (
    "hide_spine",
    "hide_angular_ticks",
    "hide_angular_labels",
    "hide_radial_labels",
    "hide_radial_ticks",
    "polar_tick_labels",
)


def _pair(value, label: str) -> tuple[float, float]:
    """Validate and coerce a length-2 sequence of real numbers (bools excluded)."""
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError(f"{label} must be a pair of numbers, got {value!r}")
    out = []
    for v in value:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"{label} must contain real numbers, got {value!r}")
        out.append(float(v))
    return (out[0], out[1])


def _scalar(value, label: str) -> float:
    """Validate and coerce a real number (bools excluded)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a real number, got {value!r}")
    return float(value)


def _positive(value, label: str) -> float:
    """Validate and coerce a strictly positive real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a real number, got {value!r}")
    value = float(value)
    if value <= 0:
        raise ValueError(f"{label} must be positive, got {value!r}")
    return value


def _bool_value(value, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a bool, got {value!r}")
    return value


def _policy_value(value, label: str = "label_policy") -> str:
    if value not in VALID_LABEL_POLICIES:
        raise ValueError(
            f"{label} must be one of {VALID_LABEL_POLICIES}, got {value!r}"
        )
    return value


@dataclass(frozen=True)
class AxisFormat:
    """Validated, matplotlib-free axis-formatting declaration.

    Common fields are consumed by both the top-level and child frame paths:
    title/labels, data ``limits`` ``(xlim, ylim)``, grid/ticks, label and scale
    policy, and a ``tick_format`` format-spec applied to numeric tick labels.
    ``options`` is a per-coordinate extension dict (e.g. polar toggles).

    Appearance-preserving style knobs (``tick_fontsize``, ``label_fontsize``,
    ``title_fontsize``, ``grid_style``, ``frame_linewidth``, ``label_offset``)
    default to the current native/custom matplotlib look.
    """

    # Common fields (both paths)
    title: str = ""
    xlabel: str | None = None
    ylabel: str | None = None
    limits: tuple[tuple[float, float], tuple[float, float]] | None = None
    grid: bool | None = None
    grid_step: float | None = None
    tick_step: float | None = None
    axis_arrows: bool | None = None
    x_reversed: bool = False
    y_reversed: bool = False
    label_policy: str = "upright"
    xscale: str | None = None
    yscale: str | None = None
    time_format: str | None = None
    tick_format: str = ":g"

    # Appearance-preserving style knobs (defaults match current output)
    tick_fontsize: float = 5
    label_fontsize: float = 7
    title_fontsize: float = 7
    grid_style: dict[str, Any] = field(
        default_factory=lambda: {
            "color": "gray",
            "linewidth": 0.3,
            "linestyle": ":",
        }
    )
    frame_linewidth: float = 1.0
    label_offset: float | None = None
    axis_arrow_offset: float | None = None

    # Per-coordinate extension
    options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", str(self.title))
        object.__setattr__(self, "xlabel", None if self.xlabel is None else str(self.xlabel))
        object.__setattr__(self, "ylabel", None if self.ylabel is None else str(self.ylabel))

        if self.limits is not None:
            if not isinstance(self.limits, (tuple, list)) or len(self.limits) != 2:
                raise ValueError(f"limits must be a pair of (xlim, ylim), got {self.limits!r}")
            object.__setattr__(
                self,
                "limits",
                (_pair(self.limits[0], "xlim"), _pair(self.limits[1], "ylim")),
            )

        if self.grid is not None:
            object.__setattr__(self, "grid", _bool_value(self.grid, "grid"))
        if self.grid_step is not None:
            object.__setattr__(self, "grid_step", _positive(self.grid_step, "grid_step"))
        if self.tick_step is not None:
            object.__setattr__(self, "tick_step", _positive(self.tick_step, "tick_step"))
        if self.axis_arrows is not None:
            object.__setattr__(self, "axis_arrows", _bool_value(self.axis_arrows, "axis_arrows"))
        object.__setattr__(self, "x_reversed", _bool_value(self.x_reversed, "x_reversed"))
        object.__setattr__(self, "y_reversed", _bool_value(self.y_reversed, "y_reversed"))

        object.__setattr__(self, "label_policy", _policy_value(self.label_policy))
        for attr in ("xscale", "yscale", "time_format"):
            value = getattr(self, attr)
            if value is not None:
                object.__setattr__(self, attr, str(value))

        object.__setattr__(self, "tick_format", self._validate_tick_format(self.tick_format))

        for attr in ("tick_fontsize", "label_fontsize", "title_fontsize", "frame_linewidth"):
            object.__setattr__(self, attr, _scalar(getattr(self, attr), attr))
        if self.tick_fontsize <= 0:
            raise ValueError(f"tick_fontsize must be positive, got {self.tick_fontsize!r}")
        if self.label_fontsize <= 0:
            raise ValueError(f"label_fontsize must be positive, got {self.label_fontsize!r}")
        if self.title_fontsize <= 0:
            raise ValueError(f"title_fontsize must be positive, got {self.title_fontsize!r}")
        if self.frame_linewidth < 0:
            raise ValueError(
                f"frame_linewidth must be non-negative, got {self.frame_linewidth!r}"
            )
        if not isinstance(self.grid_style, dict):
            raise ValueError(f"grid_style must be a dict, got {self.grid_style!r}")
        if self.label_offset is not None:
            object.__setattr__(self, "label_offset", _scalar(self.label_offset, "label_offset"))
        if self.axis_arrow_offset is not None:
            object.__setattr__(
                self, "axis_arrow_offset", _scalar(self.axis_arrow_offset, "axis_arrow_offset")
            )

        if not isinstance(self.options, dict):
            raise ValueError(f"options must be a dict, got {self.options!r}")
        object.__setattr__(self, "options", dict(self.options))

    @staticmethod
    def _validate_tick_format(value) -> str:
        if value is None or not isinstance(value, str):
            raise ValueError(f"tick_format must be a string, got {value!r}")
        return value

    # -- convenience accessors -------------------------------------------------
    @property
    def xlim(self) -> tuple[float, float] | None:
        return None if self.limits is None else self.limits[0]

    @property
    def ylim(self) -> tuple[float, float] | None:
        return None if self.limits is None else self.limits[1]

    @property
    def coord_grid_step(self) -> float:
        """Effective grid step (never None) for callers that require a default."""
        return self.grid_step if self.grid_step is not None else 0.2

    @property
    def coord_tick_step(self) -> float:
        """Effective tick step, defaulting to the grid step, then 0.2."""
        if self.tick_step is not None:
            return self.tick_step
        if self.grid_step is not None:
            return self.grid_step
        return 0.2

    @property
    def effective_polar_step(self) -> float:
        """Polar radial/grid step (matches grid_step default used by native polar)."""
        return self.grid_step if self.grid_step is not None else 0.2

    def option(self, key: str, default: Any = None) -> Any:
        """Per-coordinate extension lookup (e.g. ``axis.option("hide_spine")``)."""
        return self.options.get(key, default)

    def show_arrows(self) -> bool:
        """Effective axis-direction-arrow flag (``False`` when unset or None)."""
        return bool(self.axis_arrows)


def parse_axis_settings(settings: Mapping | None, coord=None) -> AxisFormat:
    """Read axis-formatting into an :class:`AxisFormat`, validated.

    Reads flat top-level keys from ``settings`` (``title``, ``xlabel``,
    ``ylabel``, ``xlim``/``ylim``, ``grid``, ``grid_step``, ``tick_step``,
    ``axis_arrows``, ``x_reversed``/``y_reversed``, ``label_policy``, ``xscale``/
    ``yscale``, ``time_format``,
    ``tick_format``, polar toggles, ...) and maps them into the equivalent
    :class:`AxisFormat` fields / ``options``.

    ``coord`` is currently informational context for any future coord-specific
    defaults/validation; the common parse stays coord-agnostic.

    Args:
        settings: A spec's ``settings`` dict (may be None).
        coord: Optional :class:`~geofig_engine.core.coord.Coord` for context.

    Returns:
        A validated :class:`AxisFormat`.

    Raises:
        ValueError: For malformed declarations (bad limits/tick_step/policies).
    """
    cfg = dict(settings or {})

    def _pick(*names, default=None):
        for name in names:
            if name in cfg:
                return cfg[name]
        return default

    limits = None
    if "xlim" in cfg and "ylim" in cfg:
        limits = (
            _pair(cfg["xlim"], "xlim"),
            _pair(cfg["ylim"], "ylim"),
        )

    options = {}
    for key in _LEGACY_POLAR_OPTIONS:
        if key in cfg:
            options[key] = cfg[key]

    return AxisFormat(
        title=_pick("title", "figname", default="") or "",
        xlabel=_pick("xlabel"),
        ylabel=_pick("ylabel"),
        limits=limits,
        grid=_pick("grid"),
        grid_step=_pick("grid_step"),
        tick_step=_pick("tick_step"),
        axis_arrows=_pick("axis_arrows"),
        x_reversed=_pick("x_reversed", default=False),
        y_reversed=_pick("y_reversed", default=False),
        label_policy=_pick("label_policy", default="upright"),
        xscale=_pick("xscale"),
        yscale=_pick("yscale"),
        time_format=_pick("time_format"),
        tick_format=_pick("tick_format", default=":g"),
        axis_arrow_offset=_pick("axis_arrow_offset"),
        options=options,
    )
