"""
Stat: Statistical transformations for data before visual encoding.

Stats are pure functions that transform a DataFrame into a new DataFrame,
preserving or deriving columns needed for downstream channel mapping.
They must not depend on rendering or scale logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Stat:
    name: str
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Stat name must be a non-empty string")
        if not isinstance(self.params, dict):
            raise TypeError("params must be a dict")

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError("Stats must implement compute()")


@dataclass(frozen=True)
class StatIdentity(Stat):
    def __init__(self) -> None:
        super().__init__(name="identity")

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        return data


@dataclass(frozen=True)
class StatFn(Stat):
    func: Callable[[pd.DataFrame], pd.DataFrame] | None = None

    def __init__(
        self,
        func: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        object.__setattr__(self, "func", func)
        super().__init__(name="fn", params=params or {})

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        if self.func is not None:
            return self.func(data)
        return data


@dataclass(frozen=True)
class StatBin(Stat):
    bins: int | str = 10
    range: tuple[float, float] | None = None
    density: bool = False
    cumulative: bool = False

    def __init__(
        self,
        column: str | None = None,
        bins: int | str = 10,
        range: tuple[float, float] | None = None,
        density: bool = False,
        cumulative: bool = False,
    ) -> None:
        object.__setattr__(self, "bins", bins)
        object.__setattr__(self, "range", range)
        object.__setattr__(self, "density", density)
        object.__setattr__(self, "cumulative", cumulative)
        super().__init__(
            name="bin",
            params={"column": column, "bins": bins, "range": range, "density": density, "cumulative": cumulative},
        )

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        column = self.params.get("column")
        if column is None or column not in data.columns:
            return data

        vals = data[column].dropna()
        bins = self.params.get("bins", 10)
        range_param = self.params.get("range")
        density = self.params.get("density", False)
        cumulative = self.params.get("cumulative", False)

        counts, bin_edges = np.histogram(vals, bins=bins, range=range_param, density=density)

        if cumulative:
            counts = np.cumsum(counts)

        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        widths = bin_edges[1:] - bin_edges[:-1]

        return pd.DataFrame({
            "x": bin_centers,
            "y": counts,
            "width": widths,
        })


@dataclass(frozen=True)
class StatCount(Stat):
    def __init__(self) -> None:
        super().__init__(name="count")

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        return data


@dataclass(frozen=True)
class StatSmooth(Stat):
    method: str = "loess"
    span: float = 0.75
    degree: int = 2

    def __init__(
        self, method: str = "loess", span: float = 0.75, degree: int = 2
    ) -> None:
        super().__init__(
            name="smooth",
            params={"method": method, "span": span, "degree": degree},
        )

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        return data


@dataclass(frozen=True)
class StatSum(Stat):
    column: str | None = None
    group: str | None = None
    sort: bool = True
    show_percent: bool = False
    show_count: bool = False
    show_name: bool = True

    def __init__(
        self,
        column: str | None = None,
        group: str | None = None,
        sort: bool = True,
        show_percent: bool = False,
        show_count: bool = False,
        show_name: bool = True,
    ) -> None:
        object.__setattr__(self, "column", column)
        object.__setattr__(self, "group", group)
        object.__setattr__(self, "sort", sort)
        object.__setattr__(self, "show_percent", show_percent)
        object.__setattr__(self, "show_count", show_count)
        object.__setattr__(self, "show_name", show_name)
        super().__init__(
            name="sum",
            params={"column": column, "group": group, "sort": sort,
                    "show_percent": show_percent, "show_count": show_count,
                    "show_name": show_name},
        )

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        column = self.params.get("column")
        group = self.params.get("group")
        if column is None or column not in data.columns:
            return data
        if group is None or group not in data.columns:
            return data

        result = data.groupby(group, observed=True)[column].sum().reset_index()
        result.columns = ["label", "y"]
        total = result["y"].sum()
        result["width"] = result["y"] / total * 2 * np.pi
        if self.params.get("sort", True):
            result = result.sort_values("y", ascending=False).reset_index(drop=True)

        show_pct = self.params.get("show_percent", False)
        show_cnt = self.params.get("show_count", False)
        show_nm = self.params.get("show_name", True)
        if show_pct or show_cnt or not show_nm:
            parts: list[str] = []
            for _, row in result.iterrows():
                pct = row["y"] / total * 100
                cnt = int(row["y"])
                name = row["label"]
                sub: list[str] = []
                if show_nm:
                    sub.append(str(name))
                if show_cnt:
                    sub.append(f"n={cnt}")
                if show_pct:
                    sub.append(f"{pct:.1f}%")
                parts.append("\n".join(sub) if sub else str(name))
            result["label"] = parts

        starts = result["y"].cumsum().shift(1).fillna(0) / total * 2 * np.pi
        result["x"] = starts + result["width"] / 2
        return result[["x", "y", "width", "label"]]


@dataclass(frozen=True)
class StatPieLabels(Stat):
    column: str | None = None
    group: str | None = None
    show_percent: bool = True
    show_count: bool = False
    label_distance: float = 1.3
    sort: bool = True

    def __init__(
        self,
        column: str | None = None,
        group: str | None = None,
        show_percent: bool = True,
        show_count: bool = False,
        label_distance: float = 1.3,
        sort: bool = True,
    ) -> None:
        object.__setattr__(self, "column", column)
        object.__setattr__(self, "group", group)
        object.__setattr__(self, "show_percent", show_percent)
        object.__setattr__(self, "show_count", show_count)
        object.__setattr__(self, "label_distance", label_distance)
        object.__setattr__(self, "sort", sort)
        super().__init__(
            name="pie_labels",
            params={
                "column": column,
                "group": group,
                "show_percent": show_percent,
                "show_count": show_count,
                "label_distance": label_distance,
                "sort": sort,
            },
        )

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        column = self.params.get("column")
        group = self.params.get("group")
        if column is None or column not in data.columns:
            return data
        if group is None or group not in data.columns:
            return data

        total = data[column].sum()
        result = data.groupby(group, observed=True)[column].sum().reset_index()
        result.columns = ["label", "count"]
        if self.params.get("sort", True):
            result = result.sort_values("count", ascending=False).reset_index(drop=True)

        result["prop"] = result["count"] / total
        result["angle"] = result["prop"].cumsum() * 2 * np.pi - result["prop"] * np.pi
        result["x"] = result["angle"]
        result["y"] = self.params.get("label_distance", 1.3)

        parts: list[str] = []
        for _, row in result.iterrows():
            label = row["label"]
            pct = row["prop"] * 100
            cnt = int(row["count"])
            if self.params.get("show_count") and self.params.get("show_percent"):
                parts.append(f"{cnt} ({pct:.1f}%)")
            elif self.params.get("show_percent"):
                parts.append(f"{pct:.1f}%")
            elif self.params.get("show_count"):
                parts.append(str(cnt))
            else:
                parts.append(str(label))
        result["label_text"] = parts
        return result[["x", "y", "label_text"]]


@dataclass(frozen=True)
class StatRadar(Stat):
    shared_axes: bool = True

    def __init__(self, shared_axes: bool = True, x_col: str = "x", y_col: str = "y", color_col: str | None = None) -> None:
        object.__setattr__(self, "shared_axes", shared_axes)
        super().__init__(
            name="radar",
            params={"shared_axes": shared_axes, "x_col": x_col, "y_col": y_col, "color_col": color_col},
        )

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        x_col = self.params.get("x_col", "x")
        y_col = self.params.get("y_col", "y")
        color_col = self.params.get("color_col")
        required = {x_col, y_col}
        if not required.issubset(data.columns):
            return data

        result = data.copy()
        result["x_label"] = result[x_col]
        result["x"] = result[x_col]
        result["y"] = result[y_col]

        if color_col is not None and color_col in result.columns:
            result = result.sort_values(color_col)
        return result
