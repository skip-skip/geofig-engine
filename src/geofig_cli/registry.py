from typing import Any

from geofig_engine.templates.bivariate import BivariateTemplate
from geofig_engine.templates.isotope import IsotopeTemplate
from geofig_engine.templates.timeseries import TimeseriesTemplate


TEMPLATE_REGISTRY = {
    "timeseries": TimeseriesTemplate,
    "isotope": IsotopeTemplate,
    "bivariate": BivariateTemplate,
}


def create_template(name: str, **kwargs) -> Any:
    template_cls = TEMPLATE_REGISTRY[name]
    return template_cls(**kwargs)


def get_template_names() -> list[str]:
    return list(TEMPLATE_REGISTRY.keys())