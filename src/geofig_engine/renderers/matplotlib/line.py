from typing import Any

import pandas as pd
from matplotlib.axes import Axes

from geofig_engine.core.spec import FigureSpec
from geofig_engine.layers.line import LineLayer
from geofig_engine.renderers.matplotlib.util import (
    extract_channel_data,
    resolve_color_series,
)


def render_line(ax: Axes, spec: FigureSpec, layer: LineLayer, order: int,) -> None:
    """
    Render LineLayer using FigureSpec mappings.

    Supports:
    - x/y channels
    - optional y2 secondary axis
    - color/style/width/alpha channels
    - grouped rendering for iterable visual channels

    Lines are grouped by unique combinations of:
    - color
    - linewidth
    - alpha
    - linestyle

    Each group is independently sorted left-to-right.
    """

    # ---------------------------------------------------
    # required channels
    # ---------------------------------------------------
    x_data = extract_channel_data(spec, layer, "x")
    y_data = extract_channel_data(spec, layer, "y")
    y2_data = extract_channel_data(spec, layer, "y2")

    if x_data is None:
        raise ValueError("LineLayer requires x mapping")

    if y_data is None and y2_data is None:
        raise ValueError(
            "LineLayer requires at least one of y or y2"
        )

    # ---------------------------------------------------
    # optional encodings
    # ---------------------------------------------------
    color_data = extract_channel_data(spec, layer, "color")
    style_data = extract_channel_data(spec, layer, "style")
    width_data = extract_channel_data(spec, layer, "width")
    alpha_data = extract_channel_data(spec, layer, "alpha")

    # ---------------------------------------------------
    # normalize color data
    # ---------------------------------------------------
    color_data = resolve_color_series(color_data)

    # ---------------------------------------------------
    # secondary axis
    # ---------------------------------------------------
    secondary_ax = None

    if y2_data is not None:
        secondary_ax = ax.twinx()

    # ---------------------------------------------------
    # helper
    # ---------------------------------------------------
    def plot(
        target_ax,
        x,
        y,
        kwargs,
    ):
        target_ax.plot(
            x,
            y,
            zorder=order,
            **kwargs,
        )

    # ---------------------------------------------------
    # render helper
    # ---------------------------------------------------
    def render_series(
        target_ax,
        y_series,
    ):
        # -----------------------------------------------
        # normalize all visual channels
        # -----------------------------------------------
        index = x_data.index

        def normalize_channel(data):
            if data is None:
                return None

            if isinstance(data, str):
                return data

            if isinstance(data, (int, float)):
                return data

            return pd.Series(data, index=index)

        color_series = normalize_channel(color_data)
        style_series = normalize_channel(style_data)
        width_series = normalize_channel(width_data)
        alpha_series = normalize_channel(alpha_data)

        # -----------------------------------------------
        # build dataframe
        # -----------------------------------------------
        group_df = pd.DataFrame({
            "x": x_data,
            "y": y_series,
        })

        # -----------------------------------------------
        # style mapping
        # -----------------------------------------------
        line_styles = [
            "-",
            "--",
            "-.",
            ":",
        ]

        if isinstance(style_series, pd.Series):
            unique_styles = list(
                style_series.dropna().unique()
            )

            style_map = {
                value: line_styles[i % len(line_styles)]
                for i, value in enumerate(unique_styles)
            }

            group_df["style"] = style_series

        else:
            style_map = {}

            group_df["style"] = style_series

        # -----------------------------------------------
        # add channels
        # -----------------------------------------------
        group_df["color"] = color_series
        group_df["width"] = width_series
        group_df["alpha"] = alpha_series

        # -----------------------------------------------
        # group by visual combinations
        # -----------------------------------------------
        grouped = group_df.groupby(
            [
                "style",
                "color",
                "width",
                "alpha",
            ],
            dropna=False,
        )

        # -----------------------------------------------
        # render groups
        # -----------------------------------------------
        for (
            style_value,
            color_value,
            width_value,
            alpha_value,
        ), group in grouped:
            # -------------------------------------------
            # sort left-to-right, down-to-up
            # -------------------------------------------
            group = group.sort_values(["x", "y"])

            group_kwargs: dict[str, Any] = {}

            # -------------------------------------------
            # linestyle
            # -------------------------------------------
            if style_value is not None:
                if isinstance(style_series, pd.Series):
                    group_kwargs["linestyle"] = (
                        style_map.get(style_value, "-")
                    )
                else:
                    group_kwargs["linestyle"] = style_value

            # -------------------------------------------
            # color
            # -------------------------------------------
            if color_value is not None:
                group_kwargs["color"] = color_value

            # -------------------------------------------
            # linewidth
            # -------------------------------------------
            if width_value is not None:
                group_kwargs["linewidth"] = width_value

            # -------------------------------------------
            # alpha
            # -------------------------------------------
            if alpha_value is not None:
                group_kwargs["alpha"] = alpha_value

            # -------------------------------------------
            # render
            # -------------------------------------------
            plot(
                target_ax,
                group["x"],
                group["y"],
                group_kwargs,
            )

    # ---------------------------------------------------
    # render primary axis
    # ---------------------------------------------------
    if y_data is not None:
        render_series(ax, y_data)

    # ---------------------------------------------------
    # render secondary axis
    # ---------------------------------------------------
    if (
        y2_data is not None
        and secondary_ax is not None
    ):
        render_series(
            secondary_ax,
            y2_data,
        )

    # ---------------------------------------------------
    # secondary scale
    # ---------------------------------------------------
    y2scale = spec.settings.get("y2scale")

    if (
        y2scale
        and secondary_ax is not None
    ):
        secondary_ax.set_yscale(y2scale)