"""
Piper diagram template — declarative linked-axes spec (Phase 14.5 WP5).

Replaces the legacy renderer-hardcoded GridSpec + template-side math with a
pure declarative FigureSpec: one main CoordCartesian axis (diamond, world
space) plus two child FigureSpecs (cation/anion triangles, TernaryCoord +
LinkTransform).

Inputs must arrive as meq/L — no unit conversion in FigEngine.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from geofig_engine.core.coord import CoordCartesian, TernaryCoord
from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.link import LinkTransform
from geofig_engine.core.spec import FigureSpec, build_spec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.utils.typing import SourceType

_SQRT3_2 = math.sqrt(3) / 2.0
_SQRT2 = math.sqrt(2)

# Charge-bearing display labels (matplotlib mathtext sub/superscripts).
# Keyed by channel (data column) name; the ternary vertex label order follows
# the channel order, and the diamond axis titles are derived from these below.
_PIPER_ION_LABELS: dict[str, str] = {
    "Ca": r"$Ca^{++}$",
    "Mg": r"$Mg^{++}$",
    "Na+K": r"$(Na+K)^{+}$",
    "HCO3": r"$HCO_3^{-} + CO_3^{--}$",
    "SO4": r"$SO_4^{--}$",
    "Cl": r"$Cl^{-}$",
}


def _resolve_ion_label(channel: str, overrides: dict[str, str] | None) -> str:
    """Display label for a channel: explicit override, then known-ion, then name."""
    if overrides and channel in overrides:
        return overrides[channel]
    return _PIPER_ION_LABELS.get(channel, channel)


def build_piper_specs(
    data: pd.DataFrame,
    left_tri: tuple[str, str, str] = ("Ca", "Mg", "Na+K"),
    right_tri: tuple[str, str, str] = ("HCO3", "SO4", "Cl"),
    mapping: dict[str, SourceType] | None = None,
    title: str = "Piper Diagram",
    labels: dict[str, str] | None = None,
) -> list[FigureSpec]:
    """Build a Piper FigureSpec using linked axes.

    Returns a single-element list containing a FigureSpec with 3 children:
    - Left cation triangle (TernaryCoord left-handed, LinkTransform scale 0.5)
    - Right anion triangle (TernaryCoord right-handed, LinkTransform scale -0.5)
    - Diamond (CoordCartesian, LinkTransform rotate 45° + scale + translate)

    ``labels`` optionally maps a channel (data column) name to a display label
    (e.g. ``{"Ca": "$Ca^{2+}$"}``); defaults provide charge-bearing mathtext
    labels for the standard ion columns.
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
    dia_cation_pct = (data[left_tri[0]] + data[left_tri[1]]) / cat_total.replace(0.0, np.nan) * 100
    dia_cation_pct = dia_cation_pct.fillna(0.0)
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

    # -- build mappings (column references for ternary, passthrough for diamond) --
    left_channels = (left_tri[1], left_tri[0], left_tri[2])
    right_channels = (right_tri[1], right_tri[2], right_tri[0])

    left_mmap: dict[str, SourceType] = {ch: [ch] for ch in left_channels}
    left_mmap.update(visuals)

    right_mmap: dict[str, SourceType] = {ch: [ch] for ch in right_channels}
    right_mmap.update(visuals)

    dia_mmap: dict[str, SourceType] = {
        "x": ["_dia_anion_pct"],
        "y": ["_dia_cation_pct"],
    }
    dia_mmap.update(visuals)

    # -- child FigureSpecs --
    left = FigureSpec(
        data=aug,
        mappings=left_mmap,
        settings={"axis_arrows": True},
        context={},
        template_name="piper",
        coord=TernaryCoord(
            channels=left_channels,
            handedness="left",
            labels=tuple(_resolve_ion_label(ch, labels) for ch in left_channels),
        ),
        transform=LinkTransform().scale(0.5, 0.5),
        layers=[LayerSpec(
            geom=GeomPoint(),
            stat=StatIdentity(),
            visual_mapping={**visuals, **{ch: aug[ch] for ch in left_channels}},
            zorder=10,
        )],
    )
    right = FigureSpec(
        data=aug,
        mappings=right_mmap,
        settings={"axis_arrows": True},
        context={},
        template_name="piper",
        coord=TernaryCoord(
            channels=right_channels,
            handedness="right",
            labels=tuple(_resolve_ion_label(ch, labels) for ch in right_channels),
        ),
        transform=LinkTransform().scale(-0.5, 0.5).translate(1.2, 0.0),
        layers=[LayerSpec(
            geom=GeomPoint(),
            stat=StatIdentity(),
            visual_mapping={**visuals, **{ch: aug[ch] for ch in right_channels}},
            zorder=10,
        )],
    )

    dia_pct = _SQRT3_2 / 100.0
    diamond = FigureSpec(
        data=aug,
        mappings=dia_mmap,
        settings={
            "axis_arrows": True,
            "xlim": (0, 100),
            "ylim": (0, 100),
            "x_reversed": True,
            "y_reversed": True,
            "grid_step": 20,
            "tick_step": 20,
            "secondary_x": {
                "range": [0, 100],
                "label": f"{_resolve_ion_label(right_tri[1], labels)} + {_resolve_ion_label(right_tri[2], labels)}",
            },
            "secondary_y": {
                "range": [0, 100],
                "label": f"{_resolve_ion_label(left_tri[0], labels)} + {_resolve_ion_label(left_tri[1], labels)}",
            },
        },
        context={},
        template_name="piper",
        coord=CoordCartesian(),
        transform=LinkTransform()
        .rotate(45.0)
        .scale(_SQRT2 / 400.0, dia_pct * _SQRT2 / 2.0)
        .translate(0.6, 0.1),
        layers=[LayerSpec(
            geom=GeomPoint(),
            stat=StatIdentity(),
            visual_mapping={**visuals, "x": aug["_dia_anion_pct"], "y": aug["_dia_cation_pct"]},
            zorder=10,
        )],
    )

    # -- parent FigureSpec --
    parent = FigureSpec(
        data=aug,
        mappings={},
        settings={"figsize": (10, 8), "title": title},
        context={},
        template_name="piper",
        children=(left, right, diamond),
    )
    return [parent]
