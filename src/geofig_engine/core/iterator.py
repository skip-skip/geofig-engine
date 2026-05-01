"""
IteratorEngine: Dataset expansion for multi-figure generation.

Generates multiple (subset_df, context) pairs by expanding over dimension values.
"""

from dataclasses import dataclass
from itertools import product
from typing import Any, Union

import pandas as pd

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension_selector import DimensionSelector


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
        iterator_key: Tuple of column names used for iteration.
    """

    subset_df: pd.DataFrame
    context: IteratorContext
    iterator_key: tuple[str, ...]


def expand(
    dataset: Dataset,
    selectors: dict[str, Union[DimensionSelector, str, list[str]]],
) -> list[IteratorResult]:
    """
    Expand selectors into multiple (subset, context) pairs.

    Generates all combinations of dimension values as specified by selectors.
    For each combination, creates a filtered view of the dataset.

    Args:
        dataset: Source dataset to iterate over.
        selectors: Dict mapping names to dimension specifications:
            - DimensionSelector: iterate over matching dimensions' values
            - str: single column name
            - list[str]: multiple column names (Cartesian product)

    Returns:
        List of IteratorResult in deterministic order.
        - Empty selectors → single result (full dataset, empty context)
        - With selectors → multiple results (one per combination)

    Raises:
        ValueError: If DimensionSelector matches no dimensions.
        KeyError: If column doesn't exist in dataset.
    """
    # Handle no iteration case
    if not selectors:
        return [
            IteratorResult(
                subset_df=dataset.dataframe,
                context=IteratorContext({}),
                iterator_key=(),
            )
        ]

    # Resolve selectors to column names
    iterator_columns = get_iterator_columns(dataset, selectors)

    # Generate all unique combinations of context values
    contexts = generate_contexts(dataset, iterator_columns)

    # Create result for each context
    results = []
    iterator_key = tuple(sorted(iterator_columns.keys()))

    for context in contexts:
        subset_df = filter_by_context(
            dataset.dataframe,
            context,
            list(iterator_columns.values()),
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
            # Resolve DimensionSelector to column names
            columns = selector.resolve(dataset)
            result[name] = columns
        elif isinstance(selector, str):
            # Single column name
            if selector not in dataset.dataframe.columns:
                raise KeyError(f"Column '{selector}' not found in dataset")
            result[name] = [selector]
        elif isinstance(selector, list):
            # List of column names
            missing = set(selector) - set(dataset.dataframe.columns)
            if missing:
                raise KeyError(f"Columns not found in dataset: {missing}")
            result[name] = selector
        else:
            raise TypeError(
                f"Selector must be DimensionSelector, str, or list[str], "
                f"got {type(selector)}"
            )

    return result


def generate_contexts(
    dataset: Dataset, iterator_columns: dict[str, list[str]]
) -> list[IteratorContext]:
    """
    Generate all unique combinations of dimension values.

    For each selector, gets unique values in its columns, then generates
    Cartesian product across all selectors.

    Args:
        dataset: Dataset to extract values from.
        iterator_columns: Dict mapping name → column names for that selector.

    Returns:
        List of IteratorContext in sorted (deterministic) order.
    """
    # Get unique values for each selector
    value_combinations: dict[str, list[Any]] = {}

    for name, columns in iterator_columns.items():
        # Get all unique values across the columns
        values = set()
        for col in columns:
            values.update(dataset.dataframe[col].unique())
        value_combinations[name] = sorted(values)

    # Generate Cartesian product
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
    columns_lists: list[list[str]],
) -> pd.DataFrame:
    """
    Filter dataframe to rows matching context values.

    For each context value, filters rows where ANY of the columns
    (in that selector's list) matches the value.

    Args:
        df: Source dataframe to filter.
        context: Context values to match (dict of name → value).
        columns_lists: Lists of columns for each context key.

    Returns:
        Filtered view of dataframe.
    """
    result_df = df
    context_items = sorted(context.values.items())

    for (name, value), columns in zip(context_items, sorted(columns_lists)):
        # Filter: any of these columns should equal the value
        mask = result_df[columns].eq(value).any(axis=1)
        result_df = result_df.loc[mask]

    return result_df
