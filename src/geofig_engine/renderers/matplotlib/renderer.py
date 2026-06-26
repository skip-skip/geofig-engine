"""
Matplotlib renderer for FigEngine.

This backend draws fully resolved FigureSpec objects using matplotlib.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from matplotlib.dates import DateFormatter
import matplotlib.pyplot as plt

from geofig_engine.core.coord import CoordFlipped, CoordFixed, CoordPolar
from geofig_engine.core.facet import FacetGrid, FacetNull, FacetWrap
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.spec import FigureSpec
from geofig_engine.renderers.base import BaseRenderer
from geofig_engine.renderers.matplotlib.handlers import (
    render_area,
    render_bar,
    render_errorbar,
    render_function_line,
    render_line,
    render_point,
    render_ribbon,
    render_text,
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
}


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
            filtered = LayerSpec(
                geom=layer.geom,
                stat=layer.stat,
                visual_mapping={k: _filter_series(v, rows) for k, v in layer.visual_mapping.items()},
                data_override=layer.data_override,
            )
            self._render_layer(ax, spec, filtered, 10 + data_idx)
            data_idx += 1

        xlim_data = ax.get_xlim()
        ylim_data = ax.get_ylim()
        ax.autoscale(False)

        for i, layer in func_layers:
            filtered = LayerSpec(
                geom=layer.geom,
                stat=layer.stat,
                visual_mapping={k: _filter_series(v, rows) for k, v in layer.visual_mapping.items() if k != "x"},
            )
            self._render_layer(ax, spec, filtered, 1 + i)

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
        xlabel = spec.settings.get("xlabel") or self._channel_label(spec, "x")
        ylabel = spec.settings.get("ylabel") or self._channel_label(spec, "y")
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
            if yscale:
                ax.set_xscale(yscale)
            if xscale:
                ax.set_yscale(xscale)
        else:
            if xscale:
                ax.set_xscale(xscale)
            if yscale:
                ax.set_yscale(yscale)
        if isinstance(coord, CoordFixed):
            ax.set_aspect(coord.params.get("ratio", 1.0))
        grid = spec.settings.get("grid")
        if grid:
            ax.grid(grid, zorder=0)
        time_format = spec.settings.get("time_format")
        if time_format:
            ax.xaxis.set_major_formatter(DateFormatter(time_format))
        figname = spec.settings.get("figname")
        if figname:
            fig.figname = figname

    # ------------------------------------------------------------------
    # Faceted (multi-panel)
    # ------------------------------------------------------------------

    def _render_faceted(self, spec: FigureSpec):
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

        fig, axes = plt.subplots(*layout, figsize=figsize, squeeze=False)

        # Compute global limits for fixed scales
        glims = self._compute_facet_limits(spec, panels, facet.scales)

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

    def _render_layer(self, ax, spec, layer, order):
        handler = _GEOM_HANDLERS.get(layer.geom.name)
        if handler is None:
            raise TypeError(f"Unsupported geom: {layer.geom.name}")
        handler(ax, layer, order)