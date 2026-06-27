"""
Scale: Mapping from data domain to visual domain.

Scales transform data values into visual attribute values (positions, colors,
sizes, etc.). They are pure transformations applied during spec building,
before the spec reaches the renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Scale:
    name: str
    params: dict[str, Any] = field(default_factory=dict)
    domain: tuple[Any, ...] | None = None
    range: tuple[Any, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Scale name must be a non-empty string")
        if not isinstance(self.params, dict):
            raise TypeError("params must be a dict")

    def transform(self, values: pd.Series) -> pd.Series:
        raise NotImplementedError("Scale must implement transform()")

    def invert(self, values: pd.Series) -> pd.Series:
        raise NotImplementedError("Scale must implement invert()")


@dataclass(frozen=True)
class ScaleContinuous(Scale):
    trans: str = "identity"

    def __init__(
        self,
        trans: str = "identity",
        domain: tuple[float, float] | None = None,
        range: tuple[float, float] | None = None,
    ) -> None:
        valid_trans = {"identity", "log", "sqrt", "reverse"}
        if trans not in valid_trans:
            raise ValueError(f"Invalid trans '{trans}'. Must be one of {valid_trans}")
        super().__init__(
            name="continuous",
            params={"trans": trans},
            domain=domain,
            range=range,
        )

    def transform(self, values: pd.Series) -> pd.Series:
        if self.params["trans"] == "identity":
            return values
        if self.params["trans"] == "log":
            return pd.Series(np.log(values), index=values.index)
        if self.params["trans"] == "sqrt":
            return pd.Series(np.sqrt(values), index=values.index)
        if self.params["trans"] == "reverse":
            return pd.Series(-values, index=values.index)
        return values

    def invert(self, values: pd.Series) -> pd.Series:
        if self.params["trans"] == "identity":
            return values
        if self.params["trans"] == "log":
            return pd.Series(np.exp(values), index=values.index)
        if self.params["trans"] == "sqrt":
            return pd.Series(values**2, index=values.index)
        if self.params["trans"] == "reverse":
            return pd.Series(-values, index=values.index)
        return values


@dataclass(frozen=True)
class ScaleOrdinal(Scale):
    palette: tuple[str, ...] = ()

    def __init__(
        self,
        palette: Sequence[str] | None = None,
        domain: tuple[Any, ...] | None = None,
        range: tuple[Any, ...] | None = None,
    ) -> None:
        super().__init__(
            name="ordinal",
            params={"palette": tuple(palette) if palette else ()},
            domain=domain,
            range=range,
        )

    def transform(self, values: pd.Series) -> pd.Series:
        palette = self.params.get("palette", ())
        if not palette:
            return values
        unique = values.unique()
        mapping = {val: palette[i % len(palette)] for i, val in enumerate(unique)}
        return pd.Series(
            [mapping.get(v, v) for v in values],
            index=values.index,
        )

    def invert(self, values: pd.Series) -> pd.Series:
        return values


@dataclass(frozen=True)
class ScaleConstant(Scale):
    value: Any = None

    def __init__(self, value: Any = None) -> None:
        super().__init__(
            name="constant",
            params={"value": value},
        )

    def transform(self, values: pd.Series) -> pd.Series:
        return pd.Series([self.params["value"]] * len(values), index=values.index)

    def invert(self, values: pd.Series) -> pd.Series:
        return values


@dataclass(frozen=True)
class ScaleDateTime(Scale):
    fmt: str = "%Y-%m-%d"

    def __init__(
        self,
        fmt: str = "%Y-%m-%d",
        domain: tuple[Any, ...] | None = None,
        range: tuple[Any, ...] | None = None,
    ) -> None:
        super().__init__(
            name="datetime",
            params={"format": fmt},
            domain=domain,
            range=range,
        )

    def transform(self, values: pd.Series) -> pd.Series:
        return values

    def invert(self, values: pd.Series) -> pd.Series:
        return values


@dataclass(frozen=True)
class ScaleNormalize(Scale):
    """Normalize numeric values to a target range (default [0, 1])."""

    def __init__(
        self,
        range_min: float = 0.0,
        range_max: float = 1.0,
    ) -> None:
        if range_min >= range_max:
            raise ValueError(f"range_min ({range_min}) must be less than range_max ({range_max})")
        super().__init__(
            name="normalize",
            params={"range_min": range_min, "range_max": range_max},
        )

    def transform(self, values: pd.Series) -> pd.Series:
        range_min = self.params["range_min"]
        range_max = self.params["range_max"]
        clean = values.dropna()
        if len(clean) == 0:
            return pd.Series([range_min] * len(values), index=values.index)
        data_min, data_max = float(clean.min()), float(clean.max())
        if data_max > data_min:
            result = (values - data_min) / (data_max - data_min)
            result = result * (range_max - range_min) + range_min
        else:
            result = pd.Series([range_min] * len(values), index=values.index)
        return result

    def invert(self, values: pd.Series) -> pd.Series:
        return values
