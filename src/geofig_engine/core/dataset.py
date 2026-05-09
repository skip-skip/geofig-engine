from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Sequence

import pandas as pd
from pandas.api.types import is_bool_dtype
from openpyxl import load_workbook

from geofig_engine.utils.typing import DimensionsMap
from geofig_engine.utils.validation import (
    validate_dataframe,
    validate_dict,
    validate_sequence,
    validate_string,
)

from .dimension import Dimension

@dataclass
class Dataset:
    dataframe: pd.DataFrame
    key_column: str
    dimensions: DimensionsMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.dataframe = self._normalize_dataframe(self.dataframe)
        self.validate_schema()

    def _normalize_dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        validated = validate_dataframe(dataframe, "dataframe")
        return validated.copy(deep=True)

    def load_dataset(
        filepath: str | Path,
        key_column: str = "GENERATED_KEY",
        label_rows: int = 1,
        sheet_name: str | int = 0,
    ) -> Dataset:
        """
        Load Dataset from xlsx or csv.

        File structure:
        --------------------------------------------------
        label row(s)
        column header row
        data rows
        --------------------------------------------------

        Behavior:
        - merged Excel cells are expanded correctly
        - intentionally empty cells remain empty
        - csv files preserve blanks as-is
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(filepath)
        suffix = filepath.suffix.lower()
        # --------------------------------------------------
        # XLSX
        # --------------------------------------------------
        if suffix == ".xlsx":
            workbook = load_workbook(
                filepath,
                data_only=True,
            )
            if isinstance(sheet_name, int):
                worksheet = workbook.worksheets[sheet_name]
            else:
                worksheet = workbook[sheet_name]
            # ----------------------------------------------
            # extract worksheet values
            # ----------------------------------------------
            raw_data = [
                [cell for cell in row]
                for row in worksheet.iter_rows(values_only=True)
            ]
            raw = pd.DataFrame(raw_data)
            # ----------------------------------------------
            # expand merged cells ONLY
            # ----------------------------------------------
            if (label_rows > 0):
                for merged_range in worksheet.merged_cells.ranges:
                    min_col = merged_range.min_col - 1
                    max_col = merged_range.max_col - 1
                    min_row = merged_range.min_row - 1
                    max_row = merged_range.max_row - 1
                    # only process dimension rows
                    if min_row >= label_rows:
                        continue
                    value = raw.iat[min_row, min_col]
                    for row_idx in range(min_row, max_row + 1):
                        for col_idx in range(min_col, max_col + 1):
                            raw.iat[row_idx, col_idx] = value

        # --------------------------------------------------
        # CSV
        # --------------------------------------------------
        elif suffix == ".csv":
            raw = pd.read_csv(
                filepath,
                header=None,
            )
        # --------------------------------------------------
        # unsupported
        # --------------------------------------------------
        else:
            raise ValueError(
                "Only .xlsx and .csv files are supported"
            )
        # --------------------------------------------------
        # split sections
        # --------------------------------------------------
        header_row = label_rows
        dimension_df = raw.iloc[:label_rows].copy()
        column_names = (
            raw.iloc[header_row]
            .astype(str)
            .tolist()
        )
        data = raw.iloc[header_row + 1 :].copy()
        data.columns = column_names
        data = data.reset_index(drop=True)
        # --------------------------------------------------
        # build dimensions
        # --------------------------------------------------
        dimensions: dict[str, Dimension] = {}
        for col_idx, column_name in enumerate(column_names):
            labels: dict[str, Any] = {}
            for dim_idx in range(label_rows):
                value = dimension_df.iat[dim_idx, col_idx]
                if pd.isna(value):
                    continue
                labels[value] = True
            dimensions[column_name] = Dimension(
                name=column_name,
                labels=labels,
            )
        # --------------------------------------------------
        # build dataset
        # --------------------------------------------------
        if key_column not in data.columns:
            data[key_column] = range(len(data))
        return Dataset(
            dataframe=data,
            key_column=key_column,
            dimensions=dimensions,
        )
    
    def validate_schema(self) -> None:
        if self.dataframe.columns.has_duplicates:
            raise ValueError("Dataset dataframe column names must be unique")

        validate_string(self.key_column, "key_column", allow_empty=False)

        if self.key_column not in self.dataframe.columns:
            raise ValueError(f"key_column '{self.key_column}' not found in dataframe columns")

        validated_dimensions = validate_dict(
            self.dimensions,
            "dimensions",
            key_type=str,
            allow_empty=True,
        )

        missing_dimensions = set(validated_dimensions) - set(self.dataframe.columns)
        if missing_dimensions:
            raise ValueError(
                f"Dimensions refer to missing dataframe columns: {sorted(missing_dimensions)}"
            )

        for name, dimension in validated_dimensions.items():
            if hasattr(dimension, "name") and getattr(dimension, "name") != name:
                raise ValueError(
                    f"Dimension object for '{name}' has mismatched name '{dimension.name}'"
                )

    def get_column(self, name: str) -> pd.Series:
        if name not in self.dataframe.columns:
            raise KeyError(f"Column '{name}' not found in dataset")
        return self.dataframe.loc[:, name].copy()

    def select_columns(self, names: Sequence[str]) -> pd.DataFrame:
        validate_sequence(names, "names", str, allow_empty=False)

        selected = list(names)
        missing_columns = set(selected) - set(self.dataframe.columns)
        if missing_columns:
            raise KeyError(f"Columns not found in dataset: {sorted(missing_columns)}")

        return self.dataframe.loc[:, selected].copy()

    def query_dimensions(self, label: str, value: str)-> list[str]:
        dimensions = []
        for name, dimension in self.dimensions.items():
            if dimension.has_label(label) and dimension.labels.get(label) == value:
                dimensions.append(name)
        return dimensions
    
    def get_dimension_names(self) -> dict[str, Dimension]:
        return self.dimensions.keys()
    
    def get_all_labels(self) -> dict[str, Any]:
        labels = {}
        for dimension in self.dimensions.values():
            labels.update(dimension.labels)
        return labels

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
