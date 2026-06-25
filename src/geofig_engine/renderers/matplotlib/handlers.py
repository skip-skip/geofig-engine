"""LayerSpec-based geom handlers for MatplotlibRenderer."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from geofig_engine.core.layer import LayerSpec
from geofig_engine.renderers.matplotlib.util import resolve_color_series


def _resolve_constant(series: pd.Series) -> Any:
    """Return the first non-NA value from a Series, or the raw value if scalar."""
    if not isinstance(series, pd.Series):
        return series
    cleaned = series.dropna()
    if len(cleaned) > 0:
        return cleaned.iloc[0]
    return None


def render_point(ax: Axes, layer_spec: LayerSpec, order: int) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    if x is None or y is None:
        raise ValueError("GeomPoint requires both x and y channels")

    kwargs: dict[str, Any] = {"zorder": order}

    color = layer_spec.visual_mapping.get("color")
    if color is not None:
        kwargs["c"] = resolve_color_series(color)

    size = layer_spec.visual_mapping.get("size")
    if size is not None:
        kwargs["s"] = size.values if isinstance(size, pd.Series) else size

    marker = layer_spec.visual_mapping.get("marker")
    if marker is not None:
        kwargs["marker"] = marker.values if isinstance(marker, pd.Series) else marker

    alpha = layer_spec.visual_mapping.get("alpha")
    if alpha is not None:
        alpha_val = _resolve_constant(alpha) if isinstance(alpha, pd.Series) else alpha
        if alpha_val is not None:
            kwargs["alpha"] = float(alpha_val)

    x_vals = x.values if isinstance(x, pd.Series) else x
    y_vals = y.values if isinstance(y, pd.Series) else y
    ax.scatter(x_vals, y_vals, **kwargs)


def _draw_lines_grouped(ax, x, y, color_series, kwargs):
    for c_val in color_series.unique():
        if pd.isna(c_val):
            continue
        mask = color_series == c_val
        xg = x[mask] if isinstance(x, pd.Series) else pd.Series(x)[mask]
        yg = y[mask] if isinstance(y, pd.Series) else pd.Series(y)[mask]
        valid = ~(pd.isna(xg) | pd.isna(yg))
        xs, ys = xg[valid], yg[valid]
        if len(xs) < 2:
            continue
        order = np.argsort(xs.values, kind="stable")
        kw = dict(kwargs)
        kw["color"] = c_val
        ax.plot(xs.values[order], ys.values[order], **kw)


def render_line(ax: Axes, layer_spec: LayerSpec, order: int) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    if x is None or y is None:
        raise ValueError("GeomLine requires both x and y channels")

    kwargs: dict[str, Any] = {"zorder": order}

    color = layer_spec.visual_mapping.get("color")
    style = layer_spec.visual_mapping.get("style")
    width = layer_spec.visual_mapping.get("width")
    alpha = layer_spec.visual_mapping.get("alpha")

    if style is not None:
        kwargs["linestyle"] = _resolve_constant(style) if isinstance(style, pd.Series) else style
    if width is not None:
        kwargs["linewidth"] = _resolve_constant(width) if isinstance(width, pd.Series) else width
    if alpha is not None:
        alpha_val = _resolve_constant(alpha) if isinstance(alpha, pd.Series) else alpha
        if alpha_val is not None:
            kwargs["alpha"] = float(alpha_val)

    if color is not None:
        resolved = resolve_color_series(color)
        if isinstance(resolved, pd.Series) and resolved.nunique() > 1:
            _draw_lines_grouped(ax, x, y, resolved, kwargs)
            return
        kwargs["color"] = _resolve_constant(resolved) if isinstance(resolved, pd.Series) else resolved

    x_vals = x.values if isinstance(x, pd.Series) else x
    y_vals = y.values if isinstance(y, pd.Series) else y
    ax.plot(x_vals, y_vals, **kwargs)


def render_bar(ax: Axes, layer_spec: LayerSpec, order: int) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    if x is None or y is None:
        raise ValueError("GeomBar requires both x and y channels")

    kwargs: dict[str, Any] = {"zorder": order}

    color = layer_spec.visual_mapping.get("color")
    if color is not None:
        kwargs["color"] = resolve_color_series(color)

    width = layer_spec.visual_mapping.get("width")
    if width is not None:
        kwargs["width"] = _resolve_constant(width) if isinstance(width, pd.Series) else width

    alpha = layer_spec.visual_mapping.get("alpha")
    if alpha is not None:
        alpha_val = _resolve_constant(alpha) if isinstance(alpha, pd.Series) else alpha
        if alpha_val is not None:
            kwargs["alpha"] = float(alpha_val)

    ax.bar(x, y, **kwargs)


def render_area(ax: Axes, layer_spec: LayerSpec, order: int) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    if x is None or y is None:
        raise ValueError("GeomArea requires both x and y channels")

    kwargs: dict[str, Any] = {"zorder": order}

    color = layer_spec.visual_mapping.get("color")
    if color is not None:
        resolved = resolve_color_series(color)
        kwargs["color"] = _resolve_constant(resolved) if isinstance(resolved, pd.Series) else resolved

    alpha = layer_spec.visual_mapping.get("alpha")
    if alpha is not None:
        alpha_val = _resolve_constant(alpha) if isinstance(alpha, pd.Series) else alpha
        if alpha_val is not None:
            kwargs["alpha"] = float(alpha_val)

    ax.fill_between(x, y, 0, **kwargs)


def render_ribbon(ax: Axes, layer_spec: LayerSpec, order: int) -> None:
    x = layer_spec.visual_mapping.get("x")
    ymin = layer_spec.visual_mapping.get("ymin")
    ymax = layer_spec.visual_mapping.get("ymax")
    if x is None or ymin is None or ymax is None:
        raise ValueError("GeomRibbon requires x, ymin, and ymax channels")

    kwargs: dict[str, Any] = {"zorder": order}

    color = layer_spec.visual_mapping.get("color")
    if color is not None:
        resolved = resolve_color_series(color)
        kwargs["color"] = _resolve_constant(resolved) if isinstance(resolved, pd.Series) else resolved

    alpha = layer_spec.visual_mapping.get("alpha")
    if alpha is not None:
        alpha_val = _resolve_constant(alpha) if isinstance(alpha, pd.Series) else alpha
        if alpha_val is not None:
            kwargs["alpha"] = float(alpha_val)

    ax.fill_between(x, ymin, ymax, **kwargs)


def render_function_line(ax: Axes, layer_spec: LayerSpec, order: int) -> None:
    func = layer_spec.geom.func
    if not func:
        raise ValueError("GeomFunctionLine requires a func expression")

    x = layer_spec.visual_mapping.get("x")
    kwargs: dict[str, Any] = {"zorder": order}

    color = layer_spec.visual_mapping.get("color")
    if color is not None:
        resolved = resolve_color_series(color)
        if isinstance(resolved, pd.Series):
            kwargs["color"] = _resolve_constant(resolved)
        else:
            kwargs["color"] = resolved

    style = layer_spec.visual_mapping.get("style")
    if style is not None:
        kwargs["linestyle"] = _resolve_constant(style) if isinstance(style, pd.Series) else style

    width = layer_spec.visual_mapping.get("width")
    if width is not None:
        kwargs["linewidth"] = _resolve_constant(width) if isinstance(width, pd.Series) else width

    label = layer_spec.visual_mapping.get("label")
    if label is not None:
        kwargs["label"] = _resolve_constant(label) if isinstance(label, pd.Series) else label

    alpha = layer_spec.visual_mapping.get("alpha")
    if alpha is not None:
        alpha_val = _resolve_constant(alpha) if isinstance(alpha, pd.Series) else alpha
        if alpha_val is not None:
            kwargs["alpha"] = float(alpha_val)

    if isinstance(x, pd.Series) and len(x) > 0:
        x_min, x_max = float(x.min()), float(x.max())
    else:
        x_min, x_max = ax.get_xlim()

    x_plot = np.linspace(x_min, x_max, 500)

    try:
        y_plot = eval(
            func.strip(),
            {"__builtins__": {}, "np": np},
            {"x": x_plot},
        )
    except Exception as exc:
        raise ValueError(
            f"Failed to evaluate function expression: '{func}'"
        ) from exc

    ax.plot(x_plot, y_plot, **kwargs)


def render_text(ax: Axes, layer_spec: LayerSpec, order: int) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    label = layer_spec.visual_mapping.get("label")
    if x is None or y is None or label is None:
        raise ValueError("GeomText requires x, y, and label channels")

    color = layer_spec.visual_mapping.get("color")
    size = layer_spec.visual_mapping.get("size")
    alpha = layer_spec.visual_mapping.get("alpha")

    x_vals = x.values if isinstance(x, pd.Series) else [x]
    y_vals = y.values if isinstance(y, pd.Series) else [y]
    labels = label.values if isinstance(label, pd.Series) else [label]

    for i in range(len(x_vals)):
        kw: dict[str, Any] = {"zorder": order}
        if color is not None:
            c = color.values[i] if isinstance(color, pd.Series) else color
            kw["color"] = c
        if size is not None:
            s = size.values[i] if isinstance(size, pd.Series) else size
            kw["fontsize"] = s
        if alpha is not None:
            a = alpha.values[i] if isinstance(alpha, pd.Series) else alpha
            kw["alpha"] = float(a)
        ax.text(x_vals[i], y_vals[i], str(labels[i]), **kw)


def render_errorbar(ax: Axes, layer_spec: LayerSpec, order: int) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    ymin = layer_spec.visual_mapping.get("ymin")
    ymax = layer_spec.visual_mapping.get("ymax")
    if x is None or y is None or ymin is None or ymax is None:
        raise ValueError("GeomErrorbar requires x, y, ymin, and ymax channels")

    x_vals = x.values if isinstance(x, pd.Series) else [x]
    y_vals = y.values if isinstance(y, pd.Series) else [y]
    ymin_vals = ymin.values if isinstance(ymin, pd.Series) else [ymin]
    ymax_vals = ymax.values if isinstance(ymax, pd.Series) else [ymax]

    yerr_lower = np.array(y_vals) - np.array(ymin_vals)
    yerr_upper = np.array(ymax_vals) - np.array(y_vals)

    kwargs: dict[str, Any] = {"zorder": order, "fmt": "none"}

    color = layer_spec.visual_mapping.get("color")
    if color is not None:
        resolved = resolve_color_series(color)
        kwargs["color"] = _resolve_constant(resolved) if isinstance(resolved, pd.Series) else resolved

    width = layer_spec.visual_mapping.get("width")
    if width is not None:
        kwargs["capsize"] = _resolve_constant(width) if isinstance(width, pd.Series) else width

    alpha = layer_spec.visual_mapping.get("alpha")
    if alpha is not None:
        alpha_val = _resolve_constant(alpha) if isinstance(alpha, pd.Series) else alpha
        if alpha_val is not None:
            kwargs["alpha"] = float(alpha_val)

    ax.errorbar(x_vals, y_vals, yerr=[yerr_lower, yerr_upper], **kwargs)
