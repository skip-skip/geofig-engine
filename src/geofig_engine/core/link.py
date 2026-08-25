"""
LinkTransform: affine placement of a linked axis inside world space.

Each child FigureSpec carries a LinkTransform that maps its local
coordinate space into the parent's world space.

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

    def transform_points(self, pts) -> np.ndarray:
        """Map an (n, 2)-like sequence of local points into world space."""
        arr = np.asarray(pts, dtype=float)
        if arr.ndim != 2 or arr.shape[1] != 2:
            raise ValueError(f"pts must have shape (n, 2), got {arr.shape}")
        ones = np.ones((arr.shape[0], 1))
        return (self.matrix() @ np.hstack([arr, ones]).T).T[:, :2]

    def transform_direction(self, vec) -> tuple[float, float]:
        """Apply only the linear part (rotate+scale) to a direction vector."""
        vx = _real_number(vec[0], "vec x")
        vy = _real_number(vec[1], "vec y")
        lin = self.matrix()[:2, :2]
        wx, wy = lin @ np.array([vx, vy])
        return (float(wx), float(wy))

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


def label_rotation(local_vec, matrix: np.ndarray, policy: str = "upright") -> float:
    """
    Text rotation (degrees) for a label attached to a transformed axis.

    Labels never inherit transforms; the renderer places them world-side at
    ``transform_point()`` anchors. This helper decides their rotation:

    - ``"upright"`` (default): always 0 — text stays horizontal regardless
      of the transform stack.
    - ``"parallel"``: rotation of the transformed tangent direction, so the
      label runs along its edge *after* deformation. Uses only the linear
      part of *matrix*, making it correct under non-uniform scale (the
      squash-aware case: rotate 45° + scale_y<1 tilts a horizontal edge to
      atan2(sin45·k, cos45), not 45°).
    """
    if policy == "upright":
        return 0.0
    if policy != "parallel":
        raise ValueError(f"label policy must be 'upright' or 'parallel', got {policy!r}")
    v = np.asarray(local_vec, dtype=float)
    if v.shape != (2,):
        raise ValueError(f"local_vec must have shape (2,), got {v.shape}")
    w = matrix[:2, :2] @ v
    if w[0] == 0.0 and w[1] == 0.0:
        return 0.0
    return float(math.degrees(math.atan2(w[1], w[0])))
