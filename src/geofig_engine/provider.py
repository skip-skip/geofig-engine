"""
DataProvider contract (Phase 15 — interoperability M1).

The single input abstraction the engine consumes: a structural
``DataProvider`` Protocol plus two concrete implementations. Provider views
from ``geodata`` (and result tables from ``geochemmodel``) satisfy the
Protocol duck-typed — this module never imports those packages.
"""

from __future__ import annotations

from itertools import product
from typing import Any, Protocol, runtime_checkable

import pandas as pd

from geofig_engine.core.dataset import Dataset


@runtime_checkable
class DataProvider(Protocol):
    """Structural contract for every input the engine consumes.

    Implementers are duck-typed; the engine never imports the provider's
    package. Member semantics:

    - ``columns`` — the concrete column names available on the provider.
    - ``resolve(selector)`` — maps a ``DimensionSelector`` (or plain column
      name / list of names) to the concrete column strings it denotes.
    - ``expand(iterators)`` — multi-figure expansion: yields one
      ``(frame, context)`` pair per iterator combination; ``iterators=None``
      yields the single ``(frame, {})`` pair. The engine calls this and never
      re-implements iterator expansion.
    - ``subset(...)`` — returns a **new** provider (never mutates the input),
      row-filtered by column values (exact match; ``in`` list) and optionally
      restricted to ``columns``.
    - ``unique_values(column)`` — sorted unique values for a column.
    - ``dimensions(column)`` — column metadata labels (``{}`` when the
      provider has no metadata plane).
    """

    @property
    def columns(self) -> list[str]: ...

    def resolve(self, selector) -> list[str]: ...

    def expand(
        self, iterators: list | None = None
    ) -> list[tuple[pd.DataFrame, dict]]: ...

    def subset(self, *, columns=None, **filters) -> DataProvider: ...

    def unique_values(self, column: str) -> list: ...

    def dimensions(self, column: str) -> dict: ...


def _require_column(name: str, frame: pd.DataFrame) -> None:
    """Raise ``KeyError`` unless ``name`` is a column of ``frame``."""
    if not isinstance(name, str):
        raise TypeError(f"column names must be strings, got {type(name).__name__}")
    if name not in frame.columns:
        raise KeyError(f"Column '{name}' not found in provider")


def _matches_attributes(dimension: Any, attrs: dict[str, Any]) -> bool:
    """Match a metadata object (or plain labels dict) against an attribute selector."""
    labels = (
        dimension
        if isinstance(dimension, dict)
        else getattr(dimension, "labels", {})
    )
    for key, value in attrs.items():
        if labels.get(key) != value:
            return False
    return True


def _resolve_columns(
    selector: Any,
    frame: pd.DataFrame,
    dimensions: dict | None = None,
) -> list[str]:
    """Resolve a selector to concrete column names (minimal duck check).

    Supported forms:

    - column name: ``"chem1"``
    - ``(kind, column)`` tuple: ``("column", "chem1")``
    - ``DimensionSelector``-like object (anything exposing a ``selector``
      attribute, e.g. ``core.dimension_selector.DimensionSelector``)
    - explicit list of names: ``["chem1", "chem2"]``
    - attribute-based dict: ``{"analyte": True}`` (requires metadata via
      ``dimensions``; ``KeyError``/``ValueError`` otherwise)

    Unknown columns raise ``KeyError`` with a descriptive message.
    """
    if isinstance(selector, str):
        _require_column(selector, frame)
        return [selector]

    # "(kind, column)" tuple form, e.g. ("column", "chem1")
    if (
        isinstance(selector, tuple)
        and len(selector) == 2
        and isinstance(selector[0], str)
        and isinstance(selector[1], str)
    ):
        _require_column(selector[1], frame)
        return [selector[1]]

    # DimensionSelector-like duck check (any object exposing `selector`)
    inner = getattr(selector, "selector", None)
    if inner is not None and not isinstance(selector, (list, tuple)):
        return _resolve_columns(inner, frame, dimensions)

    if isinstance(selector, (list, tuple)):
        names = list(selector)
        for name in names:
            _require_column(name, frame)
        return names

    if isinstance(selector, dict):
        if not dimensions:
            raise ValueError(
                "No dimension metadata available to resolve attribute "
                f"selector: {selector}"
            )
        result = [
            name
            for name, dimension in dimensions.items()
            if _matches_attributes(dimension, selector)
        ]
        if not result:
            raise ValueError(f"No dimensions match attributes selector: {selector}")
        return result

    raise TypeError(f"Unsupported selector: {selector!r}")


def _subset_frame(
    frame: pd.DataFrame,
    *,
    columns: list[str] | str | None = None,
    **filters: Any,
) -> pd.DataFrame:
    """Filter ``frame`` by exact-match / ``in``-list column values.

    ``columns`` optionally restricts the returned frame's columns; the
    original ``frame`` is never mutated (a filtered copy is returned).
    """
    mask = pd.Series(True, index=frame.index)
    for name, value in filters.items():
        _require_column(name, frame)
        if isinstance(value, (list, tuple, set, frozenset)):
            mask &= frame[name].isin(value)
        else:
            mask &= frame[name].eq(value)

    result = frame.loc[mask].copy()

    if columns is not None:
        if isinstance(columns, str):
            columns = [columns]
        missing = set(columns) - set(frame.columns)
        if missing:
            raise KeyError(f"Columns not found in provider: {sorted(missing)}")
        result = result[list(columns)]

    return result


