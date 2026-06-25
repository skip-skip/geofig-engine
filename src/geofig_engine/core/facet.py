"""
Facet: Subplot splitting strategies for multi-panel figures.

Facets divide a dataset into subsets, each rendered as a separate panel
within a single figure. They are distinct from the IteratorEngine, which
generates multiple independent figures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import pandas as pd

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension_selector import DimensionSelector


@dataclass(frozen=True)
class Facet:
    name: str
    by: tuple[str, ...] = ()
    scales: str = "fixed"
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Facet name must be a non-empty string")
        if self.scales not in ("fixed", "free", "free_x", "free_y"):
            raise ValueError(
                f"Invalid scales '{self.scales}'. Must be one of: fixed, free, free_x, free_y"
            )

    def split(self, dataset: Dataset) -> list[tuple[pd.DataFrame, dict[str, Any]]]:
        raise NotImplementedError("Facet must implement split()")


@dataclass(frozen=True)
class FacetNull(Facet):
    def __init__(self) -> None:
        super().__init__(name="null", scales="fixed")

    def split(self, dataset: Dataset) -> list[tuple[pd.DataFrame, dict[str, Any]]]:
        return [(dataset.dataframe, {})]


@dataclass(frozen=True)
class FacetWrap(Facet):
    ncol: int = 0
    nrow: int = 0

    def __init__(
        self,
        by: Sequence[str] | str,
        ncol: int = 0,
        nrow: int = 0,
        scales: str = "fixed",
    ) -> None:
        if isinstance(by, str):
            by = (by,)
        super().__init__(
            name="wrap",
            by=tuple(by),
            scales=scales,
            params={"ncol": ncol, "nrow": nrow},
        )

    def split(self, dataset: Dataset) -> list[tuple[pd.DataFrame, dict[str, Any]]]:
        if not self.by:
            return [(dataset.dataframe, {})]

        results: list[tuple[pd.DataFrame, dict[str, Any]]] = []
        grouped = dataset.dataframe.groupby(list(self.by), sort=True)
        for keys, subset in grouped:
            keys_tuple = keys if isinstance(keys, tuple) else (keys,)
            if len(self.by) == 1:
                context = {self.by[0]: keys_tuple[0]}
            else:
                context = dict(zip(self.by, keys_tuple))
            results.append((subset, context))
        return results


@dataclass(frozen=True)
class FacetGrid(Facet):
    def __init__(
        self,
        row: str,
        col: str,
        scales: str = "fixed",
    ) -> None:
        super().__init__(
            name="grid",
            by=(row, col),
            scales=scales,
            params={"row": row, "col": col},
        )

    def split(self, dataset: Dataset) -> list[tuple[pd.DataFrame, dict[str, Any]]]:
        if not self.by or len(self.by) < 2:
            return [(dataset.dataframe, {})]

        row_col = self.params
        row_key = row_col["row"]
        col_key = row_col["col"]

        results: list[tuple[pd.DataFrame, dict[str, Any]]] = []
        grouped = dataset.dataframe.groupby([row_key, col_key], sort=True)
        for keys, subset in grouped:
            row_val, col_val = keys if isinstance(keys, tuple) else (keys, None)
            results.append((subset, {row_key: row_val, col_key: col_val}))
        return results
