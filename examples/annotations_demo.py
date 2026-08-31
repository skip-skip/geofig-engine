"""Demonstration of Phase 13 annotation / reference additions.

Shows GeomHSpan, GeomVSpan, GeomRect, GeomAbline, GeomText with
angle/bbox, and per-layer zorder control.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from geofig_engine.core.coord import CoordPolar
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.geom import (
    GeomAbline,
    GeomHSpan,
    GeomLine,
    GeomPoint,
    GeomRect,
    GeomText,
    GeomVSpan,
)
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatIdentity
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer


def make_dataset() -> Dataset:
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "x": np.linspace(0, 10, 20),
        "y": np.linspace(0, 10, 20) + rng.normal(0, 0.5, 20),
        "group": ["A", "B"] * 10,
    })
    return Dataset(dataframe=df, key_column="x")


def main() -> None:
    out = Path(__file__).resolve().parent / "outputs" / "annotations_demo"
    out.mkdir(parents=True, exist_ok=True)

    engine = FigureEngine()
    renderer = MatplotlibRenderer()
    ds = make_dataset()

    # ---- 1. Classification-style plot: scatter + quadrants + reference line ----
    layers = [
        Layer(
            geom=GeomPoint(),
            stat=StatIdentity(),
            mapping={"x": "x", "y": "y", "color": "group"},
            zorder=10,
        ),
        Layer(
            geom=GeomVSpan(),
            stat=StatIdentity(),
            mapping={"xmin": 0, "xmax": 5, "color": "lightblue", "alpha": 0.15},
            zorder=1,
        ),
        Layer(
            geom=GeomHSpan(),
            stat=StatIdentity(),
            mapping={"ymin": 5, "ymax": 10, "color": "lightgreen", "alpha": 0.15},
            zorder=2,
        ),
        Layer(
            geom=GeomRect(),
            stat=StatIdentity(),
            mapping={"xmin": 5, "xmax": 10, "ymin": 0, "ymax": 5,
                      "color": "salmon", "alpha": 0.15},
            zorder=3,
        ),
        Layer(
            geom=GeomAbline(slope=1.0, intercept=0.0),
            stat=StatIdentity(),
            mapping={"color": "black", "style": "--", "width": 1.5},
            zorder=5,
        ),
    ]
    specs = engine.build_specs_from_layers(
        ds, layers,
        settings={
            "title": "1 – Quadrants + 1:1 line (zorder demo)",
            "xlabel": "X", "ylabel": "Y",
            "figsize": (8, 6),
        },
    )
    fig = renderer.render(specs[0])
    fig.savefig(out / "01_quadrants_abline.png", dpi=150)
    print("✓ 01_quadrants_abline.png")

    # ---- 2. Threshold bands with annotated labels ----
    layers = [
        Layer(
            geom=GeomPoint(),
            stat=StatIdentity(),
            mapping={"x": "x", "y": "y"},
            zorder=10,
        ),
        Layer(
            geom=GeomHSpan(),
            stat=StatIdentity(),
            mapping={"ymin": 8, "ymax": 12, "color": "red", "alpha": 0.1},
            zorder=1,
        ),
        Layer(
            geom=GeomAbline(slope=0.0, intercept=8.0),
            stat=StatIdentity(),
            mapping={"color": "red", "style": ":", "width": 1},
            zorder=2,
        ),
        Layer(
            geom=GeomAbline(slope=0.0, intercept=12.0),
            stat=StatIdentity(),
            mapping={"color": "red", "style": ":", "width": 1},
            zorder=2,
        ),
        Layer(
            geom=GeomText(),
            stat=StatIdentity(),
            mapping={"x": 1, "y": 12.5, "label": "Threshold",
                     "color": "red", "size": 10, "angle": 0},
            zorder=20,
        ),
    ]
    specs = engine.build_specs_from_layers(
        ds, layers,
        settings={
            "title": "2 – Threshold bands with annotation",
            "xlabel": "X", "ylabel": "Y",
            "figsize": (8, 6),
        },
    )
    fig = renderer.render(specs[0])
    fig.savefig(out / "02_threshold_bands.png", dpi=150)
    print("✓ 02_threshold_bands.png")

    # ---- 3. Rotated text + bbox labels on scatter ----
    layers = [
        Layer(
            geom=GeomPoint(),
            stat=StatIdentity(),
            mapping={"x": "x", "y": "y"},
            zorder=10,
        ),
        Layer(
            geom=GeomText(),
            stat=StatIdentity(),
            mapping={
                "x": "x", "y": "y", "label": "y",
                "angle": 45, "size": 8,
                "bbox": {"facecolor": "yellow", "alpha": 0.3, "pad": 2},
            },
            zorder=20,
        ),
    ]
    specs = engine.build_specs_from_layers(
        ds, layers,
        settings={
            "title": "3 – Rotated text with bounding boxes",
            "xlabel": "X", "ylabel": "Y",
            "figsize": (8, 6),
        },
    )
    fig = renderer.render(specs[0])
    fig.savefig(out / "03_rotated_bbox_text.png", dpi=150)
    print("✓ 03_rotated_bbox_text.png")

    # ---- 4. Two-point abline with custom styling ----
    layers = [
        Layer(
            geom=GeomPoint(),
            stat=StatIdentity(),
            mapping={"x": "x", "y": "y"},
            zorder=10,
        ),
        Layer(
            geom=GeomAbline(x1=0, y1=2, x2=10, y2=8),
            stat=StatIdentity(),
            mapping={"color": "purple", "style": "-.", "width": 2, "alpha": 0.7},
            zorder=5,
        ),
    ]
    specs = engine.build_specs_from_layers(
        ds, layers,
        settings={
            "title": "4 – Two-point abline (purple dash-dot)",
            "xlabel": "X", "ylabel": "Y",
            "figsize": (8, 6),
        },
    )
    fig = renderer.render(specs[0])
    fig.savefig(out / "04_two_point_abline.png", dpi=150)
    print("✓ 04_two_point_abline.png")

    # ---- 5. Polar text with angle channel ----
    df_polar = pd.DataFrame({
        "cat": ["A", "B", "C", "D"],
        "val": [1.0, 2.0, 1.5, 2.5],
    })
    ds_polar = Dataset(dataframe=df_polar, key_column="cat")
    layers = [
        Layer(
            geom=GeomLine(),
            stat=StatIdentity(),
            mapping={"x": "cat", "y": "val"},
            zorder=10,
        ),
        Layer(
            geom=GeomText(),
            stat=StatIdentity(),
            mapping={"x": "cat", "y": "val", "label": "cat",
                     "size": 12, "color": "darkblue"},
            zorder=20,
        ),
    ]
    specs = engine.build_specs_from_layers(
        ds_polar, layers,
        coord=CoordPolar(),
        settings={
            "title": "5 – Polar text (auto-aligned by coord)",
            "polar_tick_labels": True,
            "figsize": (6, 6),
        },
    )
    fig = renderer.render(specs[0])
    fig.savefig(out / "05_polar_text.png", dpi=150)
    print("✓ 05_polar_text.png")

    print("\nAll annotation demo outputs saved to:", out)


if __name__ == "__main__":
    main()
