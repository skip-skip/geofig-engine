"""
Matplotlib renderer for FigEngine.

This backend draws fully resolved FigureSpec objects using matplotlib.
"""

from __future__ import annotations

from typing import Any

from matplotlib.dates import DateFormatter
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import is_color_like
from matplotlib.figure import Figure
from matplotlib.axes import Axes

from geofig_engine.core.spec import FigureSpec, extract_data_for_mapping
from geofig_engine.layers.base import FigureLayer
from geofig_engine.layers.function_line import FunctionLineLayer
from geofig_engine.layers.line import LineLayer
from geofig_engine.renderers.base import BaseRenderer
from geofig_engine.layers.scatter import ScatterLayer
from geofig_engine.renderers.matplotlib.function_line import render_function_line
from geofig_engine.renderers.matplotlib.line import render_line
from geofig_engine.renderers.matplotlib.scatter import render_scatter
from geofig_engine.renderers.matplotlib.util import IMPLEMENTED

class MatplotlibRenderer(BaseRenderer):
    """Matplotlib backend for rendering FigEngine FigureSpec objects."""

    def render(self, spec: FigureSpec):
        if self.supports(spec) is False:
            raise NotImplementedError(f"MatplotlibRenderer does not currently support template '{spec.template_name}'")
        
        figsize = spec.settings.get("figsize", (10, 6))
        fig, ax = plt.subplots(figsize=figsize)

        # ------------------------------------
        # 1. LAYERS
        # ------------------------------------
        if not spec.layers:
            raise ValueError("FigureSpec must define at least one layer")

        for i, layer in enumerate(spec.layers):
            self._render_layer(ax, spec, layer, i+3) # reserve space for background elements

        # ------------------------------------
        # 2. GLOBAL SETTINGS
        # ------------------------------------
        title = spec.settings.get("title")
        if title:
            ax.set_title(title)
        xlabel = spec.settings.get("xlabel")
        if xlabel:
            ax.set_xlabel(xlabel)
        ylabel = spec.settings.get("ylabel")
        if ylabel:
            ax.set_ylabel(ylabel)
        xlim = spec.settings.get("xlim")
        if xlim:
            ax.set_xlim(xlim)
        ylim = spec.settings.get("ylim")
        if ylim:
            ax.set_ylim(ylim)
        xscale = spec.settings.get("xscale")
        if xscale:
            ax.set_xscale(xscale)
        yscale = spec.settings.get("yscale")
        if yscale:
            ax.set_yscale(yscale)
        grid = spec.settings.get("grid")
        if grid:
            ax.grid(grid, zorder=0)
        time_format = spec.settings.get("time_format")
        if time_format:
            ax.xaxis.set_major_formatter(DateFormatter(time_format))
        return fig
    
    def supports(self, spec: FigureSpec) -> bool:
        if spec.template_name in IMPLEMENTED:
            return True
        return False

    def _render_layer(self, ax, spec, layer, order):
        if isinstance(layer, ScatterLayer):
            render_scatter(ax, spec, layer, order)
            return
        if isinstance(layer, LineLayer):
            render_line(ax, spec, layer, order)
            return
        if isinstance(layer, FunctionLineLayer):
            render_function_line(ax, spec, layer, order)
            return
        if isinstance(layer, FigureLayer):
            return
        raise TypeError(f"Unsupported layer type: {type(layer)}")