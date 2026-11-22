from typing import Any

from geofig_engine.core.geom import GeomAbline, GeomHSpan, GeomPoint, GeomText, GeomVSpan
from geofig_engine.core.layer import Layer
from geofig_engine.core.scale import Scale
from geofig_engine.core.stat import StatIdentity
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import SourceType


NPR_NNP_DEFAULTS: dict[str, Any] = {
    "figsize": (8, 8),
    "title": "NPR vs NNP — ARD Classification",
    "grid": True,
    "xlabel": "NPR (Neutralisation Potential Ratio)",
    "ylabel": "NNP (Net Neutralisation Potential)",
}


def npr_nnp_builder(
    mapping: dict[str, SourceType] | None = None,
    settings: dict[str, Any] | None = None,
    **kwargs: Any,
) -> "TemplateRecipe":
    """Native registry builder for ``npr_nnp`` (18.4).

    ``npr_crit`` / ``nnp_crit`` come from flat settings or direct factory
    kwargs; renderer settings merge into ``default_settings``.
    """
    from geofig_engine.engine.api import DEFAULT_TEMPLATE_MAPPING, TemplateRecipe

    options = settings or {}
    effective_mapping = (
        dict(mapping or {})
        if kwargs.get("_legacy_factory", False)
        else {**DEFAULT_TEMPLATE_MAPPING, **(mapping or {})}
    )
    npr_crit = kwargs.get("npr_crit", options.get("npr_crit", 3))
    nnp_crit = kwargs.get("nnp_crit", options.get("nnp_crit", 20))
    npr_low = 1
    npr_high = npr_crit
    nnp_low = -nnp_crit
    nnp_high = nnp_crit

    return TemplateRecipe(
        name="npr_nnp",
        layers=[
            Layer(
                geom=GeomVSpan(),
                stat=StatIdentity(),
                mapping={
                    "xmin": npr_low, "xmax": npr_high,
                    "color": "gray", "alpha": 1.0,
                },
                zorder=0,
            ),
            Layer(
                geom=GeomHSpan(),
                stat=StatIdentity(),
                mapping={
                    "ymin": nnp_low, "ymax": nnp_high,
                    "color": "gray", "alpha": 1.0,
                },
                zorder=0,
            ),
            Layer(
                geom=GeomAbline(slope=0, intercept=nnp_crit),
                stat=StatIdentity(),
                mapping={"color": "black", "style": "dashed"},
                zorder=1,
            ),
            Layer(
                geom=GeomAbline(x1=npr_crit, y1=0, x2=npr_crit, y2=1),
                stat=StatIdentity(),
                mapping={"color": "black", "style": "dashed"},
                zorder=1,
            ),
            Layer(
                geom=GeomText(),
                stat=StatIdentity(),
                mapping={
                    "x": npr_high * 0.4, "y": nnp_high * 0.92,
                    "label": f"Non-Acid Generating\nMaterial\n(NNP>{nnp_crit} and NPR>{npr_crit})",
                    "size": 6,
                },
                zorder=2,
            ),
            Layer(
                geom=GeomText(),
                stat=StatIdentity(),
                mapping={
                    "x": (npr_low * npr_high) ** 0.5, "y": nnp_high * 3,
                    "label": "Uncertain\nAcid Generating\nCharacteristics",
                    "size": 6,
                },
                zorder=2,
            ),
            Layer(
                geom=GeomText(),
                stat=StatIdentity(),
                mapping={
                    "x": npr_low * 0.33, "y": nnp_low * 0.5,
                    "label": f"Potentially Acid Generating (PAG)\nMaterial\n(NNP<{nnp_low} and NPR<{npr_low})",
                    "size": 6,
                },
                zorder=2,
            ),
            Layer(
                geom=GeomPoint(),
                stat=StatIdentity(),
                mapping=effective_mapping,
                scales=kwargs.get("scales"),
                zorder=10,
            ),
        ],
        default_settings={**NPR_NNP_DEFAULTS, **options},
        mapping_consumed=True,
    )


def npr_nnp(
    mapping: dict[str, SourceType] | None = None,
    npr_crit: float = 3,
    nnp_crit: float = 20,
    scales: dict[str, Scale] | None = None,
) -> FigureTemplate:
    recipe = npr_nnp_builder(
        mapping=mapping,
        npr_crit=npr_crit,
        nnp_crit=nnp_crit,
        scales=scales,
        _legacy_factory=True,
    )
    return FigureTemplate(
        name=recipe.name,
        layers=recipe.layers,
        coord=recipe.coord,
        default_settings=recipe.default_settings,
    )
