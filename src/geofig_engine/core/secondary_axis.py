"""
Secondary axis declarations for cartesian frames.

A general secondary-axis system lets a linked cartesian child display extra
scales along its upper/right frame edges (WP-B) and plot a second data series
against them (WP-D). Secondary axes are declared as structured entries in a
child :class:`~geofig_engine.core.spec.FigureSpec` ``settings`` dict::

    settings = {
        "xlim": (0, 100), "ylim": (0, 100),
        "tick_step": 20, "label_policy": "upright",
        "secondary_x": {
            "range": [100, 0],        # secondary data scale
            "tick_step": 20,          # default = primary tick_step
            "label_policy": "upright",# default = primary label_policy
            "position": "top",        # default "top"; alt "bottom"
            "label": "Anions (%)",    # optional axis title
        },
        "secondary_y": {"range": [100, 0], "position": "right", ...},
    }

A secondary value maps **linearly** onto the primary (local-frame) coordinate
determined by the child's ``xlim``/``ylim``. A ``range`` of ``[100, 0]`` on a
``[0, 100]`` primary therefore yields the reversed/complement scale the piper
diamond needs; other ranges generalize beyond bare reversal.

This module is intentionally matplotlib-free so the mapping + tick math can be
unit-tested directly and reused by both the frame renderer (WP-B) and the
coord/data path (WP-D).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping

VALID_LABEL_POLICIES = ("upright", "parallel")

# Edges a secondary axis may be drawn on, per orientation.
_POSITION_BY_ORIENTATION = {
    "x": ("top", "bottom"),
    "y": ("right", "left"),
}
_DEFAULT_POSITION = {"x": "top", "y": "right"}

_REL_TOL = 1e-9


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


def _tick_labels(value, label: str = "tick_labels") -> dict[float, str]:
    """Validate and normalize a ``{position: label}`` tick-label declaration.

    Keys may be real numbers or numeric strings (JSON round-trips coerce dict
    keys to strings); they are normalized to ``float`` positions. Values must
    be non-empty strings. Returns a ``{float: str}`` dict.
    """
    out: dict[float, str] = {}
    if not isinstance(value, (dict, Mapping)):
        raise ValueError(f"{label} must be a dict of {{position: label}}, got {value!r}")
    for k, v in value.items():
        if isinstance(k, bool) or not isinstance(k, (int, float, str)):
            raise ValueError(f"{label} key {k!r} must be a numeric position")
        if isinstance(k, str):
            try:
                pos = float(k)
            except ValueError as exc:
                raise ValueError(f"{label} key {k!r} must be a numeric position") from exc
        else:
            pos = float(k)
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"{label} values must be non-empty strings, got {v!r}")
        out[pos] = v
    return out


def linear_mapping(
    primary: tuple[float, float],
    secondary: tuple[float, float],
) -> tuple[Callable[[float], float], Callable[[float], float]]:
    """Return ``(fwd, inv)`` linear maps between *primary* and *secondary* ranges.

    ``fwd(v)`` maps a primary value to secondary; ``inv(v)`` maps a secondary
    value back to primary (the local-frame coordinate). Both require invertible
    (non-degenerate) ranges; each is the affine inverse of the other.
    """
    p0, p1 = _pair(primary, "primary range")
    s0, s1 = _pair(secondary, "secondary range")
    if _invertible(p0, p1):
        raise ValueError(f"primary range must not be degenerate, got {primary!r}")
    if _invertible(s0, s1):
        raise ValueError(f"secondary range must not be degenerate, got {secondary!r}")

    def fwd(p: float) -> float:
        p = _scalar(p, "primary value")
        t = (p - p0) / (p1 - p0)
        return s0 + t * (s1 - s0)

    def inv(s: float) -> float:
        s = _scalar(s, "secondary value")
        t = (s - s0) / (s1 - s0)
        return p0 + t * (p1 - p0)

    return fwd, inv


def _invertible(a: float, b: float) -> bool:
    return abs(b - a) <= _REL_TOL


@dataclass(frozen=True)
class SecondaryAxis:
    """A validated secondary axis declaration for a cartesian child.

    Attributes:
        orientation: ``"x"`` (drawn on the top/bottom edge) or ``"y"``
            (drawn on the right/left edge).
        range: Secondary data scale ``(min, max)`` as declared in settings.
        tick_step: Spacing between tick labels on the secondary scale.
        label_policy: ``"upright"`` or ``"parallel"`` base text rotation policy,
            inherited from the primary axis unless overridden.
        axis_label_policy: ``"upright"`` or ``"parallel"``, or ``None`` to
            inherit the secondary's ``label_policy`` (independent axis-label
            rotation).
        tick_label_policy: ``"upright"`` or ``"parallel"``, or ``None`` to
            inherit the secondary's ``label_policy`` (independent tick-label
            rotation).
        position: Frame edge to draw on (see :data:`_POSITION_BY_ORIENTATION`).
        label: Optional axis title (usually empty).
        primary_range: The local-frame range this axis maps onto (from the
            child's ``xlim``/``ylim``).
    """

    orientation: str
    range: tuple[float, float]
    tick_step: float
    label_policy: str
    position: str
    label: str
    primary_range: tuple[float, float]
    axis_label_policy: str | None = None
    tick_label_policy: str | None = None
    abs_ticks: bool = False
    tick_labels: dict[float, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "range", _pair(self.range, "secondary range"))
        object.__setattr__(self, "primary_range", _pair(self.primary_range, "primary range"))
        object.__setattr__(self, "tick_step", _scalar(self.tick_step, "tick_step"))
        if self.tick_step <= 0:
            raise ValueError(f"secondary {self.orientation!r} tick_step must be positive, "
                             f"got {self.tick_step!r}")
        if _invertible(self.range[0], self.range[1]):
            raise ValueError(f"secondary {self.orientation!r} range must not be degenerate, "
                             f"got {self.range!r}")
        if self.label_policy not in VALID_LABEL_POLICIES:
            raise ValueError(
                f"secondary {self.orientation!r} label_policy must be one of "
                f"{VALID_LABEL_POLICIES}, got {self.label_policy!r}"
            )
        if self.axis_label_policy is not None and self.axis_label_policy not in VALID_LABEL_POLICIES:
            raise ValueError(
                f"secondary {self.orientation!r} axis_label_policy must be one of "
                f"{VALID_LABEL_POLICIES}, got {self.axis_label_policy!r}"
            )
        if self.tick_label_policy is not None and self.tick_label_policy not in VALID_LABEL_POLICIES:
            raise ValueError(
                f"secondary {self.orientation!r} tick_label_policy must be one of "
                f"{VALID_LABEL_POLICIES}, got {self.tick_label_policy!r}"
            )
        if not isinstance(self.abs_ticks, bool):
            raise ValueError(
                f"secondary {self.orientation!r} abs_ticks must be a bool, "
                f"got {self.abs_ticks!r}"
            )
        object.__setattr__(
            self, "tick_labels", _tick_labels(self.tick_labels)
        )
        allowed = _POSITION_BY_ORIENTATION[self.orientation]
        if self.position not in allowed:
            raise ValueError(
                f"secondary {self.orientation!r} position must be one of {allowed}, "
                f"got {self.position!r}"
            )

    @property
    def fwd(self) -> Callable[[float], float]:
        """Map a primary (local) value to this axis's secondary units."""
        return linear_mapping(self.primary_range, self.range)[0]

    @property
    def inv(self) -> Callable[[float], float]:
        """Map a secondary value to the primary (local-frame) coordinate."""
        return linear_mapping(self.primary_range, self.range)[1]

    def tick_values(self) -> list[float]:
        """Secondary tick positions (secondary units).

        When ``tick_labels`` is set, returns all label positions (frame edges
        included); otherwise returns interior numeric ticks at ``tick_step``
        (endpoints excluded, like primary ticks).
        """
        if self.tick_labels:
            return sorted(self.tick_labels)
        s0, s1 = self.range
        lo, hi = min(s0, s1), max(s0, s1)
        step = self.tick_step
        if step <= 0 or _invertible(lo, hi):
            return []
        values = []
        v = lo
        while v <= hi + 0.5 * step:
            if abs(v - s0) <= _REL_TOL or abs(v - s1) <= _REL_TOL:
                v += step
                continue
            values.append(v)
            v += step
        return values

    def tick_coordinates(self) -> list[tuple[float, float]]:
        """Return ``[(tick_value, local_coord), ...]``.

        Named ticks include frame-edge positions; numeric ticks are interior.
        """
        out = []
        for sv in self.tick_values():
            out.append((sv, self.inv(sv)))
        return out

    def axis_label_policy_eff(self) -> str:
        """Effective rotation policy for this secondary's axis title."""
        return self.axis_label_policy if self.axis_label_policy is not None else self.label_policy

    def tick_label_policy_eff(self) -> str:
        """Effective rotation policy for this secondary's tick labels."""
        return self.tick_label_policy if self.tick_label_policy is not None else self.label_policy


def parse_secondary_settings(
    settings: Mapping | None,
    *,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
    defaults: Mapping | None = None,
) -> dict[str, SecondaryAxis]:
    """Read ``secondary_x``/``secondary_y`` declarations from a child's settings.

    Args:
        settings: The child spec's ``settings`` dict (may be None).
        xlim: Local-frame range the secondary x maps onto (the child's x axis).
        ylim: Local-frame range the secondary y maps onto (the child's y axis).
            Either may be None in which case it is read from ``settings``
            (``"xlim"``/``"ylim"``) or defaults to ``(0, 1)``.
        defaults: Optional fallback dict from which ``tick_step``, ``label_policy``,
            ``axis_label_policy``, ``tick_label_policy``, ``abs_ticks`` and
            ``tick_labels`` are inherited when a secondary declaration omits them
            (the child's frame ``grid_step``/``tick_step``/``label_policy``,
            those axes' effective policies, and primary tick-label formatting).

    Returns a dict keyed by orientation (``"x"``/``"y"``) of validated
    :class:`SecondaryAxis`. Absent declarations are skipped; malformed ones
    raise :class:`ValueError`.
    """
    cfg = dict(settings or {})
    defaults = defaults or {}

    primary_by_orientation = {
        "x": _pair(xlim if xlim is not None else cfg.get("xlim", (0.0, 1.0)), "xlim"),
        "y": _pair(ylim if ylim is not None else cfg.get("ylim", (0.0, 1.0)), "ylim"),
    }

    default_step = cfg.get("tick_step", defaults.get("tick_step",
                                                     defaults.get("grid_step", 0.2)))
    default_policy = cfg.get("label_policy", defaults.get("label_policy", "upright"))

    result: dict[str, SecondaryAxis] = {}
    for orientation in ("x", "y"):
        raw = cfg.get(f"secondary_{orientation}")
        if raw is None:
            continue
        if not isinstance(raw, Mapping):
            raise ValueError(
                f"settings['secondary_{orientation}'] must be a mapping, got {raw!r}"
            )
        spec_range = raw.get("range")
        if spec_range is None:
            raise ValueError(
                f"settings['secondary_{orientation}'] requires a 'range', got {raw!r}"
            )
        result[orientation] = SecondaryAxis(
            orientation=orientation,
            range=_pair(spec_range, f"secondary_{orientation} range"),
            tick_step=raw.get("tick_step", default_step),
            label_policy=raw.get("label_policy", default_policy),
            axis_label_policy=raw.get(
                "axis_label_policy", defaults.get("axis_label_policy")
            ),
            tick_label_policy=raw.get(
                "tick_label_policy", defaults.get("tick_label_policy")
            ),
            position=raw.get("position", _DEFAULT_POSITION[orientation]),
            label=raw.get("label", ""),
            primary_range=primary_by_orientation[orientation],
            abs_ticks=raw.get(
                "abs_ticks", defaults.get("abs_ticks", False)
            ),
            tick_labels=raw.get(
                "tick_labels", defaults.get("tick_labels", {})
            ),
        )
    return result
