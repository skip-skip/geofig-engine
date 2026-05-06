from typing import Any
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import is_color_like
from geofig_engine.core.spec import FigureSpec, extract_data_for_mapping
from geofig_engine.layers.base import FigureLayer
from geofig_engine.layers.scatter import ScatterLayer

### List of templates that have a valid implementation in this renderer.
IMPLEMENTED: list[str] = ["test", "bivariate"]

def resolve_color_series(color_data: Any) -> Any:
    """
    Normalize color input into matplotlib-compatible format.

    Rules:
    - str → constant color
    - list/Series → categorical mapping if needed
    - valid color strings are preserved
    """

    if color_data is None:
        return None

    # -------------------------
    # scalar color
    # -------------------------
    if isinstance(color_data, str):
        return color_data

    color_series = pd.Series(color_data)

    unique_values = color_series.dropna().unique()

    # -------------------------
    # if all values are valid colors → pass through
    # -------------------------
    if all(is_color_like(v) for v in unique_values):
        return color_series

    # -------------------------
    # categorical mapping
    # -------------------------
    palette = list(plt.rcParams["axes.prop_cycle"].by_key()["color"])

    mapping = {
        value: palette[i % len(palette)]
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
    print(f"Extracted data for channel '{channel}': {data}")
    return data