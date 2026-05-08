from typing import Any
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import is_color_like, to_hex
from geofig_engine.core.spec import FigureSpec, extract_data_for_mapping
from geofig_engine.layers.base import FigureLayer
from geofig_engine.layers.scatter import ScatterLayer

### List of templates that have a valid implementation in this renderer.
IMPLEMENTED: list[str] = ["test", "bivariate", "isotope", "timeseries"]

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
def extract_channel_data(spec: FigureSpec, layer: ScatterLayer, channel: str) -> Any:
    """
    Extract data for a given channel from the FigureSpec mappings.

    Args:
        spec: The FigureSpec to extract from.
        layer: The ScatterLayer defining the channel mapping.
        channel: The channel name (e.g., "x", "y", "color").

    Returns:
        The extracted data for the channel, or None if not defined.
    """
    data = extract_data_for_mapping(spec, channel)
    if data is None:
        data = getattr(layer, channel)
    return data