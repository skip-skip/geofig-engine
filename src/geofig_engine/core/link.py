"""
AxisLink: declarative secondary axes sharing one canvas (Phase 14.5).

A figure has one main axis plus zero or more named links. World space is
defined as the main axis's post-transform data space; each link places its
own local ``[0, 1]²`` space inside that world via a :class:`LinkTransform`.

Composition convention (pinned by unit tests in ``tests/test_links.py``):

    ``matrix()`` returns the homogeneous product ``M = T · S · R``, so a
    point experiences

        1. rotate   -- about the link's local origin
        2. scale    -- along world x/y axes (after rotation)
        3. translate-- into world position

    Fields are declared outermost-first (translate is the world placement,
    rotate/scale shape local content); applying them to points runs in the
    reverse order. Scale acting after rotation is what makes the Piper
    diamond's "rotate 45°, then squash y" directly expressible as
    ``LinkTransform(translate=..., rotate=45.0, scale=(1.0, k))``.

This module is matplotlib-free by design; renderers bridge ``matrix()``
into an ``Affine2D.from_values(...)`` themselves.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from geofig_engine.core.coord import Coord


def _numeric_pair(value, label: str) -> tuple[float, float]:
    """Validate and coerce a length-2 sequence of real numbers (bools excluded)."""
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise TypeError(f"{label} must be a pair of numbers, got {value!r}")
    for v in value:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise TypeError(f"{label} must contain real numbers, got {value!r}")
    return (float(value[0]), float(value[1]))


def _real_number(value, label: str) -> float:
    """Validate and coerce a real number (bools excluded)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number, got {value!r}")
    return float(value)


@dataclass(frozen=True)
class LinkTransform:
    """
    Affine placement of a linked axis inside world space.

    Attributes:
        translate: World-space offset applied last, declared in world units.
        rotate: Rotation in degrees about the link's local origin.
        scale: Stretch/squash along world x/y axes, applied after rotation.
    """

    translate: tuple[float, float] = (0.0, 0.0)
    rotate: float = 0.0
    scale: tuple[float, float] = (1.0, 1.0)

    def __post_init__(self) -> None:
        object.__setattr__(self, "translate", _numeric_pair(self.translate, "translate"))
        object.__setattr__(self, "scale", _numeric_pair(self.scale, "scale"))
        object.__setattr__(self, "rotate", _real_number(self.rotate, "rotate"))

    def matrix(self) -> np.ndarray:
        """
        Return the 3x3 homogeneous matrix ``M = T · S · R``.

        Right-multiplication order means points experience rotate, then
        scale, then translate.
        """
        theta = math.radians(self.rotate)
        c, s = math.cos(theta), math.sin(theta)
        tx, ty = self.translate
        sx, sy = self.scale

        t_mat = np.array([[1.0, 0.0, tx], [0.0, 1.0, ty], [0.0, 0.0, 1.0]])
        s_mat = np.array([[sx, 0.0, 0.0], [0.0, sy, 0.0], [0.0, 0.0, 1.0]])
        r_mat = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        return t_mat @ s_mat @ r_mat

    def transform_point(self, xy) -> tuple[float, float]:
        """Map a single local-space point into world space."""
        x = _real_number(xy[0], "point x")
        y = _real_number(xy[1], "point y")
        vec = self.matrix() @ np.array([x, y, 1.0])
        return (float(vec[0]), float(vec[1]))

    def to_dict(self) -> dict:
        """JSON-compatible representation of this transform."""
        return {
            "translate": list(self.translate),
            "rotate": self.rotate,
            "scale": list(self.scale),
        }

    @classmethod
    def from_dict(cls, data: dict) -> LinkTransform:
        """Reconstruct a LinkTransform from its dict representation."""
        return cls(
            translate=tuple(data.get("translate", (0.0, 0.0))),
            rotate=data.get("rotate", 0.0),
            scale=tuple(data.get("scale", (1.0, 1.0))),
        )


@dataclass(frozen=True)
class AxisLink:
    """
    A named secondary axis placed in world space.

    Attributes:
        name: Unique identifier; LayerSpec.subplot routes layers here.
        coord: Projection for this axis's local space (Coord instance).
        transform: Placement of the local [0, 1]² space in world space.
        frame: Optional styling hints consumed by renderer frame providers.
    """

    name: str
    coord: Coord
    transform: LinkTransform = field(default_factory=LinkTransform)
    frame: dict | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError(f"name must be a non-empty string, got {self.name!r}")
        if not isinstance(self.coord, Coord):
            raise TypeError(
                f"coord must be a Coord instance, got {type(self.coord).__name__}"
            )
        if not isinstance(self.transform, LinkTransform):
            raise TypeError(
                f"transform must be a LinkTransform, got {type(self.transform).__name__}"
            )
        if self.frame is not None and not isinstance(self.frame, dict):
            raise TypeError(f"frame must be a dict or None, got {self.frame!r}")
