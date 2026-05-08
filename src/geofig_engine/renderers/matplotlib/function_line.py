from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes

from geofig_engine.core.spec import FigureSpec
from geofig_engine.layers.function_line import FunctionLineLayer
from geofig_engine.renderers.matplotlib.util import extract_channel_data


def render_function_line(
    ax: Axes,
    spec: FigureSpec,
    layer: FunctionLineLayer,
    order: int,
) -> None:
    """
    Render a mathematical function line across the x domain.

    layer.func should be a string expression using `x`.

    Examples:
        "8*x+10"
        "0.5*x"
        "np.sin(x)"
    """

    # ---------------------------------------------------
    # resolve x data
    # ---------------------------------------------------
    x_data = extract_channel_data(spec, layer, "x")

    if x_data is None:
        raise ValueError("FunctionLineLayer requires x mapping")

    # ---------------------------------------------------
    # generate plotting domain
    # ---------------------------------------------------
    x_min = np.nanmin(x_data)
    x_max = np.nanmax(x_data)

    x_plot = np.linspace(x_min, x_max, 500)

    # ---------------------------------------------------
    # evaluate function expression
    # ---------------------------------------------------
    expression = layer.func.strip()

    if not expression:
        raise ValueError("FunctionLineLayer func cannot be empty")

    try:
        y_plot = eval(
            expression,
            {
                "__builtins__": {},
                "np": np,
            },
            {
                "x": x_plot,
            },
        )

    except Exception as exc:
        raise ValueError(
            f"Failed to evaluate function expression: '{expression}'"
        ) from exc

    # ---------------------------------------------------
    # render line
    # ---------------------------------------------------
    ax.plot(
        x_plot,
        y_plot,
        color=layer.color,
        linestyle=layer.linestyle,
        linewidth=layer.linewidth,
        label=layer.label,
        zorder=order,
    )