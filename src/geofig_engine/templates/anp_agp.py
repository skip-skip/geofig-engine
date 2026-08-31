from typing import Any

from geofig_engine.core.geom import GeomAbline, GeomPoint, GeomText
from geofig_engine.core.layer import Layer
from geofig_engine.core.scale import Scale
from geofig_engine.core.stat import StatIdentity
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import SourceType


ANP_AGP_DEFAULTS: dict[str, Any] = {
    "figsize": (8, 8),
    "title": "ANP vs AGP — Classification",
    "axis": {
        "grid": True,
        "xlabel": "AGP (Acid Generation Potential)",
        "ylabel": "ANP (Acid Neutralisation Potential)",
    },
}


def anp_agp(
    mapping: dict[str, SourceType] | None = None,
    scales: dict[str, Scale] | None = None,
) -> FigureTemplate:
    mapping = mapping or {}
    slopes = [1, 2, 3, 4]
    labels = ["NP:AP = 1:1", "NP:AP = 2:1", "NP:AP = 3:1", "NP:AP = 4:1"]

    layers: list[Layer] = []
    for i, (s, lbl) in enumerate(zip(slopes, labels)):
        layers.append(
            Layer(
                geom=GeomAbline(slope=s, intercept=0),
                stat=StatIdentity(),
                mapping={"color": "gray", "style": "dashed", "width": 0.8},
                zorder=1,
            )
        )
        layers.append(
            Layer(
                geom=GeomText(),
                stat=StatIdentity(),
                mapping={
                    "x": 1, "y": s + 0.5,
                    "label": lbl, "size": 9, "color": "gray",
                },
                zorder=2,
            )
        )

    layers.extend([
        Layer(
            geom=GeomText(),
            stat=StatIdentity(),
            mapping={
                "x": 0.2, "y": 500,
                "label": "Non-Acid Generating\nMaterial",
                "size": 7,
            },
            zorder=2,
        ),
        Layer(
            geom=GeomText(),
            stat=StatIdentity(),
            mapping={
                "x": 1.5, "y": 1.4,
                "label": "Uncertain Acid Generating\nCharacteristics",
                "size": 7, "rotation": 37.2,
            },
            zorder=2,
        ),
        Layer(
            geom=GeomText(),
            stat=StatIdentity(),
            mapping={
                "x": 500, "y": 0.5,
                "label": "Potentially Acid Generating (PAG)\nMaterial",
                "size": 7,
            },
            zorder=2,
        ),
        Layer(
            geom=GeomPoint(),
            stat=StatIdentity(),
            mapping=mapping,
            scales=scales,
            zorder=10,
        ),
    ])

    return FigureTemplate(
        name="anp_agp",
        layers=layers,
        default_settings=dict(ANP_AGP_DEFAULTS),
    )
