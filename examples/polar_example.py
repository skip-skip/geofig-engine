"""Demonstration of polar plots: pie chart, radar chart, and polar scatter."""

from pathlib import Path

import numpy as np
import pandas as pd

from geofig_engine.core.coord import CoordPolar
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatIdentity
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.templates import pie, radar


def make_pie_data() -> Dataset:
    rows = [
        {"category": "Apples", "value": 30},
        {"category": "Bananas", "value": 45},
        {"category": "Cherries", "value": 15},
        {"category": "Dates", "value": 10},
    ]
    df = pd.DataFrame(rows)
    return Dataset(dataframe=df, key_column="category")


def make_radar_data() -> Dataset:
    rng = np.random.default_rng(42)
    rows = []
    categories = ["Speed", "Strength", "Agility", "Endurance", "Intelligence"]
    for hero in ["Alpha", "Beta", "Gamma"]:
        for cat in categories:
            rows.append({
                "hero": hero,
                "trait": cat,
                "score": rng.uniform(20, 100),
            })
    df = pd.DataFrame(rows)
    df["id"] = range(len(df))
    return Dataset(dataframe=df, key_column="id")


def make_scatter_data() -> Dataset:
    rng = np.random.default_rng(42)
    n = 200
    rows = []
    for i in range(n):
        angle = rng.uniform(0, 2 * np.pi)
        radius = rng.uniform(0, 10)
        group = ["Red", "Blue"][i % 2]
        rows.append({
            "angle": angle,
            "radius": radius,
            "group": group,
            "size": rng.uniform(10, 100),
            "id": i,
        })
    df = pd.DataFrame(rows)
    return Dataset(dataframe=df, key_column="id")


def main() -> None:
    out = Path(__file__).resolve().parent / "outputs" / "polar"
    out.mkdir(parents=True, exist_ok=True)

    engine = FigureEngine()
    renderer = MatplotlibRenderer()

    # ---- 1. Pie chart ----
    pie_ds = make_pie_data()
    tmpl = pie(
        mapping={"x": "category", "y": "value"},
    )
    specs = engine.build_specs_from_template(
        pie_ds, tmpl,
        settings={"axis": {"title": "Fruit Distribution"}},
    )
    fig = renderer.render(specs[0])
    fig.savefig(str(out / "01_pie_chart.png"))
    fig.clf()
    print("1/5  Pie chart saved")

    # ---- 1b. Pie chart with percent + count ----
    tmpl2 = pie(
        mapping={"x": "category", "y": "value"},
        show_percent=True,
        show_count=True,
        show_name=True,
    )
    specs2 = engine.build_specs_from_template(
        pie_ds, tmpl2,
        settings={"axis": {"title": "Fruit Distribution (with labels)"}},
    )
    fig2 = renderer.render(specs2[0])
    fig2.savefig(str(out / "01b_pie_chart_labeled.png"))
    fig2.clf()
    print("2/5  Labeled pie chart saved")

    # ---- 1c. Pie chart with percent only, no name ----
    tmpl3 = pie(
        mapping={"x": "category", "y": "value"},
        show_percent=True,
        show_name=False,
    )
    specs3 = engine.build_specs_from_template(
        pie_ds, tmpl3,
        settings={"axis": {"title": "Fruit Distribution (percent only)"}},
    )
    fig3 = renderer.render(specs3[0])
    fig3.savefig(str(out / "01c_pie_chart_pct_only.png"))
    fig3.clf()
    print("3/5  Percent-only pie chart saved")

    # ---- 2. Radar chart ----
    radar_ds = make_radar_data()
    tmpl = radar(
        mapping={"x": "trait", "y": "score", "color": "hero"},
        fill=True,
        fill_alpha=0.1,
    )
    specs = engine.build_specs_from_template(
        radar_ds, tmpl,
        settings={"axis": {"title": "Hero Attributes"}},
    )
    fig = renderer.render(specs[0])
    fig.savefig(str(out / "02_radar_chart.png"))
    fig.clf()
    print("4/5  Radar chart saved")

    # ---- 3. Polar scatter ----
    scat_ds = make_scatter_data()
    layers = [
        Layer(
            geom=GeomPoint(),
            stat=StatIdentity(),
            mapping={"x": "angle", "y": "radius", "color": "group", "size": "size"},
        ),
    ]
    specs = engine.build_specs_from_layers(
        scat_ds, layers,
        settings={
            "title": "Polar Scatter",
            "xlabel": "Angle (rad)",
            "ylabel": "Radius",
        },
        coord=CoordPolar(),
    )
    fig = renderer.render(specs[0])
    fig.savefig(str(out / "03_polar_scatter.png"))
    fig.clf()
    print("5/5  Polar scatter saved")

    print(f"\nAll 5 polar figures saved to: {out}")


if __name__ == "__main__":
    main()
