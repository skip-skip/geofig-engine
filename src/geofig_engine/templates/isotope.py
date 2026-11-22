"""
Isotope figure template for FigEngine.

Defines the contract for two-dimensional isotope plots with optional
color and marker encodings. Uses the geom preset registry for water
isotope reference lines (GMWL, LMWL, etc.).
"""

from collections.abc import Sequence
from typing import Any

from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.layer import Layer
from geofig_engine.core.scale import Scale
from geofig_engine.core.stat import StatIdentity
from geofig_engine.data.geom_presets import get_geom_preset_registry
from geofig_engine.data.validator import FunctionValidator
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import SourceType


ISOTOPE_DEFAULTS: dict[str, Any] = {
    "figsize": (10, 6),
    "xscale": "linear",
    "yscale": "linear",
    "grid": True,
}

ACCEPTED_CATEGORIES: list[str] = ["water_isotope"]
ACCEPTED_GEOM_KINDS: tuple[str, ...] = ("function_line",)
REQUIRED_VARIABLES: tuple[str, ...] = ("x",)


def _validate_preset_for_isotope(preset_id: str, preset) -> None:
    """Raise ValueError if a preset is not renderable by the isotope template."""
    if preset.category not in ACCEPTED_CATEGORIES:
        raise ValueError(
            f"Function '{preset_id}' category '{preset.category}' "
            f"not accepted. Requires: {ACCEPTED_CATEGORIES}"
        )

    unsupported = preset.geom_kinds - set(ACCEPTED_GEOM_KINDS)
    if unsupported:
        raise ValueError(
            f"Function '{preset_id}' geom kinds {sorted(unsupported)} "
            f"not accepted. Requires: {list(ACCEPTED_GEOM_KINDS)}"
        )

    for item in preset.items:
        if item.geom_type != "function_line":
            continue
        variables = FunctionValidator.extract_variables(item.params["func"])
        if not all(v in variables for v in REQUIRED_VARIABLES):
            raise ValueError(
                f"Function '{preset_id}' missing required variables: "
                f"{REQUIRED_VARIABLES}"
            )


def _load_functions(
    functions: Sequence[str] | None = None,
    auto_filter: bool = True,
) -> list[Layer]:
    registry = get_geom_preset_registry()

    if functions is None and auto_filter:
        return registry.auto_layers(
            category="water_isotope", geom_kinds=ACCEPTED_GEOM_KINDS
        )
    elif functions is not None:
        for preset_id in functions:
            _validate_preset_for_isotope(preset_id, registry.get(preset_id))
        return registry.layers_for(functions)
    else:
        return []


def isotope_builder(
    mapping: dict[str, SourceType] | None = None,
    settings: dict[str, Any] | None = None,
    **kwargs: Any,
) -> "TemplateRecipe":
    """Native registry builder for ``isotope`` (18.4).

    ``functions`` / ``auto_filter`` come from flat settings or direct factory
    kwargs; renderer settings merge into ``default_settings``.
    """
    from geofig_engine.engine.api import DEFAULT_TEMPLATE_MAPPING, TemplateRecipe

    options = settings or {}
    effective_mapping = (
        dict(mapping or {})
        if kwargs.get("_legacy_factory", False)
        else {**DEFAULT_TEMPLATE_MAPPING, **(mapping or {})}
    )
    func_layers = _load_functions(
        functions=kwargs.get("functions", options.get("functions")),
        auto_filter=kwargs.get("auto_filter", options.get("auto_filter", True)),
    )
    data_layer = Layer(
        geom=GeomPoint(),
        stat=StatIdentity(),
        mapping=effective_mapping,
        scales=kwargs.get("scales"),
    )
    return TemplateRecipe(
        name="isotope",
        layers=[*func_layers, data_layer],
        default_settings={**ISOTOPE_DEFAULTS, **options},
        mapping_consumed=True,
    )


def isotope(
    mapping: dict[str, SourceType] | None = None,
    scales: dict[str, Scale] | None = None,
    functions: Sequence[str] | None = None,
    auto_filter: bool = True,
) -> FigureTemplate:
    recipe = isotope_builder(
        mapping=mapping,
        scales=scales,
        functions=functions,
        auto_filter=auto_filter,
        _legacy_factory=True,
    )
    return FigureTemplate(
        name=recipe.name,
        layers=recipe.layers,
        coord=recipe.coord,
        default_settings=recipe.default_settings,
    )
