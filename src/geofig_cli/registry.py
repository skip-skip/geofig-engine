from typing import Any

from geofig_engine.templates import bivariate, isotope, timeseries


TEMPLATE_REGISTRY = {
    "timeseries": timeseries,
    "isotope": isotope,
    "bivariate": bivariate,
}


def create_template(name: str, **kwargs) -> Any:
    factory = TEMPLATE_REGISTRY[name]
    return factory(**kwargs)


def get_template_names() -> list[str]:
    return list(TEMPLATE_REGISTRY.keys())
