from geofig_engine.core.dataset import Dataset
from geofig_engine.core.iterator import DimensionIterator

from geofig_cli.state import IteratorConfig


def get_label_keys(dataset: Dataset) -> list[str]:
    labels = dataset.get_all_labels()
    return list(labels.keys())


def get_dimension_names(dataset: Dataset) -> list[str]:
    return list(dataset.get_dimension_names())


def get_selector_options(dataset: Dataset) -> list[str]:
    label_keys = get_label_keys(dataset)
    dimension_names = get_dimension_names(dataset)

    options: list[str] = []

    for key in label_keys:
        options.append(f"label:{key}")

    for name in dimension_names:
        options.append(f"dimension:{name}")

    return sorted(set(options))


def normalize_selector(selector: str) -> tuple[str, str]:
    if ":" not in selector:
        return "dimension", selector

    selector_type, selector_value = selector.split(":", 1)
    return selector_type.strip().lower(), selector_value.strip()


def build_dimension_iterator(
    config: IteratorConfig,
    dataset: Dataset,
) -> DimensionIterator:
    selector_type, selector_value = normalize_selector(config.selector)

    if config.mode == DimensionIterator.Mode.DIMENSION:
        dimensions = dataset.query_dimensions(selector_value, True)
    else:
        dimensions = [selector_value]

    return DimensionIterator(
        channel=config.channel,
        dimensions=dimensions,
        mode=config.mode,
    )