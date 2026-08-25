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


def _compute_diamond_xy(
    cat_x: np.ndarray, cat_y: np.ndarray,
    an_x: np.ndarray, an_y: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Derive diamond-space (x, y) from ternary-projected cation/anion coords."""
    h = _SQRT3_2
    dx = an_y / (4 * h) + 0.5 * an_x - cat_y / (4 * h) + 0.5 * cat_x - 0.5
    dy = 0.5 * an_y + h * an_x + 0.5 * cat_y - h * cat_x
    return np.nan_to_num(dx), np.nan_to_num(dy)


def _ternary_xy(frac_a: pd.Series, frac_b: pd.Series,
                frac_c: pd.Series, handedness: str = "left"):
    """Project three fraction series into local ternary (x, y)."""
    a = frac_a.to_numpy(dtype=float)
    b = frac_b.to_numpy(dtype=float)
    c = frac_c.to_numpy(dtype=float)
    x = 0.5 * a + c
    y = _SQRT3_2 * a
    if handedness == "right":
        x = 1.0 - x
    return x, y


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

    # -- ternary fractions (cations: f0=Ca, f1=Mg, f2=Na+K) --
    def _fracs(cols):
        total = data[list(cols)].sum(axis=1)
        return [data[c] / total.replace(0.0, np.nan) for c in cols]

    cat_fracs = _fracs(left_tri)   # [Ca_f, Mg_f, Nak_f]
    an_fracs = _fracs(right_tri)   # [HCO3_f, SO4_f, Cl_f]

    # local ternary projections
    cat_x, cat_y = _ternary_xy(cat_fracs[1], cat_fracs[0], cat_fracs[2])
    an_x, an_y = _ternary_xy(an_fracs[1], an_fracs[2], an_fracs[0],
                              handedness="right")

    # diamond world coordinates
    dia_x, dia_y = _compute_diamond_xy(cat_x, cat_y, an_x, an_y)

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
    aug["_dia_x"] = dia_x
    aug["_dia_y"] = dia_y

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
    diamond_link = AxisLink(
        name="diamond",
        coord=CoordCartesian(),
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

    # diamond layer: pre-computed world coords
    dia_vm: dict = {"x": pd.Series(dia_x, index=aug.index),
                    "y": pd.Series(dia_y, index=aug.index)}
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

    def _fracs(cols):
        total = data[list(cols)].sum(axis=1)
        return [data[c] / total.replace(0.0, np.nan) for c in cols]

    cat_fracs = _fracs(left_tri)
    an_fracs = _fracs(right_tri)
    cat_x, cat_y = _ternary_xy(cat_fracs[1], cat_fracs[0], cat_fracs[2])
    an_x, an_y = _ternary_xy(an_fracs[1], an_fracs[2], an_fracs[0],
                              handedness="right")
    dia_x, dia_y = _compute_diamond_xy(cat_x, cat_y, an_x, an_y)

    visuals: dict[str, pd.Series] = {}
    if mapping:
        for channel, source in mapping.items():
            if isinstance(source, str) and source in data.columns:
                visuals[channel] = data[source]
            elif isinstance(source, pd.Series):
                visuals[channel] = source

    vm: dict = {"x": pd.Series(dia_x, index=data.index),
                "y": pd.Series(dia_y, index=data.index)}
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
