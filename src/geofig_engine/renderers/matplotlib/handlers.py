"""LayerSpec-based geom handlers for MatplotlibRenderer."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import to_rgba

from geofig_engine.core.coord import CoordPolar
from geofig_engine.core.layer import LayerSpec
from geofig_engine.renderers.matplotlib.util import resolve_color_series, resolve_marker_series


def _resolve_constant(series: pd.Series) -> Any:
    """Return the first non-NA value if constant, else return the full Series."""
    if not isinstance(series, pd.Series):
        return series
    cleaned = series.dropna()
    if len(cleaned) > 0 and cleaned.nunique() == 1:
        return cleaned.iloc[0]
    if len(cleaned) > 0:
        return series
    return None


def render_point(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    if x is None or y is None:
        raise ValueError("GeomPoint requires both x and y channels")

    from geofig_engine.renderers.matplotlib.position import dodge_positions

    geom = layer_spec.geom  # GeomPoint

    color = layer_spec.visual_mapping.get("color")
    size = layer_spec.visual_mapping.get("size")
    marker = layer_spec.visual_mapping.get("marker")
    alpha = layer_spec.visual_mapping.get("alpha")

    x_vals = x.values if isinstance(x, pd.Series) else np.asarray(x)
    y_vals = y.values if isinstance(y, pd.Series) else np.asarray(y)

    if len(x_vals) == 0:
        return

    # Resolve color to per-point values
    resolved_color = resolve_color_series(color) if color is not None else None

    # Resolve marker to per-point marker style strings
    resolved_marker = resolve_marker_series(marker) if marker is not None else None

    # Resolve size to per-point numeric values
    resolved_size = None
    if size is not None:
        resolved_size = size.values if isinstance(size, pd.Series) else size

    # Resolve alpha to scalar
    resolved_alpha = None
    if alpha is not None:
        resolved_alpha = _resolve_constant(alpha) if isinstance(alpha, pd.Series) else alpha
        if resolved_alpha is not None:
            resolved_alpha = float(resolved_alpha)

    # Dodge positions when color grouping is active
    if geom.dodge > 0 and color is not None and isinstance(color, pd.Series):
        from geofig_engine.renderers.matplotlib.position import dodge_positions
        color_str = color.astype(str)
        x_str = x.astype(str) if not pd.api.types.is_numeric_dtype(x) else x
        all_series = list(color_str.unique())
        groups = []
        try:
            groups = sorted(x_str.unique())
        except Exception:
            groups = list(dict.fromkeys(x_str))
        n_series = len(all_series)
        x_out = np.empty_like(x_vals, dtype=float)
        for gi, gval in enumerate(groups):
            for si, sname in enumerate(all_series):
                mask = (x_str == gval) & (color_str == sname)
                if not mask.any():
                    continue
                pos, _ = dodge_positions(float(gi + 1), si, n_series, geom.dodge)
                x_out[mask.values] = pos
        x_vals = x_out

    # Add jitter
    if geom.jitter > 0:
        rng = np.random.default_rng(42)
        x_vals = x_vals + rng.uniform(-geom.jitter, geom.jitter, len(x_vals))

    # When markers vary per point, scatter each marker group separately
    if resolved_marker is not None and isinstance(resolved_marker, pd.Series) and resolved_marker.nunique() > 1:
        for mkr in resolved_marker.unique():
            mask = resolved_marker == mkr
            kwargs: dict[str, Any] = {"zorder": order, "s": 20, "edgecolors": "black", "linewidths": 0.5, "marker": mkr}
            if resolved_color is not None:
                c_vals = resolved_color[mask] if isinstance(resolved_color, pd.Series) else resolved_color
                kwargs["c"] = c_vals.values if isinstance(c_vals, pd.Series) else c_vals
            if resolved_size is not None:
                s_vals = resolved_size[mask] if isinstance(resolved_size, (pd.Series, np.ndarray)) else resolved_size
                kwargs["s"] = s_vals.values if isinstance(s_vals, pd.Series) else s_vals
            if resolved_alpha is not None:
                kwargs["alpha"] = resolved_alpha
            ax.scatter(x_vals[mask.values], y_vals[mask.values], **kwargs)
    else:
        kwargs: dict[str, Any] = {"zorder": order, "s": 20, "edgecolors": "black", "linewidths": 0.5}
        if resolved_color is not None:
            kwargs["c"] = resolved_color.values if isinstance(resolved_color, pd.Series) else resolved_color
        if resolved_size is not None:
            kwargs["s"] = resolved_size
        if resolved_marker is not None:
            m = resolved_marker.iloc[0] if isinstance(resolved_marker, pd.Series) else resolved_marker
            kwargs["marker"] = m
        if resolved_alpha is not None:
            kwargs["alpha"] = resolved_alpha
        ax.scatter(x_vals, y_vals, **kwargs)


def _draw_lines_grouped(ax, x, y, color_series, kwargs, polar=False):
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
        if polar:
            sorted_xs = xs.values[order]
            sorted_ys = ys.values[order]
            ax.plot(
                np.append(sorted_xs, sorted_xs[0]),
                np.append(sorted_ys, sorted_ys[0]),
                **kw,
            )
        else:
            ax.plot(xs.values[order], ys.values[order], **kw)


def render_line(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
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
            _draw_lines_grouped(ax, x, y, resolved, kwargs, polar=isinstance(coord, CoordPolar))
            return
        kwargs["color"] = _resolve_constant(resolved) if isinstance(resolved, pd.Series) else resolved

    x_vals = x.values if isinstance(x, pd.Series) else x
    y_vals = y.values if isinstance(y, pd.Series) else y
    if isinstance(coord, CoordPolar):
        x_vals = np.append(x_vals, x_vals[0])
        y_vals = np.append(y_vals, y_vals[0])
    ax.plot(x_vals, y_vals, **kwargs)


def _stack_values(x: pd.Series, y: pd.Series, fill: bool = False) -> tuple[pd.Series, pd.Series]:
    """Compute stacked y and bottom values for bars at each x.

    Returns (adjusted_y, bottom) where adjusted_y is normalised for fill.
    """
    df = pd.DataFrame({"x": x.values, "y": y.values})
    if fill:
        df["y"] = df.groupby("x")["y"].transform(lambda g: g / g.sum() if g.sum() > 0 else g)
    df["bottom"] = df.groupby("x")["y"].cumsum() - df["y"]
    return pd.Series(df["y"].values), pd.Series(df["bottom"].values)


def render_bar(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    if x is None or y is None:
        raise ValueError("GeomBar requires both x and y channels")

    kwargs: dict[str, Any] = {"zorder": order, "edgecolor": "black", "linewidth": 0.5}

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

    position = getattr(layer_spec.geom, "position", "identity")
    if position in ("stack", "fill"):
        y_adj, bottom = _stack_values(x, y, fill=(position == "fill"))
        kwargs["bottom"] = bottom
        y = y_adj
    ax.bar(x, y, **kwargs)


def _draw_areas_grouped(ax, x, y, color_series, kwargs, polar=False):
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
        if polar:
            kw["facecolor"] = c_val
            kw.pop("color", None)
            sorted_xs = xs.values[order]
            sorted_ys = ys.values[order]
            ax.fill(
                np.append(sorted_xs, sorted_xs[0]),
                np.append(sorted_ys, sorted_ys[0]),
                **kw,
            )
        else:
            kw["color"] = c_val
            ax.fill_between(xs.values[order], ys.values[order], 0, **kw)


def render_area(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    if x is None or y is None:
        raise ValueError("GeomArea requires both x and y channels")

    kwargs: dict[str, Any] = {"zorder": order}

    alpha = layer_spec.visual_mapping.get("alpha")
    if alpha is not None:
        alpha_val = _resolve_constant(alpha) if isinstance(alpha, pd.Series) else alpha
        if alpha_val is not None:
            kwargs["alpha"] = float(alpha_val)

    color = layer_spec.visual_mapping.get("color")
    if color is not None:
        resolved = resolve_color_series(color)
        if isinstance(resolved, pd.Series) and resolved.nunique() > 1:
            _draw_areas_grouped(ax, x, y, resolved, kwargs,
                                polar=isinstance(coord, CoordPolar))
            return
        kwargs["color"] = _resolve_constant(resolved) if isinstance(resolved, pd.Series) else resolved

    if isinstance(coord, CoordPolar):
        x_vals = np.append(x.values, x.values[0])
        y_vals = np.append(y.values, y.values[0])
        fill_kw = {"facecolor": kwargs.pop("color", None)} if "color" in kwargs else {}
        fill_kw.update(kwargs)
        ax.fill(x_vals, y_vals, **fill_kw)
    else:
        ax.fill_between(x, y, 0, **kwargs)


def render_polygon(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    if x is None or y is None:
        raise ValueError("GeomPolygon requires both x and y channels")

    geom = layer_spec.geom  # GeomPolygon

    x_vals = x.values if isinstance(x, pd.Series) else np.asarray(x)
    y_vals = y.values if isinstance(y, pd.Series) else np.asarray(y)
    if len(x_vals) < 3 or len(y_vals) < 3:
        return

    kwargs: dict[str, Any] = {"zorder": order}

    color = layer_spec.visual_mapping.get("color")
    if color is not None:
        resolved = resolve_color_series(color)
        kwargs["facecolor"] = (
            _resolve_constant(resolved) if isinstance(resolved, pd.Series) else resolved
        )

    alpha = layer_spec.visual_mapping.get("alpha")
    if alpha is not None:
        alpha_val = _resolve_constant(alpha) if isinstance(alpha, pd.Series) else alpha
        if alpha_val is not None:
            kwargs["alpha"] = float(alpha_val)

    if geom.edgealpha is not None:
        kwargs["edgecolor"] = to_rgba(geom.edgecolor, geom.edgealpha)
    else:
        kwargs["edgecolor"] = geom.edgecolor
    kwargs["linewidth"] = geom.edgewidth
    kwargs["linestyle"] = geom.edgestyle

    ax.fill(x_vals, y_vals, **kwargs)


def render_ribbon(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
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


def render_function_line(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
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


def _measure_text_px(text: str, fontsize: float, rotation: float = 0) -> tuple[float, float]:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(1, 1))
    t = ax.text(0, 0, text, fontsize=fontsize, rotation=rotation)
    fig.canvas.draw()
    bb = t.get_window_extent(fig.canvas.renderer)
    plt.close(fig)
    return bb.width, bb.height


def render_text(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    label = layer_spec.visual_mapping.get("label")
    if x is None or y is None or label is None:
        raise ValueError("GeomText requires x, y, and label channels")

    color = layer_spec.visual_mapping.get("color")
    size = layer_spec.visual_mapping.get("size")
    alpha = layer_spec.visual_mapping.get("alpha")
    angle = layer_spec.visual_mapping.get("angle")
    bbox = layer_spec.visual_mapping.get("bbox")

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
        if angle is not None:
            a = angle.values[i] if isinstance(angle, pd.Series) else angle
            kw["rotation"] = float(a)
        if bbox is not None:
            b = bbox.values[i] if isinstance(bbox, pd.Series) else bbox
            kw["bbox"] = b

        if isinstance(coord, CoordPolar):
            angle_rad = float(x_vals[i])
            kw["ha"] = "left" if -np.pi / 2 <= angle_rad % (2 * np.pi) <= np.pi / 2 else "right"
            kw["va"] = "center"

        ax.text(x_vals[i], y_vals[i], str(labels[i]), **kw)


def render_errorbar(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
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


def _sort_and_filter_groups(
    x_series: pd.Series,
    sort_mode: str,
    smush: bool,
    y_series: pd.Series | None = None,
) -> list:
    """Sort unique x-group labels by sort_mode, optionally filtering empty groups.

    Parameters
    ----------
    x_series : pd.Series
        Categorical x-values used for grouping.
    sort_mode : str
        One of ``"none"``, ``"forward"``, ``"reverse"``, ``"value_forward"``,
        or ``"value_reverse"``.
    smush : bool
        If True, groups with no data are omitted.
    y_series : pd.Series or None
        Numeric y-values. Required for ``value_forward`` / ``value_reverse``.
    """
    if len(x_series) == 0:
        return []
    unique = list(x_series.unique())
    if sort_mode == "forward":
        return sorted(unique)
    elif sort_mode == "reverse":
        return sorted(unique, reverse=True)
    elif sort_mode in ("value_forward", "value_reverse"):
        if y_series is None:
            return unique
        meds = {g: float(y_series[x_series == g].median()) for g in unique}
        rev = sort_mode == "value_reverse"
        return sorted(unique, key=lambda g: meds.get(g, 0), reverse=rev)
    return unique  # none


def _build_color_map(color_series):
    """Build {label -> rgba} from the matplotlib prop cycle (first-appearance order)."""
    import matplotlib.pyplot as plt
    cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    unique = list(color_series.astype(str).unique())
    return {s: cycle[i % len(cycle)] for i, s in enumerate(unique)}


def render_box(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    if x is None or y is None:
        raise ValueError("GeomBox requires both x and y channels")

    from geofig_engine.renderers.matplotlib.position import dodge_positions

    geom = layer_spec.geom  # GeomBox
    color = layer_spec.visual_mapping.get("color")
    alpha_val = layer_spec.visual_mapping.get("alpha")
    x_labels = x.astype(str) if not pd.api.types.is_string_dtype(x) else x
    color_map: dict = {}

    if color is not None and isinstance(color, pd.Series):
        color_vals = color.astype(str)
        all_series = list(color_vals.unique())
        color_map = _build_color_map(color)
        groups = _sort_and_filter_groups(x_labels, geom.sort_mode, geom.smush, y_series=y)
        n_series = len(all_series)
        positions: list[float] = []
        data_vals: list = []
        series_for_pos: list[str] = []

        for gi, group in enumerate(groups):
            center = gi + 1
            for si, sname in enumerate(all_series):
                mask = (x_labels == group) & (color_vals == sname)
                subset = y[mask].dropna()
                if geom.smush and len(subset) == 0:
                    continue
                if len(subset) < geom.min_box_n:
                    continue
                pos, _ = dodge_positions(center, si, n_series, geom.box_width)
                positions.append(pos)
                data_vals.append(subset.values)
                series_for_pos.append(sname)

        bp = ax.boxplot(
            data_vals,
            positions=positions,
            widths=geom.box_width / n_series * 0.85,
            patch_artist=True,
            showfliers=geom.showfliers,
            showmeans=geom.showmeans,
            zorder=order,
        )

        _apply_box_colors(bp, series_for_pos, all_series, alpha_val)
        _style_box_lines(bp)

        tick_positions = [i + 1 for i in range(len(groups))]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(groups)
    else:
        groups = _sort_and_filter_groups(x_labels, geom.sort_mode, geom.smush, y_series=y)
        data_vals = [y[x_labels == g].dropna().values for g in groups]
        data_vals = [d for d in data_vals if len(d) >= geom.min_box_n]
        if not data_vals:
            raise ValueError("No data groups with sufficient samples for GeomBox")
        groups = [g for g, d in zip(groups, data_vals) if len(d) >= geom.min_box_n]
        positions = list(range(1, len(groups) + 1))

        bp = ax.boxplot(
            data_vals,
            positions=positions,
            widths=geom.box_width * 0.85,
            patch_artist=True,
            showfliers=geom.showfliers,
            showmeans=geom.showmeans,
            zorder=order,
        )

        _style_box_lines(bp)

        ax.set_xticks(positions)
        ax.set_xticklabels(groups)

    # Show n-labels
    if geom.show_n:
        for pos, vals in zip(positions, data_vals):
            n = len(vals)
            vmax = float(np.nanmax(vals)) if len(vals) > 0 else 0
            ax.text(pos, vmax, f"n={n}", ha="center", va="bottom", fontsize=7, zorder=order + 1)


def _style_box_lines(bp):
    """Set outline elements of a boxplot to black."""
    for line_list in (bp["whiskers"], bp["caps"], bp["medians"]):
        for line in line_list:
            line.set_color("black")
            line.set_linewidth(0.8)
    if bp.get("fliers"):
        for flier in bp["fliers"]:
            flier.set_markeredgecolor("black")
            flier.set_markeredgewidth(0.5)
    if bp.get("means"):
        for mean in bp["means"]:
            mean.set_markeredgecolor("black")


def _apply_box_colors(bp, series_for_pos, all_series, alpha_val):
    """Apply categorical colors to boxplot patches and set black outlines."""
    import matplotlib.pyplot as plt
    cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    color_map = {s: cycle[i % len(cycle)] for i, s in enumerate(all_series)}
    for patch, sname in zip(bp["boxes"], series_for_pos):
        patch.set_facecolor(color_map[sname])
        patch.set_edgecolor("black")
        patch.set_linewidth(0.5)
        if alpha_val is not None:
            a = _resolve_constant(alpha_val) if isinstance(alpha_val, pd.Series) else alpha_val
            if a is not None:
                patch.set_alpha(float(a))


def _style_violin_lines(parts):
    """Set violin percentile/center lines to black."""
    for key in ("cbars", "cmins", "cmaxes", "cmedians"):
        coll = parts.get(key)
        if coll is not None:
            coll.set_color("black")
            coll.set_linewidth(0.5)


def _apply_violin_colors(bodies, series_for_pos, all_series, alpha_val):
    """Apply categorical colors to violin bodies with black outline and alpha=1 default."""
    import matplotlib.pyplot as plt
    cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    color_map = {s: cycle[i % len(cycle)] for i, s in enumerate(all_series)}
    for body, sname in zip(bodies, series_for_pos):
        body.set_facecolor(color_map[sname])
        body.set_edgecolor("black")
        body.set_linewidth(0.5)
        if alpha_val is not None:
            a = _resolve_constant(alpha_val) if isinstance(alpha_val, pd.Series) else alpha_val
            if a is not None:
                body.set_alpha(float(a))
        else:
            body.set_alpha(1.0)


def render_violin(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    if x is None or y is None:
        raise ValueError("GeomViolin requires both x and y channels")

    from geofig_engine.renderers.matplotlib.position import dodge_positions

    geom = layer_spec.geom  # GeomViolin
    color = layer_spec.visual_mapping.get("color")
    alpha_val = layer_spec.visual_mapping.get("alpha")
    x_labels = x.astype(str) if not pd.api.types.is_string_dtype(x) else x

    if color is not None and isinstance(color, pd.Series):
        color_vals = color.astype(str)
        all_series = list(color_vals.unique())
        groups = _sort_and_filter_groups(x_labels, geom.sort_mode, geom.smush, y_series=y)
        n_series = len(all_series)
        total_width = 0.8
        positions: list[float] = []
        data_vals: list = []
        series_for_pos: list[str] = []

        for gi, group in enumerate(groups):
            center = gi + 1
            for si, sname in enumerate(all_series):
                mask = (x_labels == group) & (color_vals == sname)
                subset = y[mask].dropna()
                if geom.smush and len(subset) == 0:
                    continue
                if len(subset) == 0:
                    continue
                pos, _ = dodge_positions(center, si, n_series, total_width)
                positions.append(pos)
                data_vals.append(subset.values)
                series_for_pos.append(sname)

        parts = ax.violinplot(
            data_vals,
            positions=positions,
            showmedians=geom.show_medians,
            widths=total_width / n_series,
        )
        _apply_violin_colors(parts.get("bodies", []), series_for_pos, all_series, alpha_val)
        _style_violin_lines(parts)
        tick_positions = [i + 1 for i in range(len(groups))]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(groups)
    else:
        groups = _sort_and_filter_groups(x_labels, geom.sort_mode, geom.smush, y_series=y)
        data_vals = [y[x_labels == g].dropna().values for g in groups]
        data_vals = [d for d in data_vals if len(d) > 0]
        groups = [g for g, d in zip(groups, data_vals) if len(d) > 0]
        positions = list(range(1, len(groups) + 1))

        parts = ax.violinplot(data_vals, positions=positions, showmedians=geom.show_medians)
        _style_violin_lines(parts)

        ax.set_xticks(positions)
        ax.set_xticklabels(groups)

    if color is not None and isinstance(color, pd.Series):
        pass
    else:
        for body in parts.get("bodies", []):
            body.set_edgecolor("black")
            body.set_linewidth(0.5)
            if alpha_val is not None:
                a = _resolve_constant(alpha_val) if isinstance(alpha_val, pd.Series) else alpha_val
                if a is not None:
                    body.set_alpha(float(a))
                else:
                    body.set_alpha(1.0)
            else:
                body.set_alpha(1.0)


def render_abline(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
    geom = layer_spec.geom
    kwargs: dict[str, Any] = {"zorder": order}

    color = layer_spec.visual_mapping.get("color")
    if color is not None:
        resolved = resolve_color_series(color)
        kwargs["color"] = _resolve_constant(resolved) if isinstance(resolved, pd.Series) else resolved
    style = layer_spec.visual_mapping.get("style")
    if style is not None:
        kwargs["linestyle"] = _resolve_constant(style) if isinstance(style, pd.Series) else style
    width = layer_spec.visual_mapping.get("width")
    if width is not None:
        kwargs["linewidth"] = _resolve_constant(width) if isinstance(width, pd.Series) else width
    alpha = layer_spec.visual_mapping.get("alpha")
    if alpha is not None:
        alpha_val = _resolve_constant(alpha) if isinstance(alpha, pd.Series) else alpha
        if alpha_val is not None:
            kwargs["alpha"] = float(alpha_val)

    if geom.slope is not None:
        ax.axline(xy1=(0, geom.intercept), slope=geom.slope, **kwargs)
    else:
        ax.axline(xy1=(geom.x1, geom.y1), xy2=(geom.x2, geom.y2), **kwargs)


def render_hspan(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
    ymin = layer_spec.visual_mapping.get("ymin")
    ymax = layer_spec.visual_mapping.get("ymax")
    if ymin is None or ymax is None:
        raise ValueError("GeomHSpan requires ymin and ymax channels")

    ymin_val = _resolve_constant(ymin) if isinstance(ymin, pd.Series) else ymin
    ymax_val = _resolve_constant(ymax) if isinstance(ymax, pd.Series) else ymax

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

    ax.axhspan(ymin_val, ymax_val, **kwargs)


def render_vspan(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
    xmin = layer_spec.visual_mapping.get("xmin")
    xmax = layer_spec.visual_mapping.get("xmax")
    if xmin is None or xmax is None:
        raise ValueError("GeomVSpan requires xmin and xmax channels")

    xmin_val = _resolve_constant(xmin) if isinstance(xmin, pd.Series) else xmin
    xmax_val = _resolve_constant(xmax) if isinstance(xmax, pd.Series) else xmax

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

    ax.axvspan(xmin_val, xmax_val, **kwargs)


def render_rect(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
    xmin = layer_spec.visual_mapping.get("xmin")
    xmax = layer_spec.visual_mapping.get("xmax")
    ymin = layer_spec.visual_mapping.get("ymin")
    ymax = layer_spec.visual_mapping.get("ymax")
    if xmin is None or xmax is None or ymin is None or ymax is None:
        raise ValueError("GeomRect requires xmin, xmax, ymin, and ymax channels")

    xmin_val = _resolve_constant(xmin) if isinstance(xmin, pd.Series) else xmin
    xmax_val = _resolve_constant(xmax) if isinstance(xmax, pd.Series) else xmax
    ymin_val = _resolve_constant(ymin) if isinstance(ymin, pd.Series) else ymin
    ymax_val = _resolve_constant(ymax) if isinstance(ymax, pd.Series) else ymax

    from matplotlib.patches import Rectangle

    kwargs: dict[str, Any] = {"zorder": order}
    color = layer_spec.visual_mapping.get("color")
    if color is not None:
        resolved = resolve_color_series(color)
        kwargs["facecolor"] = _resolve_constant(resolved) if isinstance(resolved, pd.Series) else resolved
    alpha = layer_spec.visual_mapping.get("alpha")
    if alpha is not None:
        alpha_val = _resolve_constant(alpha) if isinstance(alpha, pd.Series) else alpha
        if alpha_val is not None:
            kwargs["alpha"] = float(alpha_val)

    rect = Rectangle(
        (xmin_val, ymin_val),
        xmax_val - xmin_val,
        ymax_val - ymin_val,
        **kwargs,
    )
    ax.add_patch(rect)


def render_step_line(ax: Axes, layer_spec: LayerSpec, order: int, coord=None) -> None:
    x = layer_spec.visual_mapping.get("x")
    y = layer_spec.visual_mapping.get("y")
    if x is None or y is None:
        raise ValueError("GeomStepLine requires both x and y channels")

    geom = layer_spec.geom  # GeomStepLine
    kwargs: dict[str, Any] = {"zorder": order, "drawstyle": f"steps-{geom.where}", "color": "black"}

    color = layer_spec.visual_mapping.get("color")
    if color is not None:
        resolved = resolve_color_series(color)
        if isinstance(resolved, pd.Series) and resolved.nunique() > 1:
            _draw_lines_grouped(ax, x, y, resolved, kwargs)
            return
        kwargs["color"] = _resolve_constant(resolved) if isinstance(resolved, pd.Series) else resolved

    style = layer_spec.visual_mapping.get("style")
    if style is not None:
        kwargs["linestyle"] = _resolve_constant(style) if isinstance(style, pd.Series) else style

    width = layer_spec.visual_mapping.get("width")
    if width is not None:
        kwargs["linewidth"] = _resolve_constant(width) if isinstance(width, pd.Series) else width

    alpha = layer_spec.visual_mapping.get("alpha")
    if alpha is not None:
        alpha_val = _resolve_constant(alpha) if isinstance(alpha, pd.Series) else alpha
        if alpha_val is not None:
            kwargs["alpha"] = float(alpha_val)

    x_vals = x.values if isinstance(x, pd.Series) else x
    y_vals = y.values if isinstance(y, pd.Series) else y
    ax.plot(x_vals, y_vals, **kwargs)



