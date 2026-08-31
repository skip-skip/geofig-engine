from typing import Any

from geofig_engine.core.geom import GeomBar
from geofig_engine.core.layer import Layer
from geofig_engine.core.scale import Scale
from geofig_engine.core.stat import StatBin
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import SourceType


HISTOGRAM_DEFAULTS: dict[str, Any] = {
    "figsize": (10, 6),
    "axis": {
        "xscale": "linear",
        "yscale": "linear",
        "grid": True,
    },
}


def histogram(
    mapping: dict[str, SourceType] | None = None,
    scales: dict[str, Scale] | None = None,
    bins: int | str = 10,
    density: bool = False,
    cumulative: bool = False,
) -> FigureTemplate:
    mapping = mapping or {}
    x_col = mapping.get("x")
    if x_col is None:
        raise ValueError("histogram template requires 'x' in mapping")

    stat_mapping: dict[str, SourceType] = {
        "x": "x",
        "y": "y",
        "width": "width",
    }
    if "color" in mapping:
        stat_mapping["color"] = mapping["color"]
    if "alpha" in mapping:
        stat_mapping["alpha"] = mapping["alpha"]

    return FigureTemplate(
        name="histogram",
        layers=[
            Layer(
                geom=GeomBar(),
                stat=StatBin(
                    column=str(x_col),
                    bins=bins,
                    density=density,
                    cumulative=cumulative,
                ),
                mapping=stat_mapping,
                scales=scales,
            ),
        ],
        default_settings=dict(HISTOGRAM_DEFAULTS),
    )
