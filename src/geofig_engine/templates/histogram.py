from typing import Any

from geofig_engine.core.geom import GeomBar
from geofig_engine.core.layer import Layer
from geofig_engine.core.scale import Scale
from geofig_engine.core.stat import StatBin
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import SourceType


HISTOGRAM_DEFAULTS: dict[str, Any] = {
    "figsize": (10, 6),
    "xscale": "linear",
    "yscale": "linear",
    "grid": True,
}


def histogram_builder(
    mapping: dict[str, SourceType] | None = None,
    settings: dict[str, Any] | None = None,
    **kwargs: Any,
) -> "TemplateRecipe":
    """Native registry builder for ``histogram`` (18.4).

    ``bins`` / ``density`` / ``cumulative`` may come from flat ``settings``
    keys or be passed directly by the compatibility factory. Renderer settings
    merge into ``default_settings``; the mapping is bound here so stat-derived
    channels keep pointing at the binned output.
    """
    from geofig_engine.engine.api import DEFAULT_TEMPLATE_MAPPING, TemplateRecipe

    options = settings or {}
    effective_mapping = (
        dict(mapping or {})
        if kwargs.get("_legacy_factory", False)
        else {**DEFAULT_TEMPLATE_MAPPING, **(mapping or {})}
    )
    x_col = effective_mapping.get("x")
    if x_col is None:
        raise ValueError("histogram template requires 'x' in mapping")

    stat_mapping: dict[str, SourceType] = {
        "x": "x",
        "y": "y",
        "width": "width",
    }
    if "color" in effective_mapping:
        stat_mapping["color"] = effective_mapping["color"]
    if "alpha" in effective_mapping:
        stat_mapping["alpha"] = effective_mapping["alpha"]

    return TemplateRecipe(
        name="histogram",
        layers=[
            Layer(
                geom=GeomBar(),
                stat=StatBin(
                    column=str(x_col),
                    bins=kwargs.get("bins", options.get("bins", 10)),
                    density=kwargs.get("density", options.get("density", False)),
                    cumulative=kwargs.get(
                        "cumulative", options.get("cumulative", False)
                    ),
                ),
                mapping=stat_mapping,
                scales=kwargs.get("scales"),
            ),
        ],
        default_settings={**HISTOGRAM_DEFAULTS, **options},
        mapping_consumed=True,
    )


def histogram(
    mapping: dict[str, SourceType] | None = None,
    scales: dict[str, Scale] | None = None,
    bins: int | str = 10,
    density: bool = False,
    cumulative: bool = False,
) -> FigureTemplate:
    recipe = histogram_builder(
        mapping=mapping,
        scales=scales,
        bins=bins,
        density=density,
        cumulative=cumulative,
        _legacy_factory=True,
    )
    return FigureTemplate(
        name=recipe.name,
        layers=recipe.layers,
        coord=recipe.coord,
        default_settings=recipe.default_settings,
    )