def _expand_frame(
    frame: pd.DataFrame,
    iterators: list,
    dimensions: dict | None = None,
) -> list[tuple[pd.DataFrame, dict]]:
    """Expand ``frame`` into ``(subset_df, context)`` pairs, one per iterator.

    Mirrors the legacy ``core.iterator.expand`` semantics: DIMENSION-mode
    iterators produce one context per selected column name (no row filtering);
    VALUE-mode iterators produce one context per unique value across their
    columns (rows filtered to the matching values). Ordering is deterministic
    (sorted channels / values).
    """
    from geofig_engine.core.iterator import DimensionIterator

    iterator_columns: dict[str, list[str]] = {}
    column_selector_keys: set[str] = set()

    for iterator in iterators:
        channel = getattr(iterator, "channel", None)
        if channel is None or not isinstance(channel, str):
            raise TypeError("iterators must expose a string 'channel'")
        columns = _resolve_columns(
            getattr(iterator, "dimensions", None),
            frame,
            dimensions,
        )
        iterator_columns[channel] = columns
        mode = getattr(iterator, "mode", DimensionIterator.Mode.DIMENSION)
        mode = getattr(mode, "value", mode)  # normalize Enum → str for duck-types
        if mode == "dimension":
            column_selector_keys.add(channel)

    iterator_columns = dict(sorted(iterator_columns.items()))

    value_combinations: dict[str, list[Any]] = {}
    for name, columns in iterator_columns.items():
        if name in column_selector_keys:
            value_combinations[name] = list(columns)
        else:
            values: set[Any] = set()
            for col in columns:
                values.update(frame[col].dropna().unique())
            value_combinations[name] = sorted(values)

    names = sorted(value_combinations)
    value_lists = [value_combinations[name] for name in names]

    results: list[tuple[pd.DataFrame, dict]] = []
    for value_tuple in product(*value_lists):
        context = dict(zip(names, value_tuple))
        mask = pd.Series(True, index=frame.index)
        for name, value in sorted(context.items()):
            if name in column_selector_keys:
                continue
            mask &= frame[iterator_columns[name]].eq(value).any(axis=1)
        results.append((frame.loc[mask], context))

    return results


class DataFrameProvider:
    """Wrap a raw ``pandas.DataFrame`` for standalone engine use.

    ``resolve`` is identity-only (column names), ``dimensions`` returns
    ``{}`` (no metadata plane at this layer), and ``expand`` starts from a
    single context. The wrapped frame is copied so provider views never
    mutate (or observe mutation of) the caller's frame.
    """

    def __init__(self, dataframe: pd.DataFrame) -> None:
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("dataframe must be a pandas DataFrame")
        self._dataframe = dataframe.copy()

    @property
    def columns(self) -> list[str]:
        return list(self._dataframe.columns)

    def resolve(self, selector) -> list[str]:
        return _resolve_columns(selector, self._dataframe)

    def expand(
        self, iterators: list | None = None
    ) -> list[tuple[pd.DataFrame, dict]]:
        if iterators is None or len(iterators) == 0:
            return [(self._dataframe, {})]
        return _expand_frame(self._dataframe, iterators)

    def subset(self, *, columns=None, **filters) -> "DataFrameProvider":
        return DataFrameProvider(
            _subset_frame(self._dataframe, columns=columns, **filters)
        )

    def unique_values(self, column: str) -> list:
        _require_column(column, self._dataframe)
        return sorted(self._dataframe[column].dropna().unique().tolist())

    def dimensions(self, column: str) -> dict:
        return {}


class DatasetProvider(DataFrameProvider):
    """Adapt a legacy ``Dataset`` to the ``DataProvider`` contract.

    The Dataset's dataframe powers the standard provider members (mirroring
    ``DataFrameProvider``); ``dimensions(column)`` reports the Dataset's
    dimension labels for that column and attribute-based selectors resolve
    against them. Used by the legacy engine-adaptation path and deprecated
    code only.
    """

    def __init__(self, dataset: Dataset) -> None:
        super().__init__(dataset.dataframe)
        self._dimensions = dict(dataset.dimensions)

    @classmethod
    def _from_parts(
        cls, dataframe: pd.DataFrame, dimensions: dict
    ) -> "DatasetProvider":
        """Build a provider from a (already-filtered) frame + dimension map."""
        obj = cls.__new__(cls)
        DataFrameProvider.__init__(obj, dataframe)
        obj._dimensions = dict(dimensions)
        return obj

    def resolve(self, selector) -> list[str]:
        return _resolve_columns(selector, self._dataframe, self._dimensions)

    def expand(
        self, iterators: list | None = None
    ) -> list[tuple[pd.DataFrame, dict]]:
        if iterators is None or len(iterators) == 0:
            return [(self._dataframe, {})]
        return _expand_frame(self._dataframe, iterators, self._dimensions)

    def subset(self, *, columns=None, **filters) -> "DatasetProvider":
        return DatasetProvider._from_parts(
            _subset_frame(self._dataframe, columns=columns, **filters),
            self._dimensions,
        )

    def dimensions(self, column: str) -> dict:
        dimension = self._dimensions.get(column)
        if dimension is None:
            return {}
        return dict(getattr(dimension, "labels", {}))