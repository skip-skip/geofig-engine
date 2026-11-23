"""Renderer-agnostic legend extraction for dashboard snapshots.

Mirrors the shape of the Matplotlib ``LegendAccumulator`` without importing
``matplotlib.pyplot`` or any renderer module. Only ``pandas`` and the existing
marker/palette constants are used.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from geofig_engine.core.spec import FigureSpec
from geofig_engine.io.markers import DEFAULT_PALETTE


VISUAL_CHANNELS = ("color", "marker", "style")

# Common CSS color names used by pipeline templates. Hex/rgb forms are
# recognized separately; categorical labels are mapped to DEFAULT_PALETTE.
_COLOR_NAMES = frozenset({
    "aqua", "black", "blue", "brown", "cyan", "darkgray", "darkgrey",
    "gold", "gray", "green", "grey", "indigo", "lightblue", "lightgray",
    "lightgrey", "magenta", "navy", "orange", "pink", "purple", "red",
    "silver", "teal", "transparent", "white", "yellow",
})
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


@dataclass(frozen=True)
class LegendEntry:
    """Plain-data counterpart of the renderer legend entry."""

    label: str
    marker: str = "o"
    color: str = "#888888"
    linestyle: str = "-"
    alpha: float = 1.0
    subgroup: str | None = None


@dataclass(frozen=True)
class LegendGroup:
    """Plain-data counterpart of the renderer legend group."""

    column: str
    entries: list[LegendEntry] = field(default_factory=list)


def _is_color_like(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip().lower()
    if text in _COLOR_NAMES:
        return True
    if text.startswith("#"):
        body = text[1:]
        return len(body) in (3, 4, 6, 8) and all(c in _HEX_DIGITS for c in body)
    return text.startswith(("rgb(", "rgba(", "hsl(", "hsla("))


def _resolve_color_series(series: pd.Series) -> pd.Series:
    """Resolve categorical color values without importing matplotlib."""
    unique = list(series.dropna().unique())
    if not unique:
        return series
    if all(_is_color_like(value) for value in unique):
        return series
    palette = itertools.cycle(DEFAULT_PALETTE)
    return series.map({value: next(palette) for value in unique})


def extract_legend(specs: list[FigureSpec]) -> list[LegendGroup]:
    """Build legend groups from spec layers, matching renderer accumulation."""
    groups: dict[str, LegendGroup] = {}

    for spec in specs:
        for layer in spec.layers:
            col_to_channels: dict[str, dict[str, pd.Series]] = {}
            for channel in VISUAL_CHANNELS:
                value = layer.visual_mapping.get(channel)
                if isinstance(value, pd.Series) and value.name:
                    col_to_channels.setdefault(value.name, {})[channel] = value
            if not col_to_channels:
                continue

            subgroup_series = layer.visual_mapping.get("subgroup")
            if not isinstance(subgroup_series, pd.Series):
                subgroup_series = None

            for column, channels in col_to_channels.items():
                raw = (
                    spec.data[column]
                    if column in spec.data.columns
                    else next(iter(channels.values()))
                )
                resolved: dict[str, Any] = {
                    name: _resolve_color_series(series) if name == "color" else series
                    for name, series in channels.items()
                }
                entries: list[LegendEntry] = []
                seen: set[Any] = set()
                for index in range(len(raw)):
                    raw_value = raw.iloc[index]
                    if pd.isna(raw_value) or raw_value in seen:
                        continue
                    seen.add(raw_value)

                    entry_kwargs: dict[str, Any] = {"label": str(raw_value)}
                    for name, series in resolved.items():
                        value = series.iloc[index] if isinstance(series, pd.Series) else series
                        if name == "style":
                            entry_kwargs["linestyle"] = value
                        elif name in VISUAL_CHANNELS:
                            entry_kwargs[name] = value
                    if subgroup_series is not None:
                        subgroup = subgroup_series.iloc[index]
                        entry_kwargs["subgroup"] = (
                            str(subgroup) if pd.notna(subgroup) else None
                        )
                    entries.append(LegendEntry(**entry_kwargs))

                existing = groups.get(column)
                if existing is None:
                    groups[column] = LegendGroup(column=column, entries=entries)
                    continue
                known = {entry.label for entry in existing.entries}
                additions = [entry for entry in entries if entry.label not in known]
                if additions:
                    groups[column] = LegendGroup(
                        column=column, entries=list(existing.entries) + additions
                    )

    return list(groups.values())


__all__ = ["LegendEntry", "LegendGroup", "extract_legend"]
