from typing import Any
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import is_color_like, to_hex

### List of templates that have a valid implementation in this renderer.
IMPLEMENTED: list[str] = ["test", "bivariate", "isotope", "timeseries"]

# Matplotlib marker styles for categorical mapping
_MARKER_STYLES = [
    "o", "s", "D", "^", "v", "<", ">", "P", "*", "X",
    "p", "h", "H", "d", "8",
]


def resolve_color_series(color_data: Any) -> Any:
    """
    Normalize color input into matplotlib-compatible format.

    Rules:
    - str → constant color
    - iterable of valid colors → preserved
    - categorical values → mapped to generated colors

    Color generation:
    - starts with tab10 palette
    - expands into continuous hsv sampling if needed
    """

    if color_data is None:
        return None
    # ---------------------------------------------------
    # scalar color
    # ---------------------------------------------------
    if (
        isinstance(color_data, str)
        and is_color_like(color_data)
    ):
        return color_data
    color_series = pd.Series(color_data)
    unique_values = list(pd.Series(color_series.dropna().unique()))
    # ---------------------------------------------------
    # already valid colors
    # ---------------------------------------------------
    if all(is_color_like(v) for v in unique_values):
        return color_series
    # ---------------------------------------------------
    # base discrete palette
    # ---------------------------------------------------
    base_palette = list(plt.get_cmap("tab10").colors)
    n_unique = len(unique_values)
    # ---------------------------------------------------
    # enough colors in tab10
    # ---------------------------------------------------
    if n_unique <= len(base_palette):
        mapping = {
            value: to_hex(base_palette[i])
            for i, value in enumerate(unique_values)
        }
        return color_series.map(mapping)
    # ---------------------------------------------------
    # extended palette
    # ---------------------------------------------------
    colors: list[str] = [
        to_hex(c)
        for c in base_palette
    ]
    remaining = n_unique - len(base_palette)
    continuous_cmap = plt.get_cmap("gist_rainbow")
    sampled = [
        to_hex(
            continuous_cmap(i / remaining)
        )
        for i in range(remaining)
    ]
    colors.extend(sampled)
    mapping = {
        value: colors[i]
        for i, value in enumerate(unique_values)
    }
    return color_series.map(mapping)


def resolve_marker_series(marker_data: Any) -> Any:
    """
    Normalize marker input into matplotlib-compatible format.

    Rules:
    - valid marker string -> pass through
    - categorical values -> mapped to distinct marker styles
    """
    if marker_data is None:
        return None
    if isinstance(marker_data, str):
        return marker_data
    marker_series = pd.Series(marker_data)
    unique_values = list(marker_series.dropna().unique())
    if len(unique_values) == 0:
        return marker_series
    if len(unique_values) == 1 and isinstance(unique_values[0], str) and unique_values[0] in _MARKER_STYLES:
        return marker_series
    mapping = {
        value: _MARKER_STYLES[i % len(_MARKER_STYLES)]
        for i, value in enumerate(unique_values)
    }
    return marker_series.map(mapping)