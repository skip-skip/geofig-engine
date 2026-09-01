from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt

from geofig_engine.core.spec import FigureSpec
from geofig_engine.io.markers import DEFAULT_MARKERS, DEFAULT_PALETTE, gen_markers, gen_markers_series
from geofig_engine.renderers.matplotlib.util import resolve_color_series


VISUAL_CHANNELS = ("color", "marker", "style")


@dataclass(frozen=True)
class LegendEntry:
    label: str
    marker: str = "o"
    color: str = "#888888"
    linestyle: str = "-"
    alpha: float = 1.0
    subgroup: str | None = None


@dataclass(frozen=True)
class LegendGroup:
    column: str
    entries: list[LegendEntry] = field(default_factory=list)

    def set_order(self, labels: list[str]) -> LegendGroup:
        order_map = {lbl: i for i, lbl in enumerate(labels)}
        sorted_entries = sorted(
            self.entries,
            key=lambda e: order_map.get(e.label, len(order_map)),
        )
        return LegendGroup(column=self.column, entries=sorted_entries)

    def filter_entries(self, keep_labels: set[str] | None = None, drop_labels: set[str] | None = None) -> LegendGroup:
        entries = self.entries
        if keep_labels is not None:
            entries = [e for e in entries if e.label in keep_labels]
        if drop_labels is not None:
            entries = [e for e in entries if e.label not in drop_labels]
        return LegendGroup(column=self.column, entries=entries)


def build_dimension_legend(
    data: pd.DataFrame,
    color_col: str | None = None,
    marker_col: str | None = None,
    linetype_col: str | None = None,
    subgroup_col: str | None = None,
    palette: tuple[str, ...] = DEFAULT_PALETTE,
    markers: tuple[str, ...] = DEFAULT_MARKERS,
) -> list[LegendGroup]:
    groups: list[LegendGroup] = []

    for col, channel in [(color_col, "color"), (marker_col, "marker"), (linetype_col, "style")]:
        if col is None or col not in data.columns:
            continue
        unique = data[col].unique()
        entries: list[LegendEntry] = []
        marker_iter = itertools.cycle(markers)
        color_iter = itertools.cycle(palette)

        for val in unique:
            sub = None
            if subgroup_col and subgroup_col in data.columns:
                sub_vals = data.loc[data[col] == val, subgroup_col].unique()
                sub = str(sub_vals[0]) if len(sub_vals) == 1 else None

            kwargs: dict[str, Any] = {"label": str(val)}
            if channel == "color":
                kwargs["color"] = next(color_iter)
                kwargs["marker"] = next(marker_iter) if marker_col is None else "o"
            elif channel == "marker":
                kwargs["marker"] = next(marker_iter)
            elif channel == "style":
                kwargs["linestyle"] = "--" if len(entries) % 2 == 0 else ":"
            if sub:
                kwargs["subgroup"] = sub

            entries.append(LegendEntry(**kwargs))

        groups.append(LegendGroup(column=col, entries=entries))

    return groups


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

            subgroup_series: pd.Series | None = None
            sg_val = layer_spec.visual_mapping.get("subgroup")
            if sg_val is not None and isinstance(sg_val, pd.Series):
                subgroup_series = sg_val

            for col, channels in col_to_channels.items():
                if col in spec.data.columns:
                    raw_col = spec.data[col]
                else:
                    raw_col = next(iter(channels.values()))
                entries: list[LegendEntry] = []
                seen: set[Any] = set()

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
                    subgroup: str | None = None

                    for ch_name, resolved in resolved_channels.items():
                        vis_val = resolved.iloc[i] if isinstance(resolved, pd.Series) else resolved
                        if ch_name == "color":
                            color = vis_val
                        elif ch_name == "marker":
                            marker = vis_val
                        elif ch_name == "style":
                            linestyle = vis_val

                    if subgroup_series is not None:
                        sg = subgroup_series.iloc[i]
                        subgroup = str(sg) if pd.notna(sg) else None

                    entries.append(LegendEntry(
                        label=str(raw_val),
                        marker=marker,
                        color=color,
                        linestyle=linestyle,
                        subgroup=subgroup,
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
    fontsize: float = 9,
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

        current_subgroup: str | None = None
        for entry in group.entries:
            if entry.subgroup is not None and entry.subgroup != current_subgroup:
                current_subgroup = entry.subgroup
                handles.append(Rectangle((0, 0), 0, 0, alpha=0))
                labels.append(f"  {current_subgroup}")

            handles.append(_make_handle(entry))
            labels.append(entry.label)

        pad_n = max_entries - len([e for e in group.entries if e.subgroup is None])
        for _ in range(pad_n):
            handles.append(Rectangle((0, 0), 0, 0, alpha=0))
            labels.append("")

        legend = ax.legend(
            handles, labels,
            loc="center",
            frameon=False,
            handletextpad=1.5,
            labelspacing=1.2,
            fontsize=fontsize,
        )
        if legend.get_texts():
            legend.get_texts()[0].set_weight("bold")
            for t in legend.get_texts()[1:]:
                txt = t.get_text()
                if txt.startswith("  "):
                    t.set_weight("semibold")
                    t.set_fontsize(fontsize - 1)

    plt.subplots_adjust(wspace=0.4)
    plt.close(fig)
    return fig
