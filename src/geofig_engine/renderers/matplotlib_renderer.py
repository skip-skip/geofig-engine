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
        print(x_data)
        print(y_data)
        color_data = extract_data_for_mapping(spec, "color")
        marker_data = extract_data_for_mapping(spec, "marker")
        size_data = extract_data_for_mapping(spec, "size")
        alpha_data = extract_data_for_mapping(spec, "alpha")
        linestyle_data = extract_data_for_mapping(spec, "linestyle")

        scatter_kwargs: dict[str, Any] = {}

        if color_data is not None:
            if isinstance(color_data, str):
                scatter_kwargs["c"] = color_data
            else:
                color_series = pd.Series(color_data)
                unique_values = color_series.dropna().unique()
                if not all(is_color_like(value) for value in unique_values):
                    palette = list(plt.rcParams["axes.prop_cycle"].by_key()["color"])
                    mapping = {
                        value: palette[i % len(palette)]
                        for i, value in enumerate(unique_values)
                    }
                    color_series = color_series.map(mapping)
                scatter_kwargs["c"] = color_series
                color_data = color_series

        if size_data is not None:
            scatter_kwargs["s"] = size_data

        if alpha_data is not None:
            scatter_kwargs["alpha"] = alpha_data

        def plot_points(x, y, kwargs):
            ax.scatter(x, y, **kwargs)

        if marker_data is None or isinstance(marker_data, str):
            if isinstance(marker_data, str):
                scatter_kwargs["marker"] = marker_data
            plot_points(x_data, y_data, scatter_kwargs)
        else:
            marker_series = (
                marker_data
                if hasattr(marker_data, "__iter__") and not isinstance(marker_data, str)
                else [marker_data]
            )
            marker_series = pd.Series(marker_series)

            if isinstance(color_data, (list, tuple)):
                color_data = pd.Series(color_data, index=marker_series.index)

            marker_styles = ["o", "s", "^", "D", "P", "X", "*", "v", "<", ">"]
            unique_values = list(marker_series.dropna().unique())
            marker_map = {
                value: marker_styles[i % len(marker_styles)]
                for i, value in enumerate(unique_values)
            }

            for value, marker_style in marker_map.items():
                mask = marker_series == value
                group_kwargs = scatter_kwargs.copy()
                group_kwargs["marker"] = marker_style

                if color_data is not None and not isinstance(color_data, str):
                    group_kwargs["c"] = color_data.loc[mask]

                plot_points(
                    x_data.loc[mask],
                    y_data.loc[mask],
                    group_kwargs,
                )

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
