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

from matplotlib.gridspec import GridSpec

from matplotlib.patches import Polygon

from geofig_engine.core.coord import CoordFlipped, CoordFixed, CoordPolar, PiperCoord, StiffCoord
from geofig_engine.core.facet import FacetGrid, FacetNull, FacetWrap
from geofig_engine.core.layer import LayerSpec
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


class MatplotlibRenderer(BaseRenderer):
    """Matplotlib backend for rendering FigEngine FigureSpec objects."""

    def render(self, spec: FigureSpec):
        if self.supports(spec) is False:
            raise NotImplementedError(f"MatplotlibRenderer does not currently support template '{spec.template_name}'")

        if isinstance(spec.coord, PiperCoord):
            return self._render_piper(spec)
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

    def _render_axes(self, ax, spec, data):
        """Render all layers onto a single Axes, filtered to *data* rows."""
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
                coord=spec.coord,
                zorder=layer.zorder,
                subplot=layer.subplot,
                xlim=layer.xlim,
                ylim=layer.ylim,
            )
            self._render_layer(ax, spec, filtered, order)
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
                coord=spec.coord,
                zorder=layer.zorder,
                subplot=layer.subplot,
                xlim=layer.xlim,
                ylim=layer.ylim,
            )
            # Keep function lines below data layers (data starts at zorder=10)
            self._render_layer(ax, spec, filtered, order)

        ax.set_xlim(xlim_data)
        ax.set_ylim(ylim_data)

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
    # Piper diagram (3-panel: left triangle, right triangle, diamond)
    #
    # Frame decorations (boundaries, grid lines, labels) are drawn
    # directly. Data layers are dispatched by subplot through _render_axes
    # using standard GoG geometries (GeomPoint, GeomText, GeomAbline,
    # GeomRect, etc.) — all compatible with the Piper coordinate space.
    # ------------------------------------------------------------------

    def _render_piper(self, spec: FigureSpec):
        coord = spec.coord
        params = coord.params
        left_tri = params["left_tri"]
        right_tri = params["right_tri"]
        figsize = spec.settings.get("figsize", (10, 8))

        fig = plt.figure(figsize=figsize)
        # [left, bottom, width, height] in figure coordinates
        ax_dia = fig.add_axes([0.2, 0.28, 0.6, 0.6], zorder=2)
        ax_cat = fig.add_axes([0.07, -0.05, 0.525, 0.7875], zorder=1)
        ax_an = fig.add_axes([0.4, -0.05, 0.525, 0.7875], zorder=1)

        self._draw_ternary_frame(ax_cat, left_tri[1], left_tri[2], left_tri[0], "LEFT TRIANGLE", reverse_bottom=True, reverse_right=True)
        self._draw_ternary_frame(ax_an, right_tri[1], right_tri[2], right_tri[0], "RIGHT TRIANGLE", reverse_left=True)
        self._draw_diamond_frame(ax_dia)

        sx = math.sqrt(3) / 2.0
        self._draw_ternary_edge_labels(ax_cat, left_tri[1], left_tri[0], left_tri[2],
                                        rev_right=True)
        self._draw_ternary_edge_labels(ax_an, right_tri[0], right_tri[2], right_tri[1],
                                        rev_left=False, rev_base=True)
        fig.text(0.5, 0.01, "% meq/kg", ha="center", va="bottom", fontsize=12)

        axes_map = {"left_tri": ax_cat, "right_tri": ax_an, "diamond": ax_dia}
        for subplot_name, ax in axes_map.items():
            sub_layers = [l for l in spec.layers if l.subplot == subplot_name]
            if sub_layers:
                sub_spec = dataclasses.replace(spec, layers=sub_layers)
                rows = spec.data.index
                for layer in sub_layers:
                    order = layer.zorder if layer.zorder is not None else 10
                    filtered = LayerSpec(
                        geom=layer.geom,
                        stat=layer.stat,
                        visual_mapping={k: _filter_series(v, rows) for k, v in layer.visual_mapping.items()},
                        coord=spec.coord,
                        zorder=layer.zorder,
                    )
                    self._render_layer(ax, sub_spec, filtered, order)

        title = spec.settings.get("title", "Piper Diagram")
        fig.suptitle(title, fontsize=14, y=0.98)

        plt.close(fig)
        return fig

    @staticmethod
    def _draw_ternary_frame(ax, label_top, label_right, label_left, title, reverse_bottom=False, reverse_left=False, reverse_right=False):
        sx = math.sqrt(3) / 2.0
        tri = Polygon([(0, 0), (1, 0), (0.5, sx)], fill=False, edgecolor="black", linewidth=1.0)
        ax.add_patch(tri)

        for tick_val in [0.2, 0.4, 0.6, 0.8]:
            pts = [(tick_val, 0), (tick_val * 0.5, tick_val * sx)]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color="gray", linewidth=0.3, linestyle=":")
            pts = [(tick_val, 0), ((1 + tick_val) / 2, (1 - tick_val) * sx)]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color="gray", linewidth=0.3, linestyle=":")
            pts = [(tick_val * 0.5, tick_val * sx), (1 - tick_val * 0.5, tick_val * sx)]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color="gray", linewidth=0.3, linestyle=":")

        for tick_val, tick_label in [(0.2, "20"), (0.4, "40"), (0.6, "60"), (0.8, "80")]:
            bottom_label = str(100 - int(tick_label)) if reverse_bottom else tick_label
            left_label = str(100 - int(tick_label)) if reverse_left else tick_label
            right_label = str(100 - int(tick_label)) if reverse_right else tick_label
            ax.text(tick_val, -0.03, bottom_label, ha="center", va="top", fontsize=5)
            ax.text(tick_val * 0.5 - 0.026, tick_val * sx + 0.015, left_label,
                    ha="center", va="center", fontsize=5, rotation=60)
            ax.text(1 - tick_val * 0.5 + 0.026, tick_val * sx + 0.015, right_label,
                    ha="center", va="center", fontsize=5, rotation=-60)


        ax.set_xlim(-0.5, 1.5)
        ax.set_ylim(-0.5, 1.332)
        ax.set_aspect("equal")
        ax.axis("off")

    @staticmethod
    def _draw_ternary_edge_labels(ax, label_left, label_base, label_right,
                                    rev_left=True, rev_base=False, rev_right=False):
        sx = math.sqrt(3) / 2.0
        offset = 0.12
        cos30 = math.sqrt(3) / 2.0
        mid_left = (0.25 - offset * cos30, sx / 2.0 + offset * 0.5)
        mid_base = (0.5, -offset)
        mid_right = (0.75 + offset * cos30, sx / 2.0 + offset * 0.5)

        def _arrow(x, y, text, rotation=0, reverse=False):
            length = 0.5
            angle_rad = math.radians(rotation)
            dx = (length / 2) * math.cos(angle_rad)
            dy = (length / 2) * math.sin(angle_rad)
            style = '-|>' if reverse else '<|-'
            ax.annotate('', xy=(x + dx, y + dy), xytext=(x - dx, y - dy),
                        arrowprops=dict(arrowstyle=style, color='black', lw=1.0),
                        annotation_clip=False)
            ax.text(x, y, text, ha='center', va='center', rotation=rotation,
                    fontsize=7, bbox=dict(facecolor='white', edgecolor='none', pad=1))

        _arrow(*mid_left, label_left, rotation=60, reverse=rev_left)
        _arrow(*mid_base, label_base, rotation=0, reverse=rev_base)
        _arrow(*mid_right, label_right, rotation=-60, reverse=rev_right)

    @staticmethod
    def _draw_diamond_frame(ax):
        sx = math.sqrt(3) / 2.0
        dia = Polygon([(0, sx), (0.5, 0), (0, -sx), (-0.5, 0)], fill=False,
                      edgecolor="black", linewidth=1.0)
        ax.add_patch(dia)

        for t in [0.2, 0.4, 0.6, 0.8]:
            # Family 1: upper-right edge → lower-left edge
            x1 = t / 2.0
            y1 = sx * (1 - t)
            x2 = -(1 - t) / 2.0
            y2 = -t * sx
            ax.plot([x1, x2], [y1, y2], color="gray", linewidth=0.3, linestyle=":")

            # Family 2: upper-left edge → lower-right edge
            x3 = -(1 - t) / 2.0
            y3 = t * sx
            x4 = t / 2.0
            y4 = -sx * (1 - t)
            ax.plot([x3, x4], [y3, y4], color="gray", linewidth=0.3, linestyle=":")

        for t in [0.2, 0.4, 0.6, 0.8]:
            label = f"{t * 100:.0f}"
            rlabel = f"{(1 - t) * 100:.0f}"
            d = 0.03
            # Family 1: upper-right edge → lower-left edge
            ax.text(t / 2.0 + d, sx * (1 - t) + d * 0.4, rlabel,
                    ha="center", va="bottom", fontsize=5, rotation=-60)
            ax.text(-(1 - t) / 2.0 - d, -t * sx - d * 0.4, label,
                    ha="center", va="top", fontsize=5, rotation=-60)
            # Family 2: upper-left edge → lower-right edge
            ax.text(-(1 - t) / 2.0 - d, t * sx + d * 0.4, label,
                    ha="center", va="bottom", fontsize=5, rotation=60)
            ax.text(t / 2.0 + d, -sx * (1 - t) - d * 0.4, rlabel,
                    ha="center", va="top", fontsize=5, rotation=60)

        def _arrow(x, y, text, rotation=0, reverse=False):
            length = 0.4
            angle_rad = math.radians(rotation)
            dx = (length / 2) * math.cos(angle_rad)
            dy = (length / 2) * math.sin(angle_rad)
            style = '-|>' if reverse else '<|-'
            ax.annotate('', xy=(x + dx, y + dy), xytext=(x - dx, y - dy),
                        arrowprops=dict(arrowstyle=style, color='black', lw=1.0),
                        annotation_clip=False)
            ax.text(x, y, text, ha='center', va='center', rotation=rotation,
                    fontsize=7, bbox=dict(facecolor='white', edgecolor='none', pad=1))

        offset = 0.12
        cos30 = math.sqrt(3) / 2.0
        _arrow(-0.25 - offset * cos30, sx / 2.0 + offset * 0.5,
               "SO\u2084\u00b2\u207b+Cl\u207b", rotation=60, reverse=True)
        _arrow(0.25 + offset * cos30, sx / 2.0 + offset * 0.5,
               "Ca\u00b2\u207a+Mg\u00b2\u207a", rotation=-60)

        ax.set_xlim(-0.55, 0.55)
        ax.set_ylim(-sx - 0.05, sx + 0.05)
        ax.set_aspect("equal")
        ax.axis("off")

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
        if isinstance(spec.coord, (PiperCoord, StiffCoord)):
            return True
        if spec.template_name in IMPLEMENTED:
            return True
        if spec.layers:
            return all(
                l.geom.name in _GEOM_HANDLERS
                for l in spec.layers
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
                    coord=spec.coord,
                    zorder=layer.zorder,
                    subplot=layer.subplot,
                    xlim=layer.xlim,
                    ylim=layer.ylim,
                )
            )
        return dataclasses.replace(spec, layers=trans_layers)

    def _render_layer(self, ax, spec, layer, order):
        handler = _GEOM_HANDLERS.get(layer.geom.name)
        if handler is None:
            raise TypeError(f"Unsupported geom: {layer.geom.name}")
        handler(ax, layer, order)