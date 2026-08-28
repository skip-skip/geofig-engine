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


def _child_local_bbox(child):
    """Local-space bounding box corners for a child FigureSpec.

    TernaryCoord → unit triangle; CoordCartesian with settings
    ``xlim``/``ylim`` → that axis region (e.g. the diamond's [0,100]²);
    everything else → unit square.
    """
    coord = child.coord
    if isinstance(coord, TernaryCoord):
        return [(0, 0), (1, 0), (0.5, SQRT3_2), (0, 0)]
    if isinstance(coord, CoordCartesian) and child.settings:
        cfg = child.settings
        if "xlim" in cfg and "ylim" in cfg:
            x0, x1 = cfg["xlim"]
            y0, y1 = cfg["ylim"]
            return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return [(0, 0), (1, 0), (0, 1), (1, 1)]


def _draw_ternary_frame(ax, matrix, coord, settings):
    """Draw ternary triangle frame in local space, stamped by matrix.

    Reads ions from coord.channels, reversals from coord.handedness,
    title from settings.
    """
    cfg = settings or {}
    ions = list(coord.channels)
    handedness = coord.handedness
    title = cfg.get("title", "")
    label_policy = cfg.get("label_policy", "upright")

    rev_bottom = handedness == "left"
    rev_left = handedness == "right"
    rev_right = handedness == "left"

    # -- triangle outline (local space) --
    tri_local = [(0, 0), (1, 0), (0.5, SQRT3_2), (0, 0)]
    tri_arr = np.array(tri_local, dtype=float)
    ax.plot(tri_arr[:, 0], tri_arr[:, 1], color="black", linewidth=1.0, zorder=2)

    # -- internal grid at 20/40/60/80% (local space) --
    for t in [0.2, 0.4, 0.6, 0.8]:
        family1 = [(t, 0), (t * 0.5, t * SQRT3_2)]
        family2 = [(t, 0), ((1 + t) / 2, (1 - t) * SQRT3_2)]
        family3 = [(t * 0.5, t * SQRT3_2), (1 - t * 0.5, t * SQRT3_2)]
        for fam in (family1, family2, family3):
            fam_arr = np.array(fam, dtype=float)
            ax.plot(fam_arr[:, 0], fam_arr[:, 1], color="gray", linewidth=0.3,
                    linestyle=":", zorder=1)

    # -- tick labels at 20/40/60/80% (world-side text) --
    for tick_val in [0.2, 0.4, 0.6, 0.8]:
        tick_str = str(int(tick_val * 100))
        inv = str(100 - int(tick_str))

        bottom_lbl = inv if rev_bottom else tick_str
        left_lbl = inv if rev_left else tick_str
        right_lbl = inv if rev_right else tick_str

        wb = _apply_matrix_pts(matrix, [(tick_val, -0.03)])[0]
        ax.text(wb[0], wb[1], bottom_lbl, ha="center", va="top", fontsize=5,
                rotation=label_rotation((1, 0), matrix, policy=label_policy),
                clip_on=False)

        wl = _apply_matrix_pts(matrix, [(
            tick_val * 0.5 - 0.026, tick_val * SQRT3_2 + 0.015
        )])[0]
        ax.text(wl[0], wl[1], left_lbl, ha="center", va="center", fontsize=5,
                rotation=label_rotation(
                    (0.5, SQRT3_2), matrix, policy=label_policy),
                clip_on=False)

        wr = _apply_matrix_pts(matrix, [(
            1 - tick_val * 0.5 + 0.026, tick_val * SQRT3_2 + 0.015
        )])[0]
        ax.text(wr[0], wr[1], right_lbl, ha="center", va="center", fontsize=5,
                rotation=label_rotation(
                    (-0.5, SQRT3_2), matrix, policy=label_policy),
                clip_on=False)

    # -- edge title (world-side text) --
    if title:
        wt = _apply_matrix_pts(matrix, [(0.5, SQRT3_2 + 0.12)])[0]
        ax.text(wt[0], wt[1], title, ha="center", va="bottom", fontsize=7,
                fontweight="bold", clip_on=False)

    # -- ion edge labels with arrows (world-side annotations) --
    if len(ions) == 3:
        offset = 0.12
        cos30 = SQRT3_2
        mid_left = (0.25 - offset * cos30, SQRT3_2 / 2.0 + offset * 0.5)
        mid_base = (0.5, -offset)
        mid_right = (0.75 + offset * cos30, SQRT3_2 / 2.0 + offset * 0.5)

        def _arrow(x, y, text, rotation=0, reverse=False):
            length = 0.5
            angle_rad = math.radians(rotation)
            dx = (length / 2) * math.cos(angle_rad)
            dy = (length / 2) * math.sin(angle_rad)
            style = '-|>' if reverse else '<|-'
            wxy = _apply_matrix_pts(matrix, [(x + dx, y + dy)])[0]
            wxyt = _apply_matrix_pts(matrix, [(x - dx, y - dy)])[0]
            ax.annotate('', xy=wxy, xytext=wxyt,
                        arrowprops=dict(arrowstyle=style, color='black', lw=1.0),
                        annotation_clip=False)
            wpt = _apply_matrix_pts(matrix, [(x, y)])[0]
            rot = label_rotation((1, 0), matrix, policy=label_policy)
            ax.text(wpt[0], wpt[1], text, ha='center', va='center',
                    rotation=rot, fontsize=7,
                    bbox=dict(facecolor='white', edgecolor='none', pad=1),
                    clip_on=False)

        _arrow(*mid_left, ions[1], rotation=60, reverse=rev_left)
        _arrow(*mid_base, ions[0], rotation=0, reverse=rev_bottom)
        _arrow(*mid_right, ions[2], rotation=-60, reverse=rev_right)


def _draw_cartesian_axis(ax, matrix, settings):
    """Draw a cartesian axis frame in local space, stamped by *matrix*.

    Reads the axis region and styling from ``settings``:
      - ``xlim``/``ylim``: axis bounds in local space (default ``(0, 1)²``)
      - ``grid_step``: gridline spacing in both directions (default 0.2)
      - ``tick_step``: tick label spacing (default = grid_step)
      - ``label_policy``: "upright" or "parallel" (default "upright")
      - ``title``: world-side label above the box
      - ``secondary_x``/``secondary_y``: optional dicts declaring extra scales
        drawn along the top (secondary x) and right (secondary y) edges, mapped
        linearly onto the primary ``xlim``/``ylim`` ranges (see
        :mod:`geofig_engine.core.secondary_axis`).

    All geometry (box + gridlines) is drawn in local space and later stamped
    with the child's affine, exactly like data. Tick labels and title are
    placed world-side via ``_apply_matrix_pts`` so they stay upright. This
    generalizes the Piper diamond (a cartesian child in ``[0,100]²`` rotated
    45°) as well as any rotated/translated cartesian child that opts into a
    frame by supplying the ``xlim``/``ylim`` bounds in settings.
    """
    cfg = settings or {}
    xlim = cfg.get("xlim", (0.0, 1.0))
    ylim = cfg.get("ylim", (0.0, 1.0))
    grid_step = cfg.get("grid_step", 0.2)
    tick_step = cfg.get("tick_step", grid_step)
    label_policy = cfg.get("label_policy", "upright")
    title = cfg.get("title", "")

    secondary = parse_secondary_settings(cfg)

    x0, x1 = xlim
    y0, y1 = ylim

    # -- outline (local space) --
    box = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    box_arr = np.array(box, dtype=float)
    ax.plot(box_arr[:, 0], box_arr[:, 1], color="black", linewidth=1.0, zorder=2)

    # -- internal grid (local space) --
    xs = list(np.arange(x0 + grid_step, x1, grid_step))
    ys = list(np.arange(y0 + grid_step, y1, grid_step))
    for gx in xs:
        g = [(gx, y0), (gx, y1)]
        ax.plot([g[0][0], g[1][0]], [g[0][1], g[1][1]], color="gray",
                linewidth=0.3, linestyle=":", zorder=1)
    for gy in ys:
        ax.plot([x0, x1], [gy, gy], color="gray", linewidth=0.3,
                linestyle=":", zorder=1)

    # -- tick labels on bottom edge (world-side text) --
    # X-axis ticks at tick_step along the bottom (y0) edge, interior only.
    d = 1.0 if x1 - x0 == 1.0 else (x1 - x0) / 20.0
    for tx in np.arange(x0, x1 + 0.5 * tick_step, tick_step):
        if x0 - 1e-9 <= tx <= x0 + 1e-9 or x1 - 1e-9 <= tx <= x1 + 1e-9:
            continue
        w = _apply_matrix_pts(matrix, [(tx, y0 - d)])[0]
        ax.text(w[0], w[1], f"{tx:g}", ha="center", va="top", fontsize=5,
                rotation=label_rotation((1, 0), matrix, policy=label_policy),
                clip_on=False)

    # -- tick labels on left edge (world-side text) --
    for ty in np.arange(y0, y1 + 0.5 * tick_step, tick_step):
        if y0 - 1e-9 <= ty <= y0 + 1e-9 or y1 - 1e-9 <= ty <= y1 + 1e-9:
            continue
        w = _apply_matrix_pts(matrix, [(x0 - d, ty)])[0]
        ax.text(w[0], w[1], f"{ty:g}", ha="right", va="center", fontsize=5,
                rotation=label_rotation((0, 1), matrix, policy=label_policy),
                clip_on=False)

    # -- tick labels on top edge from secondary x (world-side text) --
    if "x" in secondary:
        axis = secondary["x"]
        for sv, lx in axis.tick_coordinates():
            if x0 - 1e-9 <= lx <= x0 + 1e-9 or x1 - 1e-9 <= lx <= x1 + 1e-9:
                continue
            w = _apply_matrix_pts(matrix, [(lx, y1 + d)])[0]
            ax.text(w[0], w[1], f"{sv:g}", ha="center", va="bottom", fontsize=5,
                    rotation=label_rotation((1, 0), matrix, policy=axis.label_policy),
                    clip_on=False)

    # -- tick labels on right edge from secondary y (world-side text) --
    if "y" in secondary:
        axis = secondary["y"]
        for sv, ly in axis.tick_coordinates():
            if y0 - 1e-9 <= ly <= y0 + 1e-9 or y1 - 1e-9 <= ly <= y1 + 1e-9:
                continue
            w = _apply_matrix_pts(matrix, [(x1 + d, ly)])[0]
            ax.text(w[0], w[1], f"{sv:g}", ha="left", va="center", fontsize=5,
                    rotation=label_rotation((0, 1), matrix, policy=axis.label_policy),
                    clip_on=False)

    # -- secondary axis titles (world-side text, beyond the tick labels) --
    if "x" in secondary and secondary["x"].label:
        axis = secondary["x"]
        wt = _apply_matrix_pts(matrix, [((x0 + x1) / 2.0, y1 + 0.20 * (y1 - y0))])[0]
        ax.text(wt[0], wt[1], axis.label, ha="center", va="bottom", fontsize=6,
                rotation=label_rotation((1, 0), matrix, policy=axis.label_policy),
                clip_on=False)
    if "y" in secondary and secondary["y"].label:
        axis = secondary["y"]
        wt = _apply_matrix_pts(matrix, [(x1 + 0.20 * (x1 - x0), (y0 + y1) / 2.0)])[0]
        ax.text(wt[0], wt[1], axis.label, ha="left", va="center", fontsize=6,
                rotation=label_rotation((0, 1), matrix, policy=axis.label_policy),
                clip_on=False)

    # -- edge title (world-side text) --
    if title:
        wt = _apply_matrix_pts(matrix, [((x0 + x1) / 2.0, y1 + 0.12 * (y1 - y0))])[0]
        ax.text(wt[0], wt[1], title, ha="center", va="bottom", fontsize=7,
                fontweight="bold", clip_on=False)


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

        return self._render_single(spec)

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

        for child in spec.children:
            child = self._apply_child_coord_transforms(child)
            affine = _affine_from_matrix(child.transform.matrix())

            # Draw frame first (below data): line geometry in local space,
            # stamped with the child's affine. Text labels placed world-side.
            snapshot = self._snapshot_artists(ax)
            self._draw_implied_frame(ax, child)
            for artist in self._new_artists(ax, snapshot):
                if not isinstance(artist, matplotlib.text.Text):
                    artist.set_transform(affine + ax.transData)

            self._render_axes(ax, child, child.data, layer_affine=lambda layer, a=affine: a)

        xlim, ylim = self._children_world_limits(spec.children)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_aspect("equal")

        title = spec.settings.get("title")
        if title:
            fig.suptitle(title, fontsize=14, y=0.98)
        ax.axis("off")

        plt.close(fig)
        return fig

    @staticmethod
    def _draw_implied_frame(ax, child: FigureSpec):
        """Draw frame auto-selected from child's coord type + settings."""
        matrix = child.transform.matrix()
        if isinstance(child.coord, TernaryCoord):
            _draw_ternary_frame(ax, matrix, child.coord, child.settings)
        elif (
            isinstance(child.coord, CoordCartesian)
            and "xlim" in child.settings
            and "ylim" in child.settings
        ):
            _draw_cartesian_axis(ax, matrix, child.settings)

    def _apply_child_coord_transforms(self, child: FigureSpec) -> FigureSpec:
        """Apply each child's coord to its own layers' visual mappings."""
        if not child.layers:
            return child
        trans_layers = []
        for layer in child.layers:
            vm = child.coord.transform_visual_mapping(dict(layer.visual_mapping), layer.geom)
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
                x = _filter_series(layer.visual_mapping.get("x"), rows)
                y = _filter_series(layer.visual_mapping.get("y"), rows)
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
        """Apply global settings to a single Axes."""
        coord = spec.coord
        title = spec.settings.get("title")
        if title:
            ax.set_title(title)
        xlabel = spec.settings.get("xlabel")
        if xlabel is None:
            xlabel = self._channel_label(spec, "x")
        ylabel = spec.settings.get("ylabel")
        if ylabel is None:
            ylabel = self._channel_label(spec, "y")
        if isinstance(coord, CoordFlipped):
            if ylabel:
                ax.set_xlabel(ylabel)
            if xlabel:
                ax.set_ylabel(xlabel)
        else:
            if xlabel:
                ax.set_xlabel(xlabel)
            if ylabel:
                ax.set_ylabel(ylabel)
        xlim = spec.settings.get("xlim")
        ylim = spec.settings.get("ylim")
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
        xscale = spec.settings.get("xscale")
        yscale = spec.settings.get("yscale")
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
        if "grid" in spec.settings:
            if spec.settings["grid"]:
                ax.grid(True, zorder=0)
            else:
                ax.grid(False)
        if isinstance(coord, CoordPolar):
            if spec.settings.get("hide_spine", False):
                ax.spines['polar'].set_visible(False)
            if spec.settings.get("hide_angular_ticks", False):
                ax.tick_params(axis='x', length=0)
            if spec.settings.get("hide_angular_labels", False):
                ax.set_xticklabels([])
            if spec.settings.get("hide_radial_labels", False):
                ax.set_yticklabels([])
            if spec.settings.get("hide_radial_ticks", False):
                ax.set_yticks([])
            if spec.settings.get("polar_tick_labels", False):
                self._apply_polar_ticks(ax, spec)
        time_format = spec.settings.get("time_format")
        if time_format:
            ax.xaxis.set_major_formatter(DateFormatter(time_format))
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

        if isinstance(facet, FacetWrap):
            axes_flat = axes.flat
            for idx, item in enumerate(panels):
                ax = axes_flat[idx]
                subset, ctx = item
                self._render_axes(ax, spec, subset)
                self._apply_settings(ax, fig, spec)
                self._apply_facet_panel(ax, ctx, glims, facet.scales)
                ax.set_title(", ".join(f"{k}={v}" for k, v in ctx.items()), fontsize=10)
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
                    self._apply_settings(ax, fig, spec)
                    self._apply_facet_panel(ax, ctx, glims, facet.scales)
                    if ri == 0:
                        ax.set_title(ctx.get(facet.params["col"], ""), fontsize=10)
                    if ci == 0:
                        ax.set_ylabel(ctx.get(facet.params["row"], ""), fontsize=10)

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

    def render_legend(self, legend_data: LegendAccumulator) -> plt.Figure:
        return render_legend_figure(legend_data)

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