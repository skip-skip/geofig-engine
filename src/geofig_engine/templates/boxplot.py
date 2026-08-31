"""
Boxplot figure templates for FigEngine.

Provides pre-built templates that compose GeomBox with other geoms
(e.g., GeomPoint for jittered points).
"""

from typing import Any

from geofig_engine.core.geom import GeomBox, GeomPoint
from geofig_engine.core.layer import Layer
from geofig_engine.core.scale import Scale
from geofig_engine.core.stat import StatIdentity
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import SourceType


BOXPLOT_DEFAULTS: dict[str, Any] = {
    "figsize": (10, 6),
    "xscale": "linear",
    "yscale": "linear",
    "grid": True,
}


def boxplot_with_points(
    mapping: dict[str, SourceType] | None = None,
    scales: dict[str, Scale] | None = None,
    box_width: float = 0.8,
    jitter_width: float = 0.08,
    point_size: int = 8,
    point_alpha: float = 0.4,
    sort_mode: str = "none",
    smush: bool = False,
    showfliers: bool = True,
    showmeans: bool = False,
    show_n: bool = False,
    min_box_n: int = 1,
) -> FigureTemplate:
    """Template composing a dodged boxplot with jittered points.

    Both layers share the same ``x``, ``y``, and ``color`` mapping.
    The box layer draws dodged boxplots; the point layer draws
    jittered scatter points at the same dodged positions.
    """
    box_layer = Layer(
        geom=GeomBox(
            box_width=box_width,
            sort_mode=sort_mode,
            smush=smush,
            showfliers=showfliers,
            showmeans=showmeans,
            show_n=show_n,
            min_box_n=min_box_n,
        ),
        stat=StatIdentity(),
        mapping=mapping or {},
        scales=scales,
    )
    point_layer = Layer(
        geom=GeomPoint(
            jitter=jitter_width,
            dodge=box_width,
        ),
        stat=StatIdentity(),
        mapping=mapping or {},
        scales=scales,
    )
    return FigureTemplate(
        name="boxplot_with_points",
        layers=[box_layer, point_layer],
        default_settings=dict(BOXPLOT_DEFAULTS),
    )
