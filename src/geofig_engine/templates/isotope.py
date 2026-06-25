"""
Isotope figure template for FigEngine.

Defines the contract for two-dimensional isotope plots with optional
color and marker encodings. Uses the function registry for water isotope
reference lines (GMWL, LMWL, etc.).
"""

from collections.abc import Sequence
from typing import Any

from geofig_engine.core.geom import GeomFunctionLine, GeomPoint
from geofig_engine.core.layer import Layer
from geofig_engine.core.scale import Scale
from geofig_engine.core.stat import StatIdentity
from geofig_engine.data import (
    get_function_registry,
    FunctionCategory,
    FunctionType,
)
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import SourceType


ISOTOPE_DEFAULTS: dict[str, Any] = {
    "figsize": (10, 6),
    "xscale": "linear",
    "yscale": "linear",
    "grid": True,
}

ACCEPTED_CATEGORIES = [FunctionCategory.WATER_ISOTOPE]
ACCEPTED_TYPES = [FunctionType.LINEAR]
REQUIRED_VARIABLES = ("x",)


def _load_functions(
    functions: Sequence[str] | None = None,
    auto_filter: bool = True,
) -> list[Layer]:
    registry = get_function_registry()

    if functions is None and auto_filter:
        selected = registry.filter(
            category=FunctionCategory.WATER_ISOTOPE,
            func_type=FunctionType.LINEAR,
        )
    elif functions is not None:
        selected = []
        for func_id in functions:
            math_func = registry.get(func_id)
            if math_func.category not in ACCEPTED_CATEGORIES:
                raise ValueError(
                    f"Function '{func_id}' category '{math_func.category.value}' "
                    f"not accepted. Requires: {[c.value for c in ACCEPTED_CATEGORIES]}"
                )
            if math_func.func_type not in ACCEPTED_TYPES:
                raise ValueError(
                    f"Function '{func_id}' type '{math_func.func_type.value}' "
                    f"not accepted. Requires: {[t.value for t in ACCEPTED_TYPES]}"
                )
            if not all(v in math_func.variables for v in REQUIRED_VARIABLES):
                raise ValueError(
                    f"Function '{func_id}' missing required variables: {REQUIRED_VARIABLES}"
                )
            selected.append(math_func)
    else:
        selected = []

    return [
        Layer(
            geom=GeomFunctionLine(func=m.expression, label=m.label),
            stat=StatIdentity(),
            mapping={
                "color": m.color,
                "style": m.linestyle,
                "label": m.label,
            },
        )
        for m in selected
    ]


def isotope(
    mapping: dict[str, SourceType] | None = None,
    scales: dict[str, Scale] | None = None,
    functions: Sequence[str] | None = None,
    auto_filter: bool = True,
) -> FigureTemplate:
    func_layers = _load_functions(functions=functions, auto_filter=auto_filter)
    data_layer = Layer(
        geom=GeomPoint(),
        stat=StatIdentity(),
        mapping=mapping or {},
        scales=scales,
    )
    return FigureTemplate(
        layers=[*func_layers, data_layer],
        default_settings=dict(ISOTOPE_DEFAULTS),
    )
