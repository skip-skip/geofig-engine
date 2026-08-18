import itertools

import pandas as pd

DEFAULT_MARKERS = ("o", "s", "D", "^", "v", "<", ">", "p", "*", "h", "x", "+")
DEFAULT_PALETTE = (
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
    "#bcbd22", "#17becf",
)


def gen_markers(
    values: list[str],
    markers: tuple[str, ...] = DEFAULT_MARKERS,
    palette: tuple[str, ...] = DEFAULT_PALETTE,
) -> dict[str, dict[str, str]]:
    combos = itertools.product(markers, palette)
    result: dict[str, dict[str, str]] = {}
    for val, (marker, color) in zip(values, combos):
        result[val] = {"marker": marker, "color": color}
    return result


def gen_markers_series(
    values: pd.Series,
    markers: tuple[str, ...] = DEFAULT_MARKERS,
    palette: tuple[str, ...] = DEFAULT_PALETTE,
) -> pd.Series:
    unique = values.unique()
    mapping = gen_markers(list(unique), markers=markers, palette=palette)
    return pd.Series(
        {v: mapping[v]["marker"] for v in unique},
        name=values.name,
    )


def gen_markers_cross_grouping(
    group1: list[str],
    group2: list[str],
    markers: tuple[str, ...] = DEFAULT_MARKERS,
    palette: tuple[str, ...] = DEFAULT_PALETTE,
) -> dict[str, dict[str, dict[str, str]]]:
    combos = itertools.product(markers, palette)
    result: dict[str, dict[str, dict[str, str]]] = {}
    for g1 in group1:
        result[g1] = {}
        for g2 in group2:
            marker, color = next(combos)
            result[g1][g2] = {"marker": marker, "color": color}
    return result
