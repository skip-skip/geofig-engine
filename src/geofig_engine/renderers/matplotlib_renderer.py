"""
Matplotlib renderer for FigEngine.

This backend draws fully resolved FigureSpec objects using matplotlib.
"""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from geofig_engine.core.spec import FigureSpec, extract_data_for_mapping
from geofig_engine.renderers.base import BaseRenderer


class MatplotlibRenderer(BaseRenderer):
    """Matplotlib backend for rendering FigEngine FigureSpec objects."""

    def render(self, spec: FigureSpec) -> Figure:
        """Render a single FigureSpec to a matplotlib Figure."""
        figsize = spec.settings.get("figsize", (10, 6))
        fig, ax = plt.subplots(figsize=figsize)

        x_data = extract_data_for_mapping(spec, "x")
        y_data = extract_data_for_mapping(spec, "y")

        if x_data is None or y_data is None:
            raise ValueError("FigureSpec must define both 'x' and 'y' mappings")

        color_data = extract_data_for_mapping(spec, "color")
        marker_data = extract_data_for_mapping(spec, "marker")
        size_data = extract_data_for_mapping(spec, "size")
        alpha_data = extract_data_for_mapping(spec, "alpha")
        linestyle_data = extract_data_for_mapping(spec, "linestyle")

        scatter_kwargs: dict[str, Any] = {}

        if color_data is not None:
            scatter_kwargs["c"] = color_data

        if marker_data is not None and isinstance(marker_data, str):
            scatter_kwargs["marker"] = marker_data

        if size_data is not None:
            scatter_kwargs["s"] = size_data

        if alpha_data is not None:
            scatter_kwargs["alpha"] = alpha_data

        ax.scatter(x_data, y_data, **scatter_kwargs)

        if linestyle_data is not None:
            line_kwargs: dict[str, Any] = {}
            if isinstance(color_data, str):
                line_kwargs["color"] = color_data
            if isinstance(marker_data, str):
                line_kwargs["marker"] = marker_data
            ax.plot(x_data, y_data, linestyle=linestyle_data, **line_kwargs)

        title = spec.settings.get("title")
        if title is not None:
            ax.set_title(title)

        xlabel = spec.settings.get("xlabel")
        if xlabel is not None:
            ax.set_xlabel(xlabel)

        ylabel = spec.settings.get("ylabel")
        if ylabel is not None:
            ax.set_ylabel(ylabel)

        xlim = spec.settings.get("xlim")
        if xlim is not None:
            ax.set_xlim(xlim)

        ylim = spec.settings.get("ylim")
        if ylim is not None:
            ax.set_ylim(ylim)

        return fig
