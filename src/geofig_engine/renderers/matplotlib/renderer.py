"""
Matplotlib renderer for FigEngine.

This backend draws fully resolved FigureSpec objects using matplotlib.
"""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import is_color_like
from matplotlib.figure import Figure
from matplotlib.axes import Axes

from geofig_engine.core.spec import FigureSpec, extract_data_for_mapping
from geofig_engine.layers.base import FigureLayer
from geofig_engine.renderers.base import BaseRenderer
from geofig_engine.layers.scatter import ScatterLayer
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

        for layer in spec.layers:
            self._render_layer(ax, spec, layer)

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

        return fig
    
    def supports(self, spec: FigureSpec) -> bool:
        if spec.template_name in IMPLEMENTED:
            return True
        return False

    def _render_layer(self, ax, spec, layer):
        if isinstance(layer, ScatterLayer):
            render_scatter(ax, spec, layer)
            return
        if isinstance(layer, FigureLayer):
            return
        raise TypeError(f"Unsupported layer type: {type(layer)}")