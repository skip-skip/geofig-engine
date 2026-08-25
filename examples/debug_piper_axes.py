"""Debug script: draw piper axes (frames only, no data points)."""

from pathlib import Path
import numpy as np
import pandas as pd

from geofig_engine.core.coord import CoordCartesian, TernaryCoord
from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.link import AxisLink, LinkTransform
from geofig_engine.core.spec import FigureSpec, build_spec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.renderers import MatplotlibRenderer
import math

_SQRT3_2 = math.sqrt(3) / 2.0


def build_empty_piper() -> FigureSpec:
    """Build a FigureSpec with piper links but empty data (frames only)."""
    # Empty DataFrame — just needs the right columns so coord transforms work
    df = pd.DataFrame({
        "Ca": [], "Mg": [], "Na+K": [],
        "HCO3": [], "SO4": [], "Cl": [],
    })

    left_channels = ("Mg", "Ca", "Na+K")
    right_channels = ("SO4", "Cl", "HCO3")

    left_link = AxisLink(
        name="left_tri",
        coord=TernaryCoord(channels=left_channels, handedness="left"),
        transform=LinkTransform(scale=(0.5, 0.5)),
        frame={
            "provider": "piper_ternary_frame",
            "ions": ["Mg", "Ca", "Na+K"],
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
            "ions": ["SO4", "Cl", "HCO3"],
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

    # Empty layers — one per link so the renderer knows about them
    layers = []
    for channels, link_name in [
        (["Ca", "Mg", "Na+K"], "left_tri"),
        (["HCO3", "SO4", "Cl"], "right_tri"),
        (["x", "y"], "diamond"),
    ]:
        vm: dict = {ch: pd.Series([], dtype=float) for ch in channels}
        if link_name == "diamond":
            vm["x"] = pd.Series([], dtype=float)
            vm["y"] = pd.Series([], dtype=float)
        layers.append(LayerSpec(
            geom=GeomPoint(),
            stat=StatIdentity(),
            visual_mapping=vm,
            subplot=link_name,
            zorder=10,
        ))

    return build_spec(
        data=df,
        mappings={},
        settings={"figsize": (10, 8), "title": "Piper Axes Debug (no data)"},
        context={},
        template_name="piper",
        layers=layers,
        links=(left_link, right_link, diamond_link),
    )


def main():
    out = Path(__file__).resolve().parent / "outputs"
    out.mkdir(parents=True, exist_ok=True)

    spec = build_empty_piper()
    renderer = MatplotlibRenderer()
    fig = renderer.render(spec)

    # Print axes info
    ax = fig.axes[0]
    print("xlim:", ax.get_xlim())
    print("ylim:", ax.get_ylim())
    print("lines:", len(ax.lines))
    print("texts:", len(ax.texts))

    path = out / "piper_axes_debug.png"
    fig.savefig(path, dpi=150)
    fig.clf()
    print(f"Saved to {path}")


if __name__ == "__main__":
    main()
