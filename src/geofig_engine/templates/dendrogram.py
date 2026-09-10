"""
Dendrogram registry template (15_wp7).

Renders a hierarchical-linkage dendrogram from the ``(n-1) x 4`` linkage
matrix produced by ``AgglomerativeClusterModel`` (columns
``[left, right, distance, count]`` — already computed upstream).

All topology math lives in the pure numpy helper ``_dendrogram_coords``,
executed by the ``StatDendrogram`` transform at **spec-build** time. The
pipeline performs no scipy/matplotlib calls before the renderer draws the
figure. The tree layout is the classical one: leaves are placed left-to-right
at ``x = 0..n-1`` by an in-order traversal, every merge sits at the midpoint
of its two children at its ``distance`` height, and each merge draws one
inverted-U arm per child edge — **2*(n-1) segments in total**, emitted as a
single broken ``GeomLine`` (NaN separators) with a ``GeomText`` layer for the
leaf labels, so ``render_template(data=linkage_df, template="dendrogram")``
works with no mapping.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from geofig_engine.core.coord import CoordCartesian
from geofig_engine.core.geom import GeomLine, GeomText
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import Stat

LINKAGE_COLUMNS = 4

DENDROGRAM_DEFAULTS: dict[str, Any] = {
    "figsize": (8, 6),
    "title": "Dendrogram",
    "xlabel": "Sample",
    "ylabel": "Distance",
}


def _validate_linkage(linkage: np.ndarray) -> int:
    """Validate a linkage matrix; returns the number of leaves ``n``.

    Raises a clear ``ValueError`` for malformed input (wrong shape /
    non-finite distances). Non-monotone distances warn instead of raising.
    """
    if not isinstance(linkage, np.ndarray) or linkage.ndim != 2:
        raise ValueError(
            "linkage must be a 2-D ndarray of shape (n-1, 4) with columns "
            f"[left, right, distance, count]; got {type(linkage).__name__}"
        )
    n_rows = linkage.shape[0]
    if n_rows == 0:
        raise ValueError("linkage must contain at least one merge row (n >= 2)")
    if linkage.shape[1] != LINKAGE_COLUMNS:
        raise ValueError(
            "linkage must have exactly 4 columns "
            f"([left, right, distance, count]); got shape {linkage.shape}"
        )
    distances = linkage[:, 2]
    if not np.all(np.isfinite(distances)):
        raise ValueError("linkage distances must be finite (no NaN or inf)")
    if np.any(np.diff(distances) < 0):
        warnings.warn(
            "linkage distances are not monotonically non-decreasing; "
            "the resulting dendrogram may look inverted",
            UserWarning,
            stacklevel=3,
        )
    n = n_rows + 1
    total_nodes = 2 * n - 1
    node_ids = linkage[:, :2].astype(int)
    if node_ids.min() < 0 or node_ids.max() >= total_nodes:
        raise ValueError(
            "linkage node ids must lie in [0, 2n-1) for an (n-1, 4) matrix; "
            f"got ids in [{node_ids.min()}, {node_ids.max()}]"
        )
    return n


def _dendrogram_coords(linkage: np.ndarray) -> dict[str, Any]:
    """Pure coordinate layout for a dendrogram (numpy only, no scipy).

    Args:
        linkage: ``(n-1, 4)`` ndarray ``[left, right, distance, count]``.

    Returns:
        - ``"leaf_order"``: leaf ids in left-to-right dendrogram order.
        - ``"leaf_x"``: x position per leaf id (shape ``(n,)``).
        - ``"segments"``: ``2*(n-1)`` ``(x0, y0, x1, y1)`` edges — for each
          merge one inverted-U arm to each child ``(child, height) -> (merge,
          height)``.
        - ``"max_height"``: largest merge distance (labels sit below it).
    """
    n = _validate_linkage(linkage)
    left = linkage[:, 0].astype(int)
    right = linkage[:, 1].astype(int)
    distances = linkage[:, 2].astype(float)

    total_nodes = 2 * n - 1
    x = np.zeros(total_nodes)
    y = np.zeros(total_nodes)
    children = {n + r: (int(left[r]), int(right[r])) for r in range(n - 1)}

    # 1. In-order traversal: leaves get their dendrogram x positions.
    leaf_order: list[int] = []

    def place_leaves(node: int) -> None:
        if node < n:
            leaf_order.append(node)
            return
        l, r = children[node]
        place_leaves(l)
        place_leaves(r)

    place_leaves(total_nodes - 1)
    for pos, leaf in enumerate(leaf_order):
        x[leaf] = float(pos)

    # 2. Merge heights and cluster x = midpoint of the children.
    for r in range(n - 1):
        node = n + r
        y[node] = distances[r]
        l, r_child = children[node]
        x[node] = 0.5 * (x[l] + x[r_child])

    # 3. One inverted-U arm per child edge -> exactly 2*(n-1) segments.
    segments: list[tuple[float, float, float, float]] = []
    for r in range(n - 1):
        node = n + r
        l, r_child = children[node]
        height = distances[r]
        segments.append((float(x[l]), float(y[l]), float(x[node]), float(height)))
        segments.append((float(x[node]), float(height), float(x[r_child]), float(y[r_child])))

    return {
        "leaf_order": leaf_order,
        "leaf_x": x[:n],
        "segments": segments,
        "max_height": float(distances.max()),
    }


@dataclass(frozen=True)
class StatDendrogram(Stat):
    """Spec-build transform: linkage matrix -> dendrogram layer coordinates.

    ``mode="edges"`` produces the broken ``x``/``y`` polyline (NaN between
    segments, so the single ``GeomLine`` renders the 2*(n-1) tree edges).
    ``mode="labels"`` produces one ``x``/``y``/``label`` row per leaf.
    """

    mode: str = "edges"

    def __init__(self, mode: str = "edges") -> None:
        if mode not in ("edges", "labels"):
            raise ValueError("StatDendrogram mode must be 'edges' or 'labels'")
        object.__setattr__(self, "mode", mode)
        super().__init__(name="dendrogram", params={"mode": mode})

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        frame = data.iloc[:, :LINKAGE_COLUMNS]
        if frame.shape[1] != LINKAGE_COLUMNS:
            raise ValueError(
                f"dendrogram input must have at least {LINKAGE_COLUMNS} columns "
                f"([left, right, distance, count]); got {data.shape[1]}"
            )
        linkage = frame.to_numpy(dtype=float)
        coords = _dendrogram_coords(linkage)

        if self.mode == "edges":
            xs: list[float] = []
            ys: list[float] = []
            for x0, y0, x1, y1 in coords["segments"]:
                xs.extend([x0, x1])
                ys.extend([y0, y1])
                xs.append(np.nan)
                ys.append(np.nan)
            return pd.DataFrame({"x": xs[:-1], "y": ys[:-1]})

        # labels mode: one row per leaf, below the lowest merge height.
        leaves = coords["leaf_order"]
        label_y = -0.05 * coords["max_height"]
        return pd.DataFrame(
            {
                "x": [float(coords["leaf_x"][leaf]) for leaf in leaves],
                "y": [label_y] * len(leaves),
                "label": [str(leaf) for leaf in leaves],
            }
        )


def dendrogram_builder(
    mapping: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
    **_,
) -> "TemplateRecipe":
    """Pipeline registry builder for the ``dendrogram`` key (15_wp7).

    The layer channel sources are the **stat-produced** columns (``x``/``y``
    from the linkage layout, ``label`` from the leaf order), so no mapping is
    needed — ``render_template(data=linkage_df, template="dendrogram")`` just
    works. Any ``mapping`` supplied is applied by ``render_template``'s
    per-layer override on top of these defaults.

    The ``TemplateRecipe`` import is deferred to call time so this template
    module never depends on ``engine.api`` at import time.
    """
    from geofig_engine.engine.api import TemplateRecipe

    del mapping  # channel sources are the stat-produced columns; unused here

    return TemplateRecipe(
        name="dendrogram",
        layers=[
            Layer(
                geom=GeomLine(),
                stat=StatDendrogram(mode="edges"),
                mapping={"x": "x", "y": "y"},
            ),
            Layer(
                geom=GeomText(),
                stat=StatDendrogram(mode="labels"),
                mapping={"x": "x", "y": "y", "label": "label"},
            ),
        ],
        coord=CoordCartesian(),
        default_settings={**DENDROGRAM_DEFAULTS, **(settings or {})},
    )