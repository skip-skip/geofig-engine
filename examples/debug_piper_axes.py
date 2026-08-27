"""Debug script: draw piper axes (frames only, no data points)."""

from pathlib import Path
import numpy as np
import pandas as pd

from geofig_engine.core.coord import CoordCartesian, TernaryCoord
from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.link import LinkTransform
from geofig_engine.core.spec import FigureSpec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.renderers import MatplotlibRenderer


def build_empty_piper() -> FigureSpec:
    """Build a FigureSpec with 3 children but empty data (frames only)."""
    empty_df = pd.DataFrame({
        "Ca": [], "Mg": [], "Na+K": [],
        "HCO3": [], "SO4": [], "Cl": [],
    })

    left_channels = ("Mg", "Ca", "Na+K")
    right_channels = ("SO4", "Cl", "HCO3")

    def _empty_vm(channels):
        return {ch: pd.Series([], dtype=float) for ch in channels}

    left_child = FigureSpec(
        data=empty_df, mappings={}, settings={}, context={},
        template_name="piper",
        coord=TernaryCoord(channels=left_channels, handedness="left"),
        transform=LinkTransform().scale(0.5, 0.5),
        frame_config={
            "title": "LEFT TRIANGLE",
            "rev_bottom": True,
            "rev_right": True,
        },
        layers=[LayerSpec(
            geom=GeomPoint(), stat=StatIdentity(),
            visual_mapping=_empty_vm(left_channels), zorder=10,
        )],
    )

    right_child = FigureSpec(
        data=empty_df, mappings={}, settings={}, context={},
        template_name="piper",
        coord=TernaryCoord(channels=right_channels, handedness="right"),
        transform=LinkTransform().scale(-0.5, 0.5).translate(1.0, 0.0),
        frame_config={
            "title": "RIGHT TRIANGLE",
            "rev_left": True,
        },
        layers=[LayerSpec(
            geom=GeomPoint(), stat=StatIdentity(),
            visual_mapping=_empty_vm(right_channels), zorder=10,
        )],
    )

    dia_pct = np.sqrt(3) / 200.0
    dia_scale = (np.sqrt(2) / 400.0, dia_pct * np.sqrt(2) / 2.0)
    diamond_child = FigureSpec(
        data=empty_df, mappings={}, settings={}, context={},
        template_name="piper",
        coord=CoordCartesian(),
        transform=LinkTransform()
        .rotate(45.0)
        .scale(*dia_scale)
        .translate(0.5, 0.0),
        frame_config={
            "title": "DIAMOND",
            "xlim": (0, 100),
            "ylim": (0, 100),
            "grid_step": 20,
            "tick_step": 20,
        },
        layers=[LayerSpec(
            geom=GeomPoint(), stat=StatIdentity(),
            visual_mapping={"x": pd.Series([], dtype=float),
                            "y": pd.Series([], dtype=float)},
            zorder=10,
        )],
    )

    return FigureSpec(
        data=empty_df, mappings={},
        settings={"figsize": (10, 8), "title": "Piper Axes Debug (no data)"},
        context={}, template_name="piper",
        children=(left_child, right_child, diamond_child),
    )


def main():
    out = Path(__file__).resolve().parent / "outputs"
    out.mkdir(parents=True, exist_ok=True)

    spec = build_empty_piper()
    renderer = MatplotlibRenderer()
    fig = renderer.render(spec)

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
