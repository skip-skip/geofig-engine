from dataclasses import dataclass

import pandas as pd

from geofig_engine.core.dataset import Dataset


@dataclass(frozen=True)
class DummyDimension:
    name: str
    attributes: dict


def make_dataset() -> Dataset:
    dataframe = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "chem1": [10.0, 20.0, 30.0],
            "group": ["A", "B", "A"],
        }
    )
    dimensions = {
        "id": DummyDimension(name="id", attributes={"role": "key"}),
        "chem1": DummyDimension(name="chem1", attributes={"analyte": True}),
        "group": DummyDimension(name="group", attributes={"role": "group"}),
    }
    return Dataset(dataframe=dataframe, key_column="id", dimensions=dimensions)


def test_validate_schema_success() -> None:
    dataset = make_dataset()
    assert dataset.key_column == "id"
    assert dataset.has_dimension("chem1")
    assert dataset.dimension_names == ("id", "chem1", "group")


def test_get_column_returns_series() -> None:
    dataset = make_dataset()
    column = dataset.get_column("chem1")
    assert isinstance(column, pd.Series)
    assert column.tolist() == [10.0, 20.0, 30.0]


def test_select_columns_returns_dataframe_copy() -> None:
    dataset = make_dataset()
    selection = dataset.select_columns(["id", "group"])
    assert list(selection.columns) == ["id", "group"]
    assert selection.loc[0, "group"] == "A"


def test_filter_rows_returns_subset_dataset() -> None:
    dataset = make_dataset()
    mask = dataset.dataframe["group"] == "A"
    subset = dataset.filter_rows(mask)
    assert subset.dataframe.shape[0] == 2
    assert subset.has_dimension("group")
    assert subset.key_column == "id"


def test_unique_values_returns_series() -> None:
    dataset = make_dataset()
    unique = dataset.unique_values("group")
    assert list(unique) == ["A", "B"]


def test_select_columns_raises_for_missing_column() -> None:
    dataset = make_dataset()
    try:
        dataset.select_columns(["chem1", "missing"])
        assert False, "Expected KeyError for missing column"
    except KeyError:
        pass
