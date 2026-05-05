"""
IteratorEngine: Dataset expansion for multi-figure generation.

Generates multiple (subset_df, context) pairs by expanding over dimension values.
"""

from dataclasses import dataclass
from itertools import product
from typing import Any, Sequence, Union

import pandas as pd

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension_selector import DimensionSelector, ColumnSelector
from enum import Enum

@dataclass(frozen=True)
class DimensionIterator:
    class Mode(Enum):
        VALUE = 'value'
        DIMENSION = 'dimension'
    attribute: str
    dimensions: Sequence[str] | dict[str, Any]
    mode: Mode = Mode.DIMENSION

@dataclass(frozen=True)
class IteratorContext:
    """
    Context values for a single iteration.

    Attributes:
        values: Dict mapping dimension names to their values for this iteration.
    """

    values: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        """Get a context value with default."""
        return self.values.get(key, default)

    def __repr__(self) -> str:
        """String representation for logging."""
        if not self.values:
            return "IteratorContext(empty)"
        items = ", ".join(f"{k}={v!r}" for k, v in sorted(self.values.items()))
        return f"IteratorContext({items})"


@dataclass(frozen=True)
class IteratorResult:
    """
    Result of a single iteration.

    Attributes:
        subset_df: Filtered view of the dataset for this iteration.
        context: Context values (dimension values) for this iteration.
        iterator_key: Tuple of iterator keys used for iteration.
    """

    subset_df: pd.DataFrame
    context: IteratorContext
    iterator_key: tuple[str, ...]

def expand(
    dataset: Dataset,
    iterators: Sequence[DimensionIterator] | None = None,
) -> list[IteratorResult]:
    """
    Expand Iterators into selectors into multiple (subset, context) pairs.

    Generates all combinations of dimension values as specified by selectors.
    For each combination, creates a filtered view of the dataset.

    Args:
        dataset: Source dataset to iterate over.
        iterators: Sequence of DimensionIterator objects specifying iteration dimensions.

    Returns:
        List of IteratorResult in deterministic order.
        - Empty selectors → single result (full dataset, empty context)
        - With selectors → multiple results (one per combination)

    Raises:
        ValueError: If DimensionSelector matches no dimensions.
        KeyError: If column doesn't exist in dataset.
    """
    # Handle no iteration case
    if not iterators:
        return [
            IteratorResult(
                subset_df=dataset.dataframe,
                context=IteratorContext({}),
                iterator_key=(),
            )
        ]
    selectors = {
        iterator.attribute: ColumnSelector(iterator.dimensions) 
        if iterator.mode == DimensionIterator.Mode.DIMENSION else DimensionSelector(iterator.dimensions)
        for iterator in iterators
    }
    # Resolve selectors to column names and sort by selector key to keep ordering deterministic
    iterator_columns = dict(sorted(get_iterator_columns(dataset, selectors).items()))
    column_selector_keys = {
        name
        for name, selector in selectors.items()
        if isinstance(selector, ColumnSelector)
    }

    # Generate all combinations of context values or column names
    contexts = generate_contexts(dataset, iterator_columns, column_selector_keys)

    # Create result for each context
    results = []
    iterator_key = tuple(iterator_columns.keys())

    for context in contexts:
        subset_df = filter_by_context(
            dataset.dataframe,
            context,
            iterator_columns,
            column_selector_keys,
        )
        results.append(
            IteratorResult(
                subset_df=subset_df,
                context=context,
                iterator_key=iterator_key,
            )
        )

    return results


def get_iterator_columns(
    dataset: Dataset,
    selectors: dict[str, Union[DimensionSelector, str, list[str]]],
) -> dict[str, list[str]]:
    """
    Resolve selectors to actual column names for iteration.

    Args:
        dataset: Dataset for resolution context.
        selectors: Dict of selector specifications.

    Returns:
        Dict mapping selector name → resolved list of columns.

    Raises:
        ValueError: If DimensionSelector matches no dimensions.
        KeyError: If column doesn't exist.
    """
    result = {}

    for name, selector in selectors.items():
        if isinstance(selector, DimensionSelector):
            columns = selector.resolve(dataset)
            result[name] = columns
        elif isinstance(selector, str):
            if selector not in dataset.dataframe.columns:
                raise KeyError(f"Column '{selector}' not found in dataset")
            result[name] = [selector]
        elif isinstance(selector, list):
            missing = set(selector) - set(dataset.dataframe.columns)
            if missing:
                raise KeyError(f"Columns not found in dataset: {missing}")
            result[name] = selector
        else:
            raise TypeError(
                f"Selector must be DimensionSelector, ColumnSelector, str, or list[str], "
                f"got {type(selector)}"
            )

    return result


def generate_contexts(
    dataset: Dataset,
    iterator_columns: dict[str, list[str]],
    column_selector_keys: set[str] | None = None,
) -> list[IteratorContext]:
    """
    Generate all unique combinations of values or column names.

    For value iterators, extract unique values from the selected columns.
    For column iterators, use the selected column names directly.

    Args:
        dataset: Dataset to extract values from.
        iterator_columns: Dict mapping name → column names for that selector.
        column_selector_keys: Names of selectors that should iterate over column names.

    Returns:
        List of IteratorContext in sorted (deterministic) order.
    """
    column_selector_keys = column_selector_keys or set()
    value_combinations: dict[str, list[Any]] = {}

    for name, columns in iterator_columns.items():
        if name in column_selector_keys:
            value_combinations[name] = list(columns)
            continue

        values = set()
        for col in columns:
            values.update(dataset.dataframe[col].unique())
        value_combinations[name] = sorted(values)

    names = sorted(value_combinations.keys())
    value_lists = [value_combinations[name] for name in names]

    contexts = []
    for value_tuple in product(*value_lists):
        context_dict = dict(zip(names, value_tuple))
        contexts.append(IteratorContext(context_dict))

    return contexts


def filter_by_context(
    df: pd.DataFrame,
    context: IteratorContext,
    iterator_columns: dict[str, list[str]] | list[list[str]],
    column_selector_keys: set[str] | None = None,
) -> pd.DataFrame:
    """
    Filter dataframe to rows matching context values.

    For each value iterator, filters rows where ANY of the columns
    (in that selector's list) matches the context value.
    Column iterators do not filter rows because they select columns, not values.

    Args:
        df: Source dataframe to filter.
        context: Context values to match (dict of name → value).
        iterator_columns: Dict mapping selector names → column lists, or legacy
            list of column lists for backward compatibility.
        column_selector_keys: Selector names to skip filtering for.

    Returns:
        Filtered view of dataframe.
    """
    result_df = df
    column_selector_keys = column_selector_keys or set()
    context_items = sorted(context.values.items())

    if isinstance(iterator_columns, dict):
        for name, value in context_items:
            if name in column_selector_keys:
                continue

            columns = iterator_columns.get(name)
            if columns is None:
                raise ValueError(f"Unknown iterator column for selector '{name}'")

            mask = result_df[columns].eq(value).any(axis=1)
            result_df = result_df.loc[mask]

        return result_df

    if len(context_items) != len(iterator_columns):
        raise ValueError(
            "columns_lists must have the same number of entries as context values"
        )

    for (_, value), columns in zip(context_items, iterator_columns):
        mask = result_df[columns].eq(value).any(axis=1)
        result_df = result_df.loc[mask]

    return result_df
