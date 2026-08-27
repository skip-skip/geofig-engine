"""
LinkTransform: affine placement of a linked axis inside world space.

Each child FigureSpec carries a LinkTransform that maps its local
coordinate space into the parent's world space.

Composition convention (pinned by unit tests in ``tests/test_links.py``):

``LinkTransform`` is a **fluent, orderable builder**. Operations are chained
in call order and each operation is applied to points in that same order
(first-called op transforms points first):

    LinkTransform().rotate(45).scale(sx, sy).translate(tx, ty)

    matrix():  M = translate · scale · rotate   (ops left-multiplied in call order)

so for a point ``p`` the matrix acts as ``M @ p``, meaning ``p`` experiences
rotate, then scale, then translate. This reproduces the classic Piper diamond
"rotate 45°, then squash y, then center" directly::

    LinkTransform().rotate(45.0).scale(0.0035, 0.0061).translate(0.5, 0.0)

Each fluent method returns a **new** ``LinkTransform`` (the receiver is
unchanged); ``.ops`` exposes the ordered operation list for introspection.

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


def _op_matrix(kind: str, params) -> np.ndarray:
    """Return the 3x3 homogeneous matrix for a single operation."""
    if kind == "translate":
        tx, ty = params
        return np.array([[1.0, 0.0, tx], [0.0, 1.0, ty], [0.0, 0.0, 1.0]])
    if kind == "scale":
        sx, sy = params
        return np.array([[sx, 0.0, 0.0], [0.0, sy, 0.0], [0.0, 0.0, 1.0]])
    if kind == "rotate":
        theta = math.radians(params)
        c, s = math.cos(theta), math.sin(theta)
        return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    raise ValueError(f"unknown LinkTransform operation {kind!r}")


@dataclass(frozen=True)
class LinkTransform:
    """
    Fluent, orderable affine placement of a linked axis inside world space.

    Operations are chained in call order; each is applied to points in that
    same order (first-called op transforms points first). Every fluent method
    returns a new ``LinkTransform``; the receiver is unchanged.

    Attributes:
        ops: Ordered list of operations, each either ``("translate", (tx, ty))``,
            ``("scale", (sx, sy))``, or ``("rotate", deg)``. Identifies the
            transform's full composition for introspection/equality.
    """

    ops: tuple[tuple[str, tuple | float], ...] = ()

    def __post_init__(self) -> None:
        normalized = []
        for kind, params in self.ops:
            if kind == "translate":
                normalized.append((kind, _numeric_pair(params, "translate")))
            elif kind == "scale":
                normalized.append((kind, _numeric_pair(params, "scale")))
            elif kind == "rotate":
                normalized.append((kind, _real_number(params, "rotate")))
            else:
                raise ValueError(
                    f"unknown LinkTransform operation {kind!r}; "
                    f"expected 'translate', 'scale', or 'rotate'"
                )
        object.__setattr__(self, "ops", tuple(normalized))

    # -- fluent builders ---------------------------------------------------

    def translate(self, tx, ty=0.0) -> "LinkTransform":
        """Return a new transform that additionally translates by (tx, ty).

        Translation is applied to points as the outermost (last) step.
        """
        return LinkTransform(ops=self.ops + (("translate", (tx, ty)),))

    def scale(self, sx, sy=None) -> "LinkTransform":
        """Return a new transform that additionally scales by (sx, sy).

        If ``sy`` is omitted it defaults to ``sx`` (uniform scale).
        """
        if sy is None:
            sy = sx
        return LinkTransform(ops=self.ops + (("scale", (sx, sy)),))

    def rotate(self, deg) -> "LinkTransform":
        """Return a new transform that additionally rotates by *deg* degrees."""
        return LinkTransform(ops=self.ops + (("rotate", deg),))

    # -- math --------------------------------------------------------------

    def matrix(self) -> np.ndarray:
        """
        Return the 3x3 homogeneous matrix for this transform's op chain.

        Built by left-multiplying each operation's matrix in call order, so
        the first-called op ends up rightmost and is applied to points first.
        """
        result = np.eye(3)
        for kind, params in self.ops:
            result = _op_matrix(kind, params) @ result
        return result

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
        """JSON-compatible representation of this transform (ordered ops)."""
        return {
            "operations": [
                [kind, list(params) if isinstance(params, tuple) else params]
                for kind, params in self.ops
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LinkTransform":
        """Reconstruct a LinkTransform from its dict representation."""
        ops_raw = data.get("operations", [])
        ops = []
        for entry in ops_raw:
            kind = entry[0]
            params = entry[1]
            if kind in ("translate", "scale"):
                ops.append((kind, tuple(params)))
            else:
                ops.append((kind, params))
        return cls(ops=tuple(ops))

    def __repr__(self) -> str:
        return f"LinkTransform(ops={list(self.ops)!r})"


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
