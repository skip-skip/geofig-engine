from typing import Any

from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import is_color_like
import pandas as pd

from geofig_engine.core.spec import FigureSpec, extract_data_for_mapping
from geofig_engine.layers.scatter import ScatterLayer
from geofig_engine.renderers.matplotlib.util import extract_channel_data, resolve_color_series

def render_scatter(ax: Axes, spec: FigureSpec, layer: ScatterLayer) -> None:
        """
        Render ScatterLayer using FigureSpec mappings.
        Behavior matches legacy renderer as closely as possible.
        """
        # -------------------------
        # base data (required)
        # -------------------------
        x_data = extract_channel_data(spec, layer, 'x')
        y_data = extract_channel_data(spec, layer, 'y')
        if x_data is None or y_data is None:
            raise ValueError("ScatterLayer requires both x and y mappings")
        # -------------------------
        # optional encodings
        # -------------------------
        color_data = extract_channel_data(spec, layer, 'color')
        marker_data = extract_channel_data(spec, layer, 'marker')
        size_data = extract_channel_data(spec, layer, 'size')
        alpha_data = extract_channel_data(spec, layer, 'alpha')
        # -------------------------
        # base kwargs (scalar-safe defaults)
        # -------------------------
        scatter_kwargs: dict[str, Any] = {}
        # -------------------------
        # COLOR (preserve legacy behavior)
        # -------------------------
        color_data = resolve_color_series(color_data)
        if color_data is not None:
            scatter_kwargs["c"] = color_data
        # -------------------------
        # SIZE
        # -------------------------
        if size_data is not None:
            scatter_kwargs["s"] = size_data
        # -------------------------
        # ALPHA
        # -------------------------
        if alpha_data is not None:
            scatter_kwargs["alpha"] = alpha_data
        # -------------------------
        # helper
        # -------------------------
        def plot(x, y, kwargs):
            ax.scatter(x, y, **kwargs)
        # -------------------------
        # MARKER LOGIC (unique value mapping)
        # -------------------------
        if marker_data is None or isinstance(marker_data, str):
            if isinstance(marker_data, str):
                scatter_kwargs["marker"] = marker_data
            plot(x_data, y_data, scatter_kwargs)
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
                plot(
                    x_data.loc[mask],
                    y_data.loc[mask],
                    group_kwargs,
                )

        # -------------------------
        # LAYOUT FEATURES (settings preserved)
        # -------------------------
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