from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Iterable, Sequence

import pandas as pd
from pandas.api.types import is_bool_dtype

if TYPE_CHECKING:
    from .dimension import Dimension
else:
    Dimension = object

DimensionsMap = Dict[str, Dimension]


@dataclass
class Dataset:
    dataframe: pd.DataFrame
    key_column: str
    dimensions: DimensionsMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.dataframe = self._normalize_dataframe(self.dataframe)
        self.validate_schema()

    def _normalize_dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("dataframe must be a pandas DataFrame")
        return dataframe.copy(deep=True)

    def validate_schema(self) -> None:
        if self.dataframe.columns.has_duplicates:
            raise ValueError("Dataset dataframe column names must be unique")

        if not isinstance(self.key_column, str):
            raise TypeError("key_column must be a string")

        if self.key_column not in self.dataframe.columns:
            raise ValueError(f"key_column '{self.key_column}' not found in dataframe columns")

        if not isinstance(self.dimensions, dict):
            raise TypeError("dimensions must be a dict[str, Dimension]")

        missing_dimensions = set(self.dimensions) - set(self.dataframe.columns)
        if missing_dimensions:
            raise ValueError(
                f"Dimensions refer to missing dataframe columns: {sorted(missing_dimensions)}"
            )

        for name, dimension in self.dimensions.items():
            if hasattr(dimension, "name") and getattr(dimension, "name") != name:
                raise ValueError(
                    f"Dimension object for '{name}' has mismatched name '{dimension.name}'"
                )

    def get_column(self, name: str) -> pd.Series:
        if name not in self.dataframe.columns:
            raise KeyError(f"Column '{name}' not found in dataset")
        return self.dataframe.loc[:, name].copy()

    def select_columns(self, names: Sequence[str]) -> pd.DataFrame:
        if isinstance(names, str) or not isinstance(names, Sequence):
            raise TypeError("names must be a sequence of column names")

        selected = list(names)
        missing_columns = set(selected) - set(self.dataframe.columns)
        if missing_columns:
            raise KeyError(f"Columns not found in dataset: {sorted(missing_columns)}")

        return self.dataframe.loc[:, selected].copy()

    def filter_rows(self, mask: Iterable[bool]) -> Dataset:
        if isinstance(mask, pd.Series):
            if not mask.index.equals(self.dataframe.index):
                raise ValueError("mask index must match the dataset index")
            if not is_bool_dtype(mask.dtype):
                raise TypeError("mask must be a pandas Series of booleans")
            boolean_mask = mask
        else:
            boolean_mask = pd.Series(mask, index=self.dataframe.index)
            if not is_bool_dtype(boolean_mask.dtype):
                raise TypeError("mask must be a sequence of booleans")

        filtered_df = self.dataframe.loc[boolean_mask].copy()
        return Dataset(
            dataframe=filtered_df,
            key_column=self.key_column,
            dimensions=self.dimensions.copy(),
        )

    def unique_values(self, dimension_name: str) -> pd.Index:
        return pd.Index(self.get_column(dimension_name).dropna().unique(), name=dimension_name)

    def has_dimension(self, name: str) -> bool:
        return name in self.dimensions

    @property
    def dimension_names(self) -> tuple[str, ...]:
        return tuple(self.dimensions.keys())

    @property
    def shape(self) -> tuple[int, int]:
        return self.dataframe.shape

    def __len__(self) -> int:
        return len(self.dataframe)
