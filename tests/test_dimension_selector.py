import pandas as pd

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.dimension_selector import DimensionSelector


def make_dataset() -> Dataset:
    dataframe = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "chem1": [10.0, 20.0, 30.0],
            "chem2": [5.0, 15.0, 25.0],
            "group": ["A", "B", "A"],
        }
    )
    dimensions = {
        "id": Dimension(name="id", labels={"role": "key"}),
        "chem1": Dimension(name="chem1", labels={"analyte": True}),
        "chem2": Dimension(name="chem2", labels={"analyte": True}),
        "group": Dimension(name="group", labels={"role": "group"}),
    }
    return Dataset(dataframe=dataframe, key_column="id", dimensions=dimensions)


def test_resolve_string_selector_returns_column_name() -> None:
    dataset = make_dataset()
    selector = DimensionSelector("chem1")

    assert selector.resolve(dataset) == ["chem1"]
    assert selector.is_explicit()
    assert not selector.is_metadata_based()


def test_resolve_sequence_selector_returns_column_names() -> None:
    dataset = make_dataset()
    selector = DimensionSelector(["chem1", "group"])

    assert selector.resolve(dataset) == ["chem1", "group"]


def test_resolve_attribute_selector_returns_matching_columns() -> None:
    dataset = make_dataset()
    selector = DimensionSelector({"analyte": True})

    assert selector.resolve(dataset) == ["chem1", "chem2"]
    assert selector.is_metadata_based()


def test_attribute_selector_raises_when_no_match() -> None:
    dataset = make_dataset()
    selector = DimensionSelector({"unit": "mg/L"})

    try:
        selector.resolve(dataset)
        assert False, "Expected ValueError for no matching dimensions"
    except ValueError:
        pass


def test_sequence_selector_raises_for_invalid_names() -> None:
    dataset = make_dataset()
    selector = DimensionSelector(["chem1", "missing"])

    try:
        selector.resolve(dataset)
        assert False, "Expected KeyError for missing column"
    except KeyError:
        pass


def test_invalid_selector_types_raise_type_error() -> None:
    try:
        DimensionSelector(123)  # type: ignore[arg-type]
        assert False, "Expected TypeError for invalid selector type"
    except TypeError:
        pass
