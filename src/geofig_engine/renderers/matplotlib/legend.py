from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt

from geofig_engine.core.spec import FigureSpec
from geofig_engine.renderers.matplotlib.util import resolve_color_series


VISUAL_CHANNELS = ("color", "marker", "style")


@dataclass(frozen=True)
class LegendEntry:
    label: str
    marker: str = "o"
    color: str = "#888888"
    linestyle: str = "-"
    alpha: float = 1.0


@dataclass(frozen=True)
class LegendGroup:
    column: str
    entries: list[LegendEntry] = field(default_factory=list)


class LegendAccumulator:
    def __init__(self) -> None:
        self._groups: dict[str, LegendGroup] = {}

    def add_from_spec(self, spec: FigureSpec) -> None:
        for layer_spec in spec.layers:
            col_to_channels: dict[str, dict[str, pd.Series]] = {}
            for channel in VISUAL_CHANNELS:
                val = layer_spec.visual_mapping.get(channel)
                if val is not None and isinstance(val, pd.Series) and val.name:
                    col = val.name
                    if col not in col_to_channels:
                        col_to_channels[col] = {}
                    col_to_channels[col][channel] = val

            if not col_to_channels:
                continue

            for col, channels in col_to_channels.items():
                # Use original data if available, otherwise stat-produced Series
                if col in spec.data.columns:
                    raw_col = spec.data[col]
                else:
                    raw_col = next(iter(channels.values()))
                entries: list[LegendEntry] = []
                seen: set[Any] = set()

                # Resolve color channels once for the full Series
                resolved_channels: dict[str, pd.Series | Any] = {}
                for ch_name, ch_series in channels.items():
                    if ch_name == "color":
                        resolved_channels[ch_name] = resolve_color_series(ch_series)
                    else:
                        resolved_channels[ch_name] = ch_series

                for i in range(len(raw_col)):
                    raw_val = raw_col.iloc[i]
                    if raw_val in seen:
                        continue
                    seen.add(raw_val)

                    marker: str = "o"
                    color: str = "#888888"
                    linestyle: str = "-"

                    for ch_name, resolved in resolved_channels.items():
                        vis_val = resolved.iloc[i] if isinstance(resolved, pd.Series) else resolved
                        if ch_name == "color":
                            color = vis_val
                        elif ch_name == "marker":
                            marker = vis_val
                        elif ch_name == "style":
                            linestyle = vis_val

                    entries.append(LegendEntry(
                        label=str(raw_val),
                        marker=marker,
                        color=color,
                        linestyle=linestyle,
                    ))

                existing = self._groups.get(col)
                if existing is not None:
                    seen_labels = {e.label for e in existing.entries}
                    new_entries = [e for e in entries if e.label not in seen_labels]
                    if new_entries:
                        self._groups[col] = LegendGroup(
                            col, list(existing.entries) + new_entries
                        )
                else:
                    self._groups[col] = LegendGroup(col, entries)

    @property
    def groups(self) -> list[LegendGroup]:
        return list(self._groups.values())

    def clear(self) -> None:
        self._groups.clear()


def _make_handle(entry: LegendEntry) -> Line2D:
    if entry.linestyle and entry.linestyle not in ("none", ""):
        return Line2D(
            [0], [0],
            color=entry.color,
            linestyle=entry.linestyle,
            marker=entry.marker or "",
            markersize=6,
            linewidth=2,
        )
    return Line2D(
        [0], [0],
        marker=entry.marker or "o",
        color=entry.color,
        linestyle="none",
        markersize=8,
    )


def render_legend_figure(
    legend_data: LegendAccumulator,
    figsize: tuple[float, float] = (6, 4),
) -> plt.Figure:
    groups = list(legend_data.groups)
    if not groups:
        fig, ax = plt.subplots(figsize=(2, 1))
        ax.axis("off")
        plt.close(fig)
        return fig

    n_groups = len(groups)
    max_entries = max(len(g.entries) for g in groups)
    fig, axes = plt.subplots(1, n_groups, figsize=figsize)
    if n_groups == 1:
        axes = [axes]

    for ax, group in zip(axes, groups):
        ax.axis("off")
        handles: list[Line2D | Rectangle] = []
        labels: list[str] = []

        handles.append(Rectangle((0, 0), 0, 0, alpha=0))
        labels.append(group.column)

        for entry in group.entries:
            handles.append(_make_handle(entry))
            labels.append(entry.label)

        for _ in range(max_entries - len(group.entries)):
            handles.append(Rectangle((0, 0), 0, 0, alpha=0))
            labels.append("")

        legend = ax.legend(
            handles, labels,
            loc="center",
            frameon=False,
            handletextpad=1.5,
            labelspacing=1.2,
            fontsize=9,
        )
        if legend.get_texts():
            legend.get_texts()[0].set_weight("bold")

    plt.subplots_adjust(wspace=0.4)
    plt.close(fig)
    return fig
