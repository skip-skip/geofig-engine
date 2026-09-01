"""
Matplotlib renderer for FigEngine.

This backend draws fully resolved FigureSpec objects using matplotlib.
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pandas as pd
from matplotlib.dates import DateFormatter
import matplotlib.pyplot as plt
import matplotlib.text

from matplotlib.transforms import Affine2D, IdentityTransform

from geofig_engine.core.axis import AxisFormat, parse_axis_settings
from geofig_engine.core.coord import CoordCartesian, CoordFlipped, CoordFixed, CoordPolar, StiffCoord, TernaryCoord
from geofig_engine.core.facet import FacetGrid, FacetNull, FacetWrap
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.link import LinkTransform, label_rotation
from geofig_engine.core.secondary_axis import parse_secondary_settings
from geofig_engine.core.spec import FigureSpec
from geofig_engine.renderers.base import BaseRenderer
from geofig_engine.renderers.matplotlib.handlers import (
    render_abline,
    render_area,
    render_bar,
    render_box,
    render_errorbar,
    render_function_line,
    render_hspan,
    render_line,
    render_point,
    render_rect,
    render_ribbon,
    render_step_line,
    render_text,
    render_violin,
    render_vspan,
)
from geofig_engine.renderers.matplotlib.legend import LegendAccumulator, render_legend_figure
from geofig_engine.renderers.matplotlib.util import IMPLEMENTED

_GEOM_HANDLERS = {
    "point": render_point,
    "line": render_line,
    "function_line": render_function_line,
    "bar": render_bar,
    "area": render_area,
    "ribbon": render_ribbon,
    "text": render_text,
    "errorbar": render_errorbar,
    "box": render_box,
    "violin": render_violin,
    "step_line": render_step_line,
    "hspan": render_hspan,
    "vspan": render_vspan,
    "rect": render_rect,
    "abline": render_abline,
}


def _nice_tick_max(max_val: float) -> float:
    """Return a nice round max tick value >= max_val for a 5-tick scale.

    Produces ticks at -tick_max, -tick_max/2, 0, tick_max/2, tick_max.
    """
    nice_maxes = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
    for nm in nice_maxes:
        if nm >= max_val:
            return nm
    return nice_maxes[-1]


def _filter_series(val, rows):
    if isinstance(val, pd.Series):
        idx = val.index.intersection(rows)
        return val.loc[idx]
    return val


def _facet_panels(facet, data):
    if isinstance(facet, FacetNull) or not data.columns.intersection(facet.by).any():
        return [(data, {})]
    panels = []
    grouped = data.groupby(list(facet.by), sort=True)
    for keys, subset in grouped:
        keys_tuple = keys if isinstance(keys, tuple) else (keys,)
        ctx = dict(zip(facet.by, keys_tuple))
        panels.append((subset, ctx))
    return panels


# ---------------------------------------------------------------------------
# Frame drawing: implied by child FigureSpec's coord type
#
# Each child FigureSpec carries a coord and settings. The renderer auto-
# selects the frame drawing function based on isinstance checks; frame hints
# (title, xlim/ylim bounds, grid_step, tick_step, label_policy) are read from
# the child's settings. Frame geometry is drawn in local space; the renderer
# stamps line artists with the child's affine so they deform identically to
# data. Text labels are placed world-side via _apply_matrix_pts so they
# remain upright.
# ---------------------------------------------------------------------------


def _apply_matrix_pts(matrix: np.ndarray, pts) -> np.ndarray:
    """Map an iterable of (x, y) points through a 3x3 homogeneous matrix."""
    arr = np.asarray(pts, dtype=float)
    ones = np.ones((arr.shape[0], 1))
    return (matrix @ np.hstack([arr, ones]).T).T[:, :2]


def _affine_from_matrix(matrix: np.ndarray) -> Affine2D:
    """Build an Affine2D from a 3x3 homogeneous matrix (flat, no nesting)."""
    return Affine2D.from_values(
        matrix[0, 0], matrix[1, 0],
        matrix[0, 1], matrix[1, 1],
        matrix[0, 2], matrix[1, 2],
    )


SQRT3_2 = math.sqrt(3) / 2.0

# Default perpendicular offset for axis arrows, expressed as a multiple of the
# tick-label offset so arrows sit clearly beyond the label strip when no
# explicit ``axis_arrow_offset`` is configured.
_ARROW_OFFSET_MULT = 2.0

# Secondary-axis title offset, expressed as a multiple of the secondary
# tick-label offset ``d``. Tied to ``d`` (rather than a fraction of the axis
# range) so the empty strip between the tick labels and the axis title scales
# with the configured label offset. With the Piper diamond's default
# ``d = range/20`` this reproduces the ternary frame's label-to-tick buffer
# (~0.045 world units) instead of the previous ``0.20 * range`` gap.
_SECONDARY_TITLE_OFFSET_MULT = 2.8


def _tick_label(value: float, fmt: str) -> str:
    """Format a numeric tick label with a format-spec string.

    ``fmt`` is a matplotlib-style format spec such as ``":g"`` or ``":.1f"``
    (the leading ``:`` is optional). The default ``":g"`` reproduces the
    current ``f"{x:g}"`` output for numeric tick labels.
    """
    spec = fmt[1:] if fmt.startswith(":") else fmt
    return f"{value:{spec}}"


def _draw_axis_arrow(
    ax,
    matrix: np.ndarray,
    start_local,
    end_local,
    local_vec,
    style: str = "-|>",
    lw: float = 1.0,
    label: str | None = None,
    label_fs: float | None = None,
    label_policy: str = "upright",
):
    """Draw a direction arrow parallel to an axis, pointing toward increasing values.

    ``start_local`` / ``end_local`` are the axis's low-value and high-value
    local-space endpoints (callers order them low→high so the arrowhead always
    lands on the high-value end — the "axis values must be sorted" rule). Callers
    displace these endpoints to set the arrow's offset from the axis (e.g. below
    the bottom edge, left of the left edge) before passing them. Both endpoints
    are mapped to world space via ``matrix`` so the arrow deforms identically to
    framed geometry, and the arrowhead (``style``) is drawn at the high-value end
    with ``ax.annotate``.

    An optional ``label`` is placed at the midpoint and rotated with
    :func:`~geofig_engine.core.link.label_rotation` using ``local_vec`` (the
    local tangent of the edge), so it stays parallel under ``"parallel"`` policy.
    """
    start_arr = np.asarray([start_local, end_local], dtype=float)

    world = _apply_matrix_pts(matrix, start_arr)
    ax.annotate(
        "",
        xy=world[1],
        xytext=world[0],
        arrowprops=dict(arrowstyle=style, color="black", lw=lw),
        annotation_clip=False,
    )

    if label:
        wmid = _apply_matrix_pts(matrix, [(start_arr[0] + start_arr[1]) / 2.0])[0]
        rot = label_rotation(tuple(local_vec), matrix, policy=label_policy)
        ax.text(
            wmid[0],
            wmid[1],
            label,
            ha="center",
            va="center",
            rotation=rot,
            fontsize=label_fs,
            bbox=dict(facecolor="white", edgecolor="none", pad=1),
            clip_on=False,
        )


def _child_local_bbox(child):
    """Local-space bounding box corners for a child FigureSpec.

    TernaryCoord → unit triangle; CoordCartesian with axis ``limits`` (flat
    ``xlim``/``ylim`` via AxisFormat) → that region (e.g. the diamond's
    [0,100]²); everything else → unit square.
    """
    coord = child.coord
    if isinstance(coord, TernaryCoord):
        return [(0, 0), (1, 0), (0.5, SQRT3_2), (0, 0)]
    if isinstance(coord, CoordCartesian):
        axis = parse_axis_settings(child.settings, coord)
        if axis.xlim is not None and axis.ylim is not None:
            x0, x1 = axis.xlim
            y0, y1 = axis.ylim
            return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return [(0, 0), (1, 0), (0, 1), (1, 1)]


def _draw_ternary_frame(ax, axis: AxisFormat, matrix, coord):
    """Draw ternary triangle frame in local space, stamped by matrix.

    Reads ions from coord.channels, reversals from coord.handedness, and all
    styling/formatting from the parsed :class:`AxisFormat` (``axis``).
    """
    ions = list(coord.labels if coord.labels is not None else coord.channels)
    handedness = coord.handedness
    title = axis.title
    tick_policy = axis.tick_label_policy_eff()
    axis_policy = axis.axis_label_policy_eff()
    tick_fs = axis.resolve_fontsize("tick")
    ion_fs = axis.resolve_fontsize("axis_label")
    title_fs = axis.resolve_fontsize("title")
    frame_lw = axis.frame_linewidth
    grid_style = axis.grid_style
    tick_fmt = axis.tick_format

    # Value-range reversal per edge (drives both tick labels and arrows so they
    # stay consistent). Both the cation (left) and anion (right) triangles read
    # with the same non-mirrored pattern, so the reversal flags do not depend on
    # handedness (which only mirrors the physical placement of the triangle):
    #   base edge   -> increasing toward the base-left corner (100% there)
    #   left edge   -> increasing toward the apex
    #   right edge  -> increasing toward the base-right corner
    rev_bottom = True
    rev_left = False
    rev_right = True

    # -- triangle outline (local space) --
    tri_local = [(0, 0), (1, 0), (0.5, SQRT3_2), (0, 0)]
    tri_arr = np.array(tri_local, dtype=float)
    ax.plot(tri_arr[:, 0], tri_arr[:, 1], color="black", linewidth=frame_lw, zorder=2)

    # -- internal grid at 20/40/60/80% (local space) --
    for t in [0.2, 0.4, 0.6, 0.8]:
        family1 = [(t, 0), (t * 0.5, t * SQRT3_2)]
        family2 = [(t, 0), ((1 + t) / 2, (1 - t) * SQRT3_2)]
        family3 = [(t * 0.5, t * SQRT3_2), (1 - t * 0.5, t * SQRT3_2)]
        for fam in (family1, family2, family3):
            fam_arr = np.array(fam, dtype=float)
            ax.plot(fam_arr[:, 0], fam_arr[:, 1], color=grid_style.get("color", "gray"),
                    linewidth=grid_style.get("linewidth", 0.3),
                    linestyle=grid_style.get("linestyle", ":"), zorder=1)

    # -- tick labels at 20/40/60/80% (world-side text) --
    for tick_val in [0.2, 0.4, 0.6, 0.8]:
        tick_str = str(int(tick_val * 100))
        inv = str(100 - int(tick_str))

        bottom_lbl = inv if rev_bottom else tick_str
        left_lbl = inv if rev_left else tick_str
        right_lbl = inv if rev_right else tick_str

        wb = _apply_matrix_pts(matrix, [(tick_val, -0.03)])[0]
        ax.text(wb[0], wb[1], bottom_lbl, ha="center", va="top", fontsize=tick_fs,
                rotation=label_rotation((1, 0), matrix, policy=tick_policy),
                clip_on=False)

        wl = _apply_matrix_pts(matrix, [(
            tick_val * 0.5 - 0.026, tick_val * SQRT3_2 + 0.015
        )])[0]
        ax.text(wl[0], wl[1], left_lbl, ha="center", va="center", fontsize=tick_fs,
                rotation=label_rotation(
                    (0.5, SQRT3_2), matrix, policy=tick_policy),
                clip_on=False)

        wr = _apply_matrix_pts(matrix, [(
            1 - tick_val * 0.5 + 0.026, tick_val * SQRT3_2 + 0.015
        )])[0]
        ax.text(wr[0], wr[1], right_lbl, ha="center", va="center", fontsize=tick_fs,
                rotation=label_rotation(
                    (-0.5, SQRT3_2), matrix, policy=tick_policy),
                clip_on=False)

    # -- edge title (world-side text) --
    if title:
        wt = _apply_matrix_pts(matrix, [(0.5, SQRT3_2 + 0.12)])[0]
        ax.text(wt[0], wt[1], title, ha="center", va="bottom", fontsize=title_fs,
                fontweight="bold", clip_on=False)

    # -- ion edge labels (world-side text, always drawn) --
    # Standalone labels at each edge midpoint; independent of any arrows.
    if len(ions) == 3:
        offset = 0.12
        cos30 = SQRT3_2
        mid_left = (0.25 - offset * cos30, SQRT3_2 / 2.0 + offset * 0.5)
        mid_base = (0.5, -offset)
        mid_right = (0.75 + offset * cos30, SQRT3_2 / 2.0 + offset * 0.5)

        for anchor, text, tangent in (
            (mid_base, ions[0], (1, 0)),
            (mid_left, ions[1], (0.5, SQRT3_2)),
            (mid_right, ions[2], (-0.5, SQRT3_2)),
        ):
            wp = _apply_matrix_pts(matrix, [anchor])[0]
            ax.text(wp[0], wp[1], text, ha='center', va='center',
                    rotation=label_rotation(tangent, matrix, policy=axis_policy),
                    fontsize=ion_fs,
                    bbox=dict(facecolor='white', edgecolor='none', pad=1),
                    clip_on=False)

    # -- axis direction arrows (opt-in) --
    # Each arrow runs parallel to its edge and points toward the direction in
    # which the edge's parallel axis increases in value (toward the edge's
    # 100% corner), offset just outside the triangle. The high-value corner per
    # edge is given by the same rev_* flags that orient the tick labels, so the
    # arrow always agrees with the displayed scale regardless of handedness.
    if axis.show_arrows():
        arrow_off = axis.axis_arrow_offset if axis.axis_arrow_offset is not None else 0.06
        apex_off = (arrow_off * cos30, arrow_off * 0.5)

        # Bottom edge (parallel axis base-left -> base-right).
        if rev_bottom:
            _draw_axis_arrow(ax, matrix, (1.0, -arrow_off), (0.0, -arrow_off),
                             (1.0, 0.0), lw=frame_lw)
        else:
            _draw_axis_arrow(ax, matrix, (0.0, -arrow_off), (1.0, -arrow_off),
                             (1.0, 0.0), lw=frame_lw)

        # Left edge (parallel axis base-left -> apex): toward apex by default.
        if rev_left:
            _draw_axis_arrow(
                ax, matrix,
                (0.5 - arrow_off * cos30, SQRT3_2 + arrow_off * 0.5),
                (-apex_off[0], apex_off[1]),
                (0.5, SQRT3_2), lw=frame_lw,
            )
        else:
            _draw_axis_arrow(
                ax, matrix,
                (-apex_off[0], apex_off[1]),
                (0.5 - arrow_off * cos30, SQRT3_2 + arrow_off * 0.5),
                (0.5, SQRT3_2), lw=frame_lw,
            )

        # Right edge (parallel axis base-right -> apex): toward apex by default.
        if rev_right:
            _draw_axis_arrow(
                ax, matrix,
                (0.5 + arrow_off * cos30, SQRT3_2 + arrow_off * 0.5),
                (1.0 + apex_off[0], apex_off[1]),
                (-0.5, SQRT3_2), lw=frame_lw,
            )
        else:
            _draw_axis_arrow(
                ax, matrix,
                (1.0 + apex_off[0], apex_off[1]),
                (0.5 + arrow_off * cos30, SQRT3_2 + arrow_off * 0.5),
                (-0.5, SQRT3_2), lw=frame_lw,
            )


def _draw_cartesian_axis(ax, axis: AxisFormat, matrix):
    """Draw a cartesian axis frame in local space, stamped by *matrix*.

    Reads the axis region and styling from a parsed
    :class:`~geofig_engine.core.axis.AxisFormat`:
      - ``limits``: axis bounds in local space (default ``(0, 1)²``)
      - ``grid_step``: gridline spacing in both directions (default 0.2)
      - ``tick_step``: tick label spacing (default = grid_step)
      - ``label_policy``: "upright" or "parallel" (default "upright")
      - ``title``: world-side label above the box
      - ``tick_format``: format-spec for numeric tick labels
      - ``secondary_x``/``secondary_y``: extra scales drawn along the top/right
        edges, mapped linearly onto the primary ``limits`` (see
        :mod:`geofig_engine.core.secondary_axis`).

    All geometry (box + gridlines) is drawn in local space and later stamped
    with the child's affine, exactly like data. Tick labels and title are
    placed world-side via ``_apply_matrix_pts`` so they stay upright. This
    generalizes the Piper diamond (a cartesian child in ``[0,100]²`` rotated
    45°) as well as any rotated/translated cartesian child that opts into a
    frame by supplying its bounds.
    """
    xlim = axis.xlim if axis.xlim is not None else (0.0, 1.0)
    ylim = axis.ylim if axis.ylim is not None else (0.0, 1.0)
    grid_step = axis.grid_step if axis.grid_step is not None else 0.2
    tick_step = axis.tick_step if axis.tick_step is not None else grid_step
    tick_policy = axis.tick_label_policy_eff()
    title = axis.title
    tick_fs = axis.resolve_fontsize("tick")
    title_fs = axis.resolve_fontsize("title")
    frame_lw = axis.frame_linewidth
    grid_style = axis.grid_style
    tick_fmt = axis.tick_format

    secondary = parse_secondary_settings(
        _frame_settings_dict(axis),
        defaults={
            "tick_step": tick_step,
            "label_policy": axis.label_policy,
            "axis_label_policy": axis.axis_label_policy_eff(),
            "tick_label_policy": axis.tick_label_policy_eff(),
        },
    )

    x0, x1 = xlim
    y0, y1 = ylim
    xlo, xhi = min(x0, x1), max(x0, x1)
    ylo, yhi = min(y0, y1), max(y0, y1)

    # -- outline (local space) --
    box = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    box_arr = np.array(box, dtype=float)
    ax.plot(box_arr[:, 0], box_arr[:, 1], color="black", linewidth=frame_lw, zorder=2)

    # -- internal grid (local space) --
    xs = list(np.arange(xlo + grid_step, xhi, grid_step))
    ys = list(np.arange(ylo + grid_step, yhi, grid_step))
    for gx in xs:
        g = [(gx, y0), (gx, y1)]
        ax.plot([g[0][0], g[1][0]], [g[0][1], g[1][1]], color=grid_style.get("color", "gray"),
                linewidth=grid_style.get("linewidth", 0.3), linestyle=grid_style.get("linestyle", ":"),
                zorder=1)
    for gy in ys:
        ax.plot([x0, x1], [gy, gy], color=grid_style.get("color", "gray"),
                linewidth=grid_style.get("linewidth", 0.3), linestyle=grid_style.get("linestyle", ":"),
                zorder=1)

    # -- tick-label offset from the edge (default derived from limits size) --
    d = axis.label_offset
    if d is None:
        d = 1.0 if xhi - xlo == 1.0 else (xhi - xlo) / 20.0

    # -- axis-arrow offset from the edge (default past the tick-label strip) --
    d_arrow = axis.axis_arrow_offset
    if d_arrow is None:
        d_arrow = _ARROW_OFFSET_MULT * d

    # -- tick labels on bottom edge (world-side text) --
    # X-axis ticks at tick_step along the bottom (ylo) edge, interior only.
    for tx in np.arange(xlo, xhi + 0.5 * tick_step, tick_step):
        if xlo - 1e-9 <= tx <= xlo + 1e-9 or xhi - 1e-9 <= tx <= xhi + 1e-9:
            continue
        tval = xlo + xhi - tx if axis.x_reversed else tx
        w = _apply_matrix_pts(matrix, [(tx, ylo - d)])[0]
        ax.text(w[0], w[1], _tick_label(tval, tick_fmt), ha="center", va="top", fontsize=tick_fs,
                rotation=label_rotation((1, 0), matrix, policy=tick_policy),
                clip_on=False)

    # -- tick labels on left edge (world-side text) --
    for ty in np.arange(ylo, yhi + 0.5 * tick_step, tick_step):
        if ylo - 1e-9 <= ty <= ylo + 1e-9 or yhi - 1e-9 <= ty <= yhi + 1e-9:
            continue
        tval = ylo + yhi - ty if axis.y_reversed else ty
        w = _apply_matrix_pts(matrix, [(xlo - d, ty)])[0]
        ax.text(w[0], w[1], _tick_label(tval, tick_fmt), ha="right", va="center", fontsize=tick_fs,
                rotation=label_rotation((0, 1), matrix, policy=tick_policy),
                clip_on=False)

    # -- tick labels on top edge from secondary x (world-side text) --
    if "x" in secondary:
        sec = secondary["x"]
        for sv, lx in sec.tick_coordinates():
            if xlo - 1e-9 <= lx <= xlo + 1e-9 or xhi - 1e-9 <= lx <= xhi + 1e-9:
                continue
            w = _apply_matrix_pts(matrix, [(lx, yhi + d)])[0]
            ax.text(w[0], w[1], _tick_label(sv, tick_fmt), ha="center", va="bottom", fontsize=tick_fs,
                    rotation=label_rotation((1, 0), matrix, policy=sec.tick_label_policy_eff()),
                    clip_on=False)

    # -- tick labels on right edge from secondary y (world-side text) --
    if "y" in secondary:
        sec = secondary["y"]
        for sv, ly in sec.tick_coordinates():
            if ylo - 1e-9 <= ly <= ylo + 1e-9 or yhi - 1e-9 <= ly <= yhi + 1e-9:
                continue
            w = _apply_matrix_pts(matrix, [(xhi + d, ly)])[0]
            ax.text(w[0], w[1], _tick_label(sv, tick_fmt), ha="left", va="center", fontsize=tick_fs,
                    rotation=label_rotation((0, 1), matrix, policy=sec.tick_label_policy_eff()),
                    clip_on=False)

    # -- secondary axis titles (world-side text, beyond the tick labels) --
    if "x" in secondary and secondary["x"].label:
        sec = secondary["x"]
        wt = _apply_matrix_pts(matrix, [((xlo + xhi) / 2.0, yhi + _SECONDARY_TITLE_OFFSET_MULT * d)])[0]
        ax.text(wt[0], wt[1], sec.label, ha="center", va="bottom", fontsize=axis.resolve_fontsize("axis_label"),
                rotation=label_rotation((1, 0), matrix, policy=sec.axis_label_policy_eff()),
                clip_on=False)
    if "y" in secondary and secondary["y"].label:
        sec = secondary["y"]
        wt = _apply_matrix_pts(matrix, [(xhi + _SECONDARY_TITLE_OFFSET_MULT * d, (ylo + yhi) / 2.0)])[0]
        ax.text(wt[0], wt[1], sec.label, ha="left", va="center", fontsize=axis.resolve_fontsize("axis_label"),
                rotation=label_rotation((0, 1), matrix, policy=sec.axis_label_policy_eff()),
                clip_on=False)

    # -- edge title (world-side text) --
    if title:
        wt = _apply_matrix_pts(matrix, [((xlo + xhi) / 2.0, yhi + 0.12 * (yhi - ylo))])[0]
        ax.text(wt[0], wt[1], title, ha="center", va="bottom", fontsize=title_fs,
                fontweight="bold", clip_on=False)

    # -- axis direction arrows (opt-in) --
    if axis.show_arrows():
        # Primary axes: always point toward increasing data. For a non-reversed
        # axis that is the ascending (high) end; for a reversed axis the data
        # itself is flipped, so the arrow points toward the (now) low end.
        # Offsets place the arrows outside the box (below the bottom edge /
        # left of the left edge), beyond the tick-label strip (``d_arrow``).
        if x0 != x1:
            x_end = xhi if not axis.x_reversed else xlo
            _draw_axis_arrow(
                ax, matrix,
                (xlo + xhi - x_end, ylo - d_arrow), (x_end, ylo - d_arrow),
                (1.0, 0.0), lw=frame_lw,
            )
        if y0 != y1:
            y_end = yhi if not axis.y_reversed else ylo
            _draw_axis_arrow(
                ax, matrix,
                (xlo - d_arrow, ylo + yhi - y_end), (xlo - d_arrow, y_end),
                (0.0, 1.0), lw=frame_lw,
            )
        # Secondary axes: point toward ascending secondary values, offset
        # outside the opposite edge (above the top / right of the right edge).
        if "x" in secondary:
            sec = secondary["x"]
            slo, shi = min(sec.range), max(sec.range)
            _draw_axis_arrow(
                ax, matrix,
                (sec.inv(slo), yhi + d_arrow), (sec.inv(shi), yhi + d_arrow),
                (1.0, 0.0), lw=frame_lw,
            )
        if "y" in secondary:
            sec = secondary["y"]
            slo, shi = min(sec.range), max(sec.range)
            _draw_axis_arrow(
                ax, matrix,
                (xhi + d_arrow, sec.inv(slo)), (xhi + d_arrow, sec.inv(shi)),
                (0.0, 1.0), lw=frame_lw,
            )



def _frame_settings_dict(axis: AxisFormat) -> dict:
    """Reconstruct a flat settings-style dict from an AxisFormat.

    Used to feed ``parse_secondary_settings`` (which reads flat top-level keys)
    while letting AxisFormat be the single source of format truth for the frame
    pipeline. The secondary ``range``/``label``/``position`` declarations live
    in ``axis.options``; common fallbacks come from the actual parsed values.
    """
    out: dict = {
        "xlim": (0.0, 1.0) if axis.xlim is None else axis.xlim,
        "ylim": (0.0, 1.0) if axis.ylim is None else axis.ylim,
    }
    if axis.grid_step is not None:
        out["grid_step"] = axis.grid_step
    if axis.tick_step is not None:
        out["tick_step"] = axis.tick_step
    if axis.label_policy != "upright":
        out["label_policy"] = axis.label_policy
    for key in ("secondary_x", "secondary_y"):
        if key in axis.options:
            out[key] = axis.options[key]
    return out


def _with_flat_secondary(axis: AxisFormat, settings: dict) -> AxisFormat:
    """Merge flat ``secondary_x``/``secondary_y`` settings keys into ``options``.

    The secondary-axis declarations are flat top-level settings keys on a child.
    This keeps them reachable by the unified pipeline while ``AxisFormat``
    remains the single format source. Existing ``options`` entries win over the
    flat fallback.
    """
    options = dict(axis.options)
    for key in ("secondary_x", "secondary_y"):
        if key in settings and key not in options:
            options[key] = settings[key]
    if not options:
        return axis
    return dataclasses.replace(axis, options=options)


_ARTIST_CONTAINERS = ("lines", "collections", "patches", "texts", "images")


class MatplotlibRenderer(BaseRenderer):
    """Matplotlib backend for rendering FigEngine FigureSpec objects."""

    def render(self, spec: FigureSpec):
        if self.supports(spec) is False:
            raise NotImplementedError(f"MatplotlibRenderer does not currently support template '{spec.template_name}'")

        if spec.children:
            return self._render_children(spec)
        if isinstance(spec.coord, StiffCoord):
            return self._render_stiff(spec)
        if not isinstance(spec.facet, FacetNull):
            return self._render_faceted(spec)
        if self._is_framed_single(spec):
            return self._render_single_framed(spec)

        return self._render_single(spec)

    @staticmethod
    def _is_framed_single(spec: FigureSpec) -> bool:
        """Whether a top-level spec draws the custom shared frame.

        Top-level specs with no declared frame (plain line/timeseries charts,
        histograms, etc.) keep native matplotlib axes. A spec becomes "framed"
        when it is ternary (a triangle frame) or cartesian with explicit
        world limits — the same conditions under which ``_draw_frame`` draws.
        """
        if isinstance(spec.coord, TernaryCoord):
            return True
        if isinstance(spec.coord, CoordCartesian):
            axis = parse_axis_settings(spec.settings, spec.coord)
            return axis.xlim is not None and axis.ylim is not None
        return False

    def _render_single_framed(self, spec: FigureSpec):
        """Render a top-level framed spec as one child with an identity transform.

        Reuses the exact child machinery (``_apply_child_coord_transforms`` +
        ``_draw_frame`` + ``_render_axes`` + ``_children_world_limits``) so
        top-level cartesian/ternary render through the same code and the same
        :class:`~geofig_engine.core.axis.AxisFormat` as nested children — the
        "top-level ≡ child" unification. With the identity transform, local ==
        world, so a top-level ternary spec finally draws its triangle.
        """
        figsize = spec.settings.get("figsize", (10, 6))
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_facecolor("none")
        if not spec.layers:
            raise ValueError("FigureSpec must define at least one layer")

        spec = self._apply_child_coord_transforms(spec)
        affine = _affine_from_matrix(spec.transform.matrix())

        # Frame first (below data): identity affine (local == world).
        snapshot = self._snapshot_artists(ax)
        self._draw_frame(ax, spec)
        for artist in self._new_artists(ax, snapshot):
            if not isinstance(artist, matplotlib.text.Text):
                artist.set_transform(affine + ax.transData)

        self._render_axes(ax, spec, spec.data, layer_affine=lambda layer, a=affine: a)

        xlim, ylim = self._children_world_limits([spec])
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_aspect("equal")

        title = spec.settings.get("title")
        if title:
            _axis = parse_axis_settings(spec.settings, spec.coord)
            fig.suptitle(title, fontsize=_axis.resolve_fontsize("suptitle"), y=0.98)
        ax.axis("off")

        plt.close(fig)
        return fig

    # ------------------------------------------------------------------
    # Single-axes (non-faceted)
    # ------------------------------------------------------------------

    def _render_single(self, spec: FigureSpec):
        figsize = spec.settings.get("figsize", (10, 6))
        coord = spec.coord
        subplot_kw = {}
        if isinstance(coord, CoordPolar):
            subplot_kw["projection"] = "polar"

        fig, ax = plt.subplots(figsize=figsize, subplot_kw=subplot_kw)

        if not spec.layers:
            raise ValueError("FigureSpec must define at least one layer")

        spec = self._apply_coord_transform(spec)

        self._render_axes(ax, spec, spec.data)

        if isinstance(coord, CoordPolar):
            self._draw_frame(ax, spec)

        self._apply_settings(ax, fig, spec)
        plt.close(fig)
        return fig

    def _render_axes(self, ax, spec, data, layer_affine=None):
        """Render all layers onto a single Axes, filtered to *data* rows.

        When *layer_affine* is provided (linked-axes path) it maps each
        LayerSpec to an Affine2D placed between data and display space;
        artists created for that layer are stamped with
        ``affine + ax.transData``. Handlers themselves stay transform-blind.
        """
        rows = data.index

        data_idx = 0
        func_layers = []
        for i, layer in enumerate(spec.layers):
            if layer.geom.name == "function_line":
                func_layers.append((i, layer))
                continue
            order = layer.zorder if layer.zorder is not None else (10 + data_idx)
            filtered = LayerSpec(
                geom=layer.geom,
                stat=layer.stat,
                visual_mapping={k: _filter_series(v, rows) for k, v in layer.visual_mapping.items()},
                data_override=layer.data_override,
                zorder=layer.zorder,
                xlim=layer.xlim,
                ylim=layer.ylim,
            )
            snapshot = self._snapshot_artists(ax)
            self._render_layer(ax, spec, filtered, order)
            if layer_affine is not None:
                self._stamp_new_artists(ax, snapshot, layer_affine(filtered), ax.transData)
            if layer.xlim is not None:
                ax.set_xlim(layer.xlim)
            if layer.ylim is not None:
                ax.set_ylim(layer.ylim)
            data_idx += 1

        xlim_data = ax.get_xlim()
        ylim_data = ax.get_ylim()
        ax.autoscale(False)

        for f_idx, (_, layer) in enumerate(func_layers):
            order = layer.zorder if layer.zorder is not None else (1 + f_idx)
            filtered = LayerSpec(
                geom=layer.geom,
                stat=layer.stat,
                visual_mapping={k: _filter_series(v, rows) for k, v in layer.visual_mapping.items() if k != "x"},
                zorder=layer.zorder,
                xlim=layer.xlim,
                ylim=layer.ylim,
            )
            # Keep function lines below data layers (data starts at zorder=10)
            snapshot = self._snapshot_artists(ax)
            self._render_layer(ax, spec, filtered, order)
            if layer_affine is not None:
                self._stamp_new_artists(ax, snapshot, layer_affine(filtered), ax.transData)

        ax.set_xlim(xlim_data)
        ax.set_ylim(ylim_data)

    @staticmethod
    def _snapshot_artists(ax):
        return {name: len(getattr(ax, name)) for name in _ARTIST_CONTAINERS}

    @classmethod
    def _new_artists(cls, ax, snapshot):
        new_artists = []
        for name in _ARTIST_CONTAINERS:
            container = getattr(ax, name)
            new_artists.extend(container[snapshot[name]:])
        return new_artists

    @staticmethod
    def _stamp_new_artists(ax, snapshot, affine, base_transform):
        """Attach affine+base to artists created since *snapshot*.

        For PathCollections (scatter), offsets are pre-transformed through
        the affine and the collection keeps IdentityTransform (the default
        set by ax.scatter). This prevents the marker path vertices from
        being scaled by the data→display transform, which would stretch
        markers to fill the axes.
        """
        if affine is None:
            return
        stacked = affine + base_transform
        for artist in MatplotlibRenderer._new_artists(ax, snapshot):
            if (isinstance(artist, matplotlib.collections.PathCollection)
                    and len(artist.get_offsets()) == 0):
                artist.remove()
                continue
            if isinstance(artist, matplotlib.collections.PathCollection):
                offsets = artist.get_offsets()
                artist.set_offsets(affine.transform(offsets))
                artist.set_transform(IdentityTransform())
            else:
                artist.set_transform(stacked)

    # ------------------------------------------------------------------
    # Children axes (Phase 14.51): nested FigureSpecs with implied frames
    # ------------------------------------------------------------------

    def _render_children(self, spec: FigureSpec):
        if not isinstance(spec.facet, FacetNull):
            raise NotImplementedError("Children axes do not support facets yet")

        figsize = spec.settings.get("figsize", (10, 6))
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_facecolor("none")
        if not spec.children:
            raise ValueError("FigureSpec must define at least one child")

        transformed_children = []
        for child in spec.children:
            child = self._apply_child_coord_transforms(child)
            transformed_children.append(child)
            affine = _affine_from_matrix(child.transform.matrix())

            # Draw frame first (below data): line geometry in local space,
            # stamped with the child's affine. Text labels placed world-side.
            snapshot = self._snapshot_artists(ax)
            self._draw_frame(ax, child)
            for artist in self._new_artists(ax, snapshot):
                if not isinstance(artist, matplotlib.text.Text):
                    artist.set_transform(affine + ax.transData)

            self._render_axes(ax, child, child.data, layer_affine=lambda layer, a=affine: a)

        xlim, ylim = self._children_world_limits(transformed_children)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_aspect("equal")

        title = spec.settings.get("title")
        if title:
            _axis = parse_axis_settings(spec.settings, spec.coord)
            fig.suptitle(title, fontsize=_axis.resolve_fontsize("suptitle"), y=0.98)
        ax.axis("off")

        plt.close(fig)
        return fig

    def _draw_frame(self, ax, spec: FigureSpec, matrix=None):
        """Draw the frame for *spec*, stamped by *matrix*.

        *matrix* maps the spec's local space into world display space. When
        ``None`` (or for a top-level spec), it defaults to ``spec.transform``
        and finally the identity, so local = world.

        This is the single frame-drawing entry used by BOTH the top-level path
        and the child path. It dispatches on the spec's coord type to the
        per-coordinate drawers, all consuming the shared formatted
        :class:`~geofig_engine.core.axis.AxisFormat` — the "same function calls
        + same formatting spec" core of the unified pipeline.
        """
        if matrix is None:
            matrix = spec.transform.matrix()
        matrix = matrix if matrix is not None else np.eye(3)
        axis = parse_axis_settings(spec.settings, spec.coord)
        if isinstance(spec.coord, TernaryCoord):
            _draw_ternary_frame(ax, axis, matrix, spec.coord)
        elif (
            isinstance(spec.coord, CoordCartesian)
            and axis.xlim is not None
            and axis.ylim is not None
        ):
            axis = _with_flat_secondary(axis, spec.settings)
            _draw_cartesian_axis(ax, axis, matrix)
        elif isinstance(spec.coord, CoordPolar):
            self._draw_polar_frame(ax, axis, spec)

    def _apply_child_coord_transforms(self, child: FigureSpec) -> FigureSpec:
        """Apply each child's coord (and secondary-axis channels) to its layers."""
        if not child.layers:
            return child
        secondary = parse_secondary_settings(child.settings)
        trans_layers = []
        for layer in child.layers:
            vm = child.coord.transform_visual_mapping(dict(layer.visual_mapping), layer.geom)
            vm = self._remap_secondary_channels(vm, secondary)
            trans_layers.append(
                LayerSpec(
                    geom=layer.geom,
                    stat=layer.stat,
                    visual_mapping=vm,
                    data_override=layer.data_override,
                    zorder=layer.zorder,
                    xlim=layer.xlim,
                    ylim=layer.ylim,
                )
            )
        return dataclasses.replace(child, layers=trans_layers)

    @staticmethod
    def _remap_secondary_channels(vm: dict, secondary: dict) -> dict:
        """Rewrite secondary-axis channels into local x/y.

        ``x2``/``y2`` values are interpreted in the child's secondary-axis
        units and mapped through the matching secondary-axis linear transform
        into the local-frame ``x``/``y`` coordinates (then the ``x2``/``y2``
        keys are removed). Requires the child to declare the corresponding
        ``secondary_x``/``secondary_y`` axis; otherwise a clear error is raised.
        """
        vm = dict(vm)
        for src, dst, orient in (("x2", "x", "x"), ("y2", "y", "y")):
            if src not in vm:
                continue
            axis = secondary.get(orient)
            if axis is None:
                raise ValueError(
                    f"visual mapping uses '{src}' but the child declares no "
                    f"'secondary_{orient}' axis; cannot map secondary data"
                )
            series = vm[src]
            if not isinstance(series, pd.Series):
                raise TypeError(
                    f"'{src}' must map to a data column (pd.Series), "
                    f"got {type(series).__name__}"
                )
            vm[dst] = series.map(axis.inv)
            del vm[src]
        return vm

    @staticmethod
    def _children_world_limits(children):
        """World-space bounding box from all children's transforms + data."""
        xs: list[np.ndarray] = []
        ys: list[np.ndarray] = []

        for child in children:
            matrix = child.transform.matrix()
            rows = child.data.index
            for layer in child.layers:
                if layer.geom.name == "function_line":
                    continue
                vm = layer.visual_mapping
                x = _filter_series(vm.get("x"), rows)
                y = _filter_series(vm.get("y"), rows)
                if not isinstance(x, pd.Series):
                    x = _filter_series(vm.get("x2"), rows)
                    if isinstance(x, pd.Series):
                        sec = parse_secondary_settings(child.settings).get("x")
                        if sec is not None:
                            x = x.map(sec.inv)
                if not isinstance(y, pd.Series):
                    y = _filter_series(vm.get("y2"), rows)
                    if isinstance(y, pd.Series):
                        sec = parse_secondary_settings(child.settings).get("y")
                        if sec is not None:
                            y = y.map(sec.inv)
                if not isinstance(x, pd.Series) or not isinstance(y, pd.Series):
                    continue
                if not (pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y)):
                    continue
                n = min(len(x), len(y))
                if n == 0:
                    continue
                pts = np.column_stack([x.to_numpy()[:n], y.to_numpy()[:n]])
                world = _apply_matrix_pts(matrix, pts)
                xs.append(world[:, 0])
                ys.append(world[:, 1])

            corners = child.transform.transform_points(
                _child_local_bbox(child)
            )
            xs.append(corners[:, 0])
            ys.append(corners[:, 1])

        if not xs:
            return (-1.0, 1.0), (-1.0, 1.0)

        all_x = np.concatenate(xs)
        all_y = np.concatenate(ys)
        pad_x = 0.05 * (all_x.max() - all_x.min() or 1.0)
        pad_y = 0.05 * (all_y.max() - all_y.min() or 1.0)
        return (
            (float(all_x.min() - pad_x), float(all_x.max() + pad_x)),
            (float(all_y.min() - pad_y), float(all_y.max() + pad_y)),
        )

    @staticmethod
    def _channel_label(spec: FigureSpec, channel: str) -> str | None:
        for layer in spec.layers:
            if layer.geom.name == "function_line":
                continue
            s = layer.visual_mapping.get(channel)
            if s is not None and hasattr(s, "name") and isinstance(s.name, str) and s.name:
                return s.name
        return None

    def _apply_settings(self, ax, fig, spec):
        """Apply global settings to a single Axes, via AxisFormat."""
        axis = parse_axis_settings(spec.settings, spec.coord)
        self._apply_axis_format_native(ax, fig, spec, axis)

    def _apply_axis_format_native(self, ax, fig, spec, axis: AxisFormat):
        """Apply an :class:`AxisFormat` to a native (non-stamped) Axes.

        Reads the same shared formatting model the unified frame pipeline uses
        (title/labels/limits/scales/grid/time_format), so the native single path
        and the faceted panel path consume the exact same :class:`AxisFormat`
        as the affine-stamped child frames (which use :meth:`_draw_frame`).
        Facet panels are native subplot axes, so this thin native adapter emits
        plain matplotlib mutators rather than stamped custom-frame artists.
        """
        coord = spec.coord
        if axis.title:
            ax.set_title(axis.title, fontsize=axis.resolve_fontsize("title"))
        xlabel = axis.xlabel if axis.xlabel is not None else self._channel_label(spec, "x")
        ylabel = axis.ylabel if axis.ylabel is not None else self._channel_label(spec, "y")
        if isinstance(coord, CoordFlipped):
            if ylabel:
                ax.set_xlabel(ylabel, fontsize=axis.resolve_fontsize("xlabel"))
            if xlabel:
                ax.set_ylabel(xlabel, fontsize=axis.resolve_fontsize("ylabel"))
        else:
            if xlabel:
                ax.set_xlabel(xlabel, fontsize=axis.resolve_fontsize("xlabel"))
            if ylabel:
                ax.set_ylabel(ylabel, fontsize=axis.resolve_fontsize("ylabel"))
        xlim = axis.xlim
        ylim = axis.ylim
        if isinstance(coord, CoordFlipped):
            if ylim:
                ax.set_xlim(ylim)
            if xlim:
                ax.set_ylim(xlim)
        else:
            if xlim:
                ax.set_xlim(xlim)
            if ylim:
                ax.set_ylim(ylim)
        xscale = axis.xscale
        yscale = axis.yscale
        if isinstance(coord, CoordFlipped):
            if yscale and yscale != ax.get_xscale():
                ax.set_xscale(yscale)
            if xscale and xscale != ax.get_yscale():
                ax.set_yscale(xscale)
        else:
            if xscale and xscale != ax.get_xscale():
                ax.set_xscale(xscale)
            if yscale and yscale != ax.get_yscale():
                ax.set_yscale(yscale)
        if isinstance(coord, CoordFixed):
            ax.set_aspect(coord.params.get("ratio", 1.0))
        if axis.grid is not None:
            if axis.grid:
                ax.grid(True, zorder=0)
            else:
                ax.grid(False)
        if axis.time_format:
            ax.xaxis.set_major_formatter(DateFormatter(axis.time_format))
        figname = spec.settings.get("figname")
        if figname:
            fig.figname = figname

    @staticmethod
    def _apply_polar_ticks(ax, spec):
        for layer in spec.layers:
            x = layer.visual_mapping.get("x")
            labels = layer.visual_mapping.get("label")
            if x is not None and labels is not None and isinstance(labels, pd.Series):
                df = pd.DataFrame({"x": x.values, "label": labels.values})
                unique = df.drop_duplicates(subset="x").sort_values("x")
                ax.set_xticks(unique["x"].values)
                ax.set_xticklabels(unique["label"].values)
                return

    def _draw_polar_frame(self, ax, axis: AxisFormat, spec):
        """Apply AxisFormat-driven polar frame formatting to a polar Axes.

        Pie/radar render sectors/lines through matplotlib's native polar
        projection on *ax* (that projection is the only way sectors/radar lines
        are drawn), so this drives the tick/grid/label formatting from the
        shared :class:`~geofig_engine.core.axis.AxisFormat` + its polar
        ``options``. Option semantics match the legacy flat-key behavior, so
        both a top-level polar spec and a polar child route here through the
        unified ``_draw_frame`` entry with identical results.

        Angular tick positions/labels come from the layer's x/label mapping via
        :meth:`_apply_polar_ticks`; the radial threshold grid is per
        ``axis.grid`` / ``axis.grid_style`` / ``axis.grid_step``.
        """
        options = axis.options

        # Radial grid toggled from the common axis spec (native polar grid).
        if axis.grid is not None:
            if axis.grid:
                ax.grid(True, zorder=0)
            else:
                ax.grid(False)

        if options.get("hide_spine", False):
            ax.spines["polar"].set_visible(False)
        if options.get("hide_angular_ticks", False):
            ax.tick_params(axis="x", length=0)
        if options.get("hide_angular_labels", False):
            ax.set_xticklabels([])
        if options.get("hide_radial_labels", False):
            ax.set_yticklabels([])
        if options.get("hide_radial_ticks", False):
            ax.set_yticks([])
        if options.get("polar_tick_labels", False):
            self._apply_polar_ticks(ax, spec)
            try:
                ax.tick_params(labelsize=axis.resolve_fontsize("tick"))
            except TypeError:
                pass

        # -- radial axis direction arrow (opt-in) --
        # Polar has no local-space affine stamp (native theta/r data space), so
        # call the shared helper with an identity matrix: annotate in data coords
        # along a chosen reference ray (north, theta = pi/2), pointing outward
        # (ascending radius r).
        if axis.show_arrows():
            r_lo, r_hi = ax.get_ylim()
            if r_hi - r_lo > 1e-9:
                theta0 = math.pi / 2.0
                # ``axis_arrow_offset`` adds radial inset (fraction of range) to
                # the arrow's endpoints along the ray, defaulting to no change.
                k = axis.axis_arrow_offset if axis.axis_arrow_offset is not None else 0.0
                _draw_axis_arrow(
                    ax, np.eye(3),
                    (theta0, r_lo + (0.10 + k) * (r_hi - r_lo)),
                    (theta0, r_hi * max(0.0, 0.92 - k)),
                    (0.0, 1.0), lw=axis.frame_linewidth,
                )

    # ------------------------------------------------------------------
    # Stiff diagram (single-sample 6-axis polygon)
    # ------------------------------------------------------------------

    def _render_stiff(self, spec: FigureSpec):
        coord = spec.coord
        figsize = spec.settings.get("figsize", (6, 6))
        fig, ax = plt.subplots(figsize=figsize)

        max_val = coord.params.get("max_val", 1.0)
        scale = max_val * 1.3 if max_val > 0 else 1.0
        tick_max = _nice_tick_max(max_val)
        scale_extent = tick_max / scale

        self._draw_stiff_frame(ax, coord, scale, scale_extent)
        self._draw_stiff_scale(ax, scale, tick_max, scale_extent)

        spec = self._apply_coord_transform(spec)
        self._render_axes(ax, spec, spec.data)

        sample_title = coord.params.get("sample_title", "")
        if sample_title:
            ax.set_title(sample_title, fontsize=12, fontweight="bold", pad=10)

        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-0.55, 2.5)
        ax.set_aspect("equal")
        ax.axis("off")

        plt.close(fig)
        return fig

    @staticmethod
    def _draw_stiff_frame(ax, coord, scale, scale_extent):
        params = coord.params
        ca = params.get("ca", 0)
        mg = params.get("mg", 0)
        na_k = params.get("na_k", 0)
        cl = params.get("cl", 0)
        hco3 = params.get("hco3", 0)
        so4 = params.get("so4", 0)

        left_vals = [na_k, ca, mg]
        right_vals = [cl, hco3, so4]
        labels_left = ["Na\u207a+K\u207a", "Ca\u00b2\u207a", "Mg\u00b2\u207a"]
        labels_right = ["Cl\u207b", "HCO\u2083\u207b", "SO\u2084\u00b2\u207b"]
        y_positions = [2, 1, 0]

        for v, y, lbl in zip(left_vals, y_positions, labels_left):
            ax.plot([-v / scale, -scale_extent], [y, y], color="black", linewidth=0.5, zorder=1)
            ax.text(-scale_extent - 0.03, y, lbl, ha="right", va="center", fontsize=10, fontweight="bold")

        for v, y, lbl in zip(right_vals, y_positions, labels_right):
            ax.plot([v / scale, scale_extent], [y, y], color="black", linewidth=0.5, zorder=1)
            ax.text(scale_extent + 0.03, y, lbl, ha="left", va="center", fontsize=10, fontweight="bold")

        ax.plot([0, 0], [0, 2.1], color="black", linewidth=1.0, linestyle="dashed", zorder=11)
        ax.plot([-0.5, 0.5], [1, 1], color="black", linewidth=1.0, zorder=11)

    @staticmethod
    def _draw_stiff_scale(ax, scale, tick_max, scale_extent):
        y_line = -0.18
        steps = [-tick_max, -tick_max / 2, 0, tick_max / 2, tick_max]

        ax.plot([-scale_extent, scale_extent], [y_line, y_line],
                color="black", linewidth=0.8, zorder=1)

        for t in steps:
            x = t / scale
            ax.plot([x, x], [y_line, y_line - 0.06], color="black", linewidth=0.5, zorder=1)
            label = f"{t:g}" if t != 0 else "0"
            ax.text(x, y_line - 0.1, label, ha="center", va="top", fontsize=7)

        ax.text(0, y_line - 0.22, "meq/L", ha="center", va="top", fontsize=7, color="gray")

    # ------------------------------------------------------------------
    # Faceted (multi-panel)
    # ------------------------------------------------------------------

    def _render_faceted(self, spec: FigureSpec):
        spec = self._apply_coord_transform(spec)
        figsize = spec.settings.get("figsize", (10, 6))
        facet = spec.facet
        data = spec.data
        panels = _facet_panels(facet, data)

        if not panels:
            raise ValueError("Facet produced zero panels")

        if isinstance(facet, FacetWrap):
            n = len(panels)
            ncol = facet.params.get("ncol", 0) or min(n, 3)
            nrow = facet.params.get("nrow", 0) or math.ceil(n / ncol)
            layout = (nrow, ncol)
        else:
            row_key = facet.params["row"]
            col_key = facet.params["col"]
            row_vals = sorted(data[row_key].unique())
            col_vals = sorted(data[col_key].unique())
            nrow, ncol = len(row_vals), len(col_vals)
            layout = (nrow, ncol)

            # Build position map for FacetGrid
            row_map = {v: i for i, v in enumerate(row_vals)}
            col_map = {v: ci for ci, v in enumerate(col_vals)}
            grid_panels: list[list[tuple[pd.DataFrame, dict[str, Any]] | None]] = [
                [None] * ncol for _ in range(nrow)
            ]
            for subset, ctx in panels:
                ri = row_map[ctx[row_key]]
                ci = col_map[ctx[col_key]]
                grid_panels[ri][ci] = (subset, ctx)
            panels = grid_panels  # type: ignore[assignment]
            n = nrow * ncol

        # Determine axis sharing based on facet scales
        scales = facet.scales
        sharex = scales in ("fixed", "free_y")
        sharey = scales in ("fixed", "free_x")

        fig, axes = plt.subplots(*layout, figsize=figsize, squeeze=False, sharex=sharex, sharey=sharey)

        # Compute global limits for fixed/partially-fixed scales
        glims = self._compute_facet_limits(spec, panels, scales)

        # One AxisFormat drives every faceted panel (native subplot axes).
        axis = parse_axis_settings(spec.settings, spec.coord)

        if isinstance(facet, FacetWrap):
            axes_flat = axes.flat
            for idx, item in enumerate(panels):
                ax = axes_flat[idx]
                subset, ctx = item
                self._render_axes(ax, spec, subset)
                self._apply_axis_format_native(ax, fig, spec, axis)
                self._apply_facet_panel(ax, ctx, glims, facet.scales)
                ax.set_title(", ".join(f"{k}={v}" for k, v in ctx.items()), fontsize=axis.resolve_fontsize("facet_title"))
            for idx in range(len(panels), len(axes_flat)):
                axes_flat[idx].set_visible(False)
        else:
            for ri in range(nrow):
                for ci in range(ncol):
                    item = panels[ri][ci]
                    ax = axes[ri][ci]
                    if item is None:
                        ax.set_visible(False)
                        continue
                    subset, ctx = item
                    self._render_axes(ax, spec, subset)
                    self._apply_axis_format_native(ax, fig, spec, axis)
                    self._apply_facet_panel(ax, ctx, glims, facet.scales)
                    if ri == 0:
                        ax.set_title(ctx.get(facet.params["col"], ""), fontsize=axis.resolve_fontsize("facet_title"))
                    if ci == 0:
                        ax.set_ylabel(ctx.get(facet.params["row"], ""), fontsize=axis.resolve_fontsize("facet_title"))

        plt.close(fig)
        return fig

    def _compute_facet_limits(self, spec, panels, scales):
        if scales not in ("fixed", "free_x", "free_y"):
            return None

        vals: dict[str, list[pd.Series]] = {"x": [], "y": []}
        for layer in spec.layers:
            if layer.geom.name == "function_line":
                continue

            for chan in ("x", "y"):
                v = layer.visual_mapping.get(chan)
                if v is not None and hasattr(v, "dtype") and pd.api.types.is_numeric_dtype(v):
                    vals[chan].append(v)

        glims: dict[str, tuple[float, float]] = {}
        for chan in ("x", "y"):
            if not vals[chan]:
                continue
            all_v = pd.concat(vals[chan])
            lo, hi = float(all_v.min()), float(all_v.max())
            if lo == hi:
                lo, hi = lo - 1, hi + 1
            else:
                margin = 0.05
                pad = margin * (hi - lo)
                lo, hi = lo - pad, hi + pad
            if scales == "free" or (scales == "free_x" and chan == "y") or (scales == "free_y" and chan == "x"):
                continue
            glims[chan] = (lo, hi)
        return glims or None

    def _apply_facet_panel(self, ax, ctx, glims, scales):
        if glims:
            if "x" in glims:
                ax.set_xlim(glims["x"])
            if "y" in glims:
                ax.set_ylim(glims["y"])

    # ------------------------------------------------------------------
    # Support check
    # ------------------------------------------------------------------

    def supports(self, spec: FigureSpec) -> bool:
        if isinstance(spec.coord, StiffCoord):
            return True
        if spec.template_name in IMPLEMENTED:
            return True
        if spec.layers:
            return all(
                l.geom.name in _GEOM_HANDLERS
                for l in spec.layers
            )
        if spec.children:
            return all(
                l.geom.name in _GEOM_HANDLERS
                for child in spec.children
                for l in child.layers
            )
        return False

    # ------------------------------------------------------------------
    # Legend
    # ------------------------------------------------------------------

    def render_legend(self, legend_data: LegendAccumulator, fontsize: float = 9) -> plt.Figure:
        return render_legend_figure(legend_data, fontsize=fontsize)

    def _apply_coord_transform(self, spec: FigureSpec) -> FigureSpec:
        """Apply coordinate transform to all layers' visual mappings."""
        if not spec.layers:
            return spec
        trans_layers = []
        for layer in spec.layers:
            vm = spec.coord.transform_visual_mapping(dict(layer.visual_mapping), layer.geom)
            trans_layers.append(
                LayerSpec(
                    geom=layer.geom,
                    stat=layer.stat,
                    visual_mapping=vm,
                    data_override=layer.data_override,
                    zorder=layer.zorder,
                    xlim=layer.xlim,
                    ylim=layer.ylim,
                )
            )
        return dataclasses.replace(spec, layers=trans_layers)

    def _render_layer(self, ax, spec, layer, order):
        handler = _GEOM_HANDLERS.get(layer.geom.name)
        if handler is None:
            raise TypeError(f"Unsupported geom: {layer.geom.name}")
        handler(ax, layer, order, coord=spec.coord)