from typing import Any

from geofig_engine.core.geom import GeomAbline, GeomPoint, GeomText
from geofig_engine.core.layer import Layer
from geofig_engine.core.scale import Scale
from geofig_engine.core.stat import StatIdentity
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import SourceType


NAGPH_NAG_DEFAULTS: dict[str, Any] = {
    "figsize": (8, 6),
    "axis": {
        "title": "NAG pH vs NAG — Classification",
        "grid": True,
        "xlabel": "NAG pH",
        "ylabel": "NAG (kg H\u2082SO\u2084/t)",
    },
}


def nagph_nag(
    mapping: dict[str, SourceType] | None = None,
    scales: dict[str, Scale] | None = None,
) -> FigureTemplate:
    mapping = mapping or {}
    vline_x = 4.5
    hline_y = 18.14

    return FigureTemplate(
        name="nagph_nag",
        layers=[
            Layer(
                geom=GeomAbline(x1=vline_x, y1=0, x2=vline_x, y2=1),
                stat=StatIdentity(),
                mapping={"color": "gray", "style": "dashed", "width": 1.0},
                zorder=1,
            ),
            Layer(
                geom=GeomAbline(slope=0, intercept=hline_y),
                stat=StatIdentity(),
                mapping={"color": "gray", "style": "dashed", "width": 1.0},
                zorder=1,
            ),
            Layer(
                geom=GeomText(),
                stat=StatIdentity(),
                mapping={
                    "x": vline_x / 2, "y": hline_y / 2,
                    "label": "Uncertain\nAcid Generating\nCharacteristics",
                    "size": 6,
                },
                zorder=2,
            ),
            Layer(
                geom=GeomText(),
                stat=StatIdentity(),
                mapping={
                    "x": (vline_x + 14) / 2, "y": hline_y / 2,
                    "label": "Non-Acid Generating\nMaterial",
                    "size": 6,
                },
                zorder=2,
            ),
            Layer(
                geom=GeomText(),
                stat=StatIdentity(),
                mapping={
                    "x": (vline_x + 14) / 2, "y": (hline_y + 30) / 2,
                    "label": "Uncertain\nAcid Generating\nCharacteristics",
                    "size": 6,
                },
                zorder=2,
            ),
            Layer(
                geom=GeomText(),
                stat=StatIdentity(),
                mapping={
                    "x": vline_x / 2, "y": (hline_y + 30) / 2,
                    "label": "Potentially\nAcid Generating\nMaterial",
                    "size": 6,
                },
                zorder=2,
            ),
            Layer(
                geom=GeomText(),
                stat=StatIdentity(),
                mapping={
                    "x": vline_x - 0.3, "y": hline_y / 2,
                    "label": "NAG pH = 4.5", "size": 6, "color": "gray",
                    "rotation": 90,
                },
                zorder=3,
            ),
            Layer(
                geom=GeomText(),
                stat=StatIdentity(),
                mapping={
                    "x": (vline_x + 14) / 2, "y": hline_y - 1.5,
                    "label": "18.14 kg H\u2082SO\u2084/t", "size": 6, "color": "gray",
                },
                zorder=3,
            ),
            Layer(
                geom=GeomPoint(),
                stat=StatIdentity(),
                mapping=mapping,
                scales=scales,
                zorder=10,
            ),
        ],
        default_settings=dict(NAGPH_NAG_DEFAULTS),
    )
