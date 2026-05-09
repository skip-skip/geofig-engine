from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Sequence, Union

from .dataset import Dataset
from .dimension import Dimension
from geofig_engine.utils.typing import Selector
from geofig_engine.utils.validation import validate_dict, validate_sequence


@dataclass(frozen=True)
class DimensionSelector:
    selector: Selector
    def __post_init__(self) -> None:
        if isinstance(self.selector, dict):
            validate_dict(self.selector, "selector", key_type=str, allow_empty=False)
        elif isinstance(self.selector, str):
            return
        elif isinstance(self.selector, Sequence):
            if isinstance(self.selector, str):
                return
            validate_sequence(self.selector, "selector", str, allow_empty=False)
        else:
            raise TypeError(
                "selector must be a string, sequence of strings, or dict[str, Any]"
            )

    def resolve(self, dataset: Dataset) -> list[str]:
        if isinstance(self.selector, str):
            return [self._resolve_name(dataset, self.selector)]

        if isinstance(self.selector, dict):
            return self._resolve_by_attributes(dataset, self.selector)

        return self._resolve_names(dataset, self.selector)

    def is_explicit(self) -> bool:
        return isinstance(self.selector, str) or (
            isinstance(self.selector, Sequence) and not isinstance(self.selector, str)
        )

    def is_metadata_based(self) -> bool:
        return isinstance(self.selector, dict)

    def _resolve_name(self, dataset: Dataset, name: str) -> str:
        if name not in dataset.dataframe.columns:
            raise KeyError(f"Dimension '{name}' not found in dataset")
        return name

    def _resolve_names(self, dataset: Dataset, names: Sequence[str]) -> list[str]:
        missing = [name for name in names if name not in dataset.dataframe.columns]
        if missing:
            raise KeyError(f"Dimension names not found in dataset: {sorted(missing)}")
        return list(names)

    def _resolve_by_attributes(
        self, dataset: Dataset, attrs: Dict[str, Any]
    ) -> list[str]:
        result = [
            name
            for name, dimension in dataset.dimensions.items()
            if self._matches_attributes(dimension, attrs)
        ]
        if not result:
            raise ValueError(f"No dimensions match attributes selector: {attrs}")
        return result

    def _matches_attributes(self, dimension: Dimension, attrs: Dict[str, Any]) -> bool:
        for key, value in attrs.items():
            if dimension.labels.get(key) != value:
                return False
        return True

    def _validate_attribute_selector(self, attrs: Dict[str, Any]) -> None:
        for key in attrs:
            if not isinstance(key, str):
                raise TypeError("attribute selector keys must be strings")

    def _validate_name_sequence(self, names: Sequence[str]) -> None:
        for item in names:
            if not isinstance(item, str):
                raise TypeError("selector sequence items must be strings")

@dataclass(frozen=True)
class ColumnSelector(DimensionSelector):
    """Select columns to iterate over by name or metadata."""
    pass
