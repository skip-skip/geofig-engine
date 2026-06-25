"""
Stat: Statistical transformations for data before visual encoding.

Stats are pure functions that transform a DataFrame into a new DataFrame,
preserving or deriving columns needed for downstream channel mapping.
They must not depend on rendering or scale logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

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

    def __init__(
        self, bins: int | str = 10, range: tuple[float, float] | None = None
    ) -> None:
        super().__init__(
            name="bin",
            params={"bins": bins, "range": range},
        )

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        return data


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
