"""
Piper diagram template — declarative linked-axes spec (Phase 14.5 WP5).

Replaces the legacy renderer-hardcoded GridSpec + template-side math with a
pure declarative FigureSpec: one main Axes (diamond, CoordCartesian) plus two
AxisLinks (cation/anion triangles, TernaryCoord + LinkTransform).

Inputs must arrive as meq/L — no unit conversion in FigEngine.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from geofig_engine.core.coord import CoordCartesian, TernaryCoord
from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.link import AxisLink, LinkTransform
from geofig_engine.core.spec import FigureSpec, build_spec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.utils.typing import SourceType

_SQRT3_2 = math.sqrt(3) / 2.0


def build_piper_specs(
    data: pd.DataFrame,
    left_tri: tuple[str, str, str] = ("Ca", "Mg", "Na+K"),
    right_tri: tuple[str, str, str] = ("HCO3", "SO4", "Cl"),
    mapping: dict[str, SourceType] | None = None,
    title: str = "Piper Diagram",
) -> list[FigureSpec]:
    """Build a Piper FigureSpec using linked axes.

    Returns a single-element list containing a FigureSpec with:
    - A main CoordCartesian axis (diamond, world space)
    - Left cation AxisLink (TernaryCoord left-handed, LinkTransform scale 0.5)
    - Right anion AxisLink (TernaryCoord right-handed, LinkTransform scale -0.5)
    """
    # -- validate ion columns exist --
    all_ions = set(left_tri + right_tri)
    missing = [c for c in all_ions if c not in data.columns]
    if missing:
        raise ValueError(
            f"Piper data must contain ion columns {missing}; "
            f"available: {sorted(data.columns)}"
        )

    # -- diamond percentage data --
    cat_total = data[list(left_tri)].sum(axis=1)
    an_total = data[list(right_tri)].sum(axis=1)
    # Cation %: (Ca+Mg) / (Ca+Mg+Na+K) * 100
    dia_cation_pct = (data[left_tri[0]] + data[left_tri[1]]) / cat_total.replace(0.0, np.nan) * 100
    dia_cation_pct = dia_cation_pct.fillna(0.0)
    # Anion %: (SO4+Cl) / (HCO3+SO4+Cl) * 100
    dia_anion_pct = (data[right_tri[1]] + data[right_tri[2]]) / an_total.replace(0.0, np.nan) * 100
    dia_anion_pct = dia_anion_pct.fillna(0.0)

    # -- visual mapping for color/marker/etc. passthrough --
    visuals: dict[str, pd.Series] = {}
    if mapping:
        for channel, source in mapping.items():
            if isinstance(source, str) and source in data.columns:
                visuals[channel] = data[source]
            elif isinstance(source, pd.Series):
                visuals[channel] = source

    # -- data augmentation: inject diamond coords --
    aug = data.copy()
    aug["_dia_anion_pct"] = dia_anion_pct
    aug["_dia_cation_pct"] = dia_cation_pct

    # -- links --
    # TernaryCoord channels = (apex, bottom-left, bottom-right)
    # left_tri=("Ca","Mg","Na+K"):  apex=Mg, bottom-left=Ca, bottom-right=Na+K
    # right_tri=("HCO3","SO4","Cl"): apex=SO4, bottom-left=Cl, bottom-right=HCO3
    left_channels = (left_tri[1], left_tri[0], left_tri[2])
    right_channels = (right_tri[1], right_tri[2], right_tri[0])

    left_link = AxisLink(
        name="left_tri",
        coord=TernaryCoord(channels=left_channels, handedness="left"),
        transform=LinkTransform(scale=(0.5, 0.5)),
        frame={
            "provider": "piper_ternary_frame",
            "ions": [left_tri[1], left_tri[0], left_tri[2]],
            "rev_bottom": True,
            "rev_right": True,
            "title": "LEFT TRIANGLE",
        },
    )
    right_link = AxisLink(
        name="right_tri",
        coord=TernaryCoord(channels=right_channels, handedness="right"),
        transform=LinkTransform(scale=(-0.5, 0.5), translate=(1.0, 0.0)),
        frame={
            "provider": "piper_ternary_frame",
            "ions": [right_tri[1], right_tri[2], right_tri[0]],
            "rev_left": True,
            "title": "RIGHT TRIANGLE",
        },
    )
    dia_pct = _SQRT3_2 / 100.0
    _SQRT2 = math.sqrt(2)
    diamond_link = AxisLink(
        name="diamond",
        coord=CoordCartesian(),
        transform=LinkTransform(
            translate=(0.5, 0.0),
            rotate=45.0,
            scale=(_SQRT2 / 400.0, dia_pct * _SQRT2 / 2.0),
        ),
        frame={"provider": "piper_diamond_frame"},
    )

    # -- layers --
    layers: list[LayerSpec] = []

    def _ternary_layer(channels, link_name, z=10):
        vm: dict = {ch: aug[ch] for ch in channels}
        vm.update(visuals)
        layers.append(LayerSpec(
            geom=GeomPoint(),
            stat=StatIdentity(),
            visual_mapping=vm,
            subplot=link_name,
            zorder=z,
        ))

    _ternary_layer(left_tri, "left_tri")
    _ternary_layer(right_tri, "right_tri")

    # diamond layer: percentage data in [0,100]²
    dia_vm: dict = {"x": aug["_dia_anion_pct"],
                    "y": aug["_dia_cation_pct"]}
    dia_vm.update(visuals)
    layers.append(LayerSpec(
        geom=GeomPoint(),
        stat=StatIdentity(),
        visual_mapping=dia_vm,
        subplot="diamond",
        zorder=10,
    ))

    spec = build_spec(
        data=aug,
        mappings={},
        settings={"figsize": (10, 8), "title": title},
        context={},
        template_name="piper",
        layers=layers,
        links=(left_link, right_link, diamond_link),
    )
    return [spec]


def piper_overlay_diamond(
    spec: FigureSpec,
    data: pd.DataFrame,
    mapping: dict[str, SourceType] | None = None,
) -> FigureSpec:
    """Append an extra diamond layer to an existing Piper spec.

    The overlay is a plain layer routing — no special renderer knowledge needed.
    """
    left_tri = tuple(
        link.coord.params["channels"]
        for link in spec.links if link.name == "left_tri"
    )[0]
    right_tri = tuple(
        link.coord.params["channels"]
        for link in spec.links if link.name == "right_tri"
    )[0]

    cat_total = data[list(left_tri)].sum(axis=1)
    an_total = data[list(right_tri)].sum(axis=1)
    dia_cation_pct = (data[left_tri[0]] + data[left_tri[1]]) / cat_total.replace(0.0, np.nan) * 100
    dia_cation_pct = dia_cation_pct.fillna(0.0)
    dia_anion_pct = (data[right_tri[1]] + data[right_tri[2]]) / an_total.replace(0.0, np.nan) * 100
    dia_anion_pct = dia_anion_pct.fillna(0.0)

    visuals: dict[str, pd.Series] = {}
    if mapping:
        for channel, source in mapping.items():
            if isinstance(source, str) and source in data.columns:
                visuals[channel] = data[source]
            elif isinstance(source, pd.Series):
                visuals[channel] = source

    vm: dict = {"x": dia_anion_pct, "y": dia_cation_pct}
    vm.update(visuals)

    overlay_layer = LayerSpec(
        geom=GeomPoint(),
        stat=StatIdentity(),
        visual_mapping=vm,
        subplot="diamond",
        zorder=10,
    )

    return build_spec(
        data=spec.data,
        mappings=spec.mappings,
        settings=spec.settings,
        context=spec.context,
        template_name=spec.template_name,
        layers=list(spec.layers) + [overlay_layer],
        links=spec.links,
    )
