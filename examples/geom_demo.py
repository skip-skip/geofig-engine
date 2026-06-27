"""Demonstration of all newly implemented geom types.

Shows GeomBox, GeomViolin, GeomStepLine, GeomHistogram, and
GeomBar with various configuration options and data arrangements.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.geom import GeomBar, GeomStepLine, GeomViolin
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatIdentity
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.templates import boxplot_with_points, histogram


def make_dataset() -> Dataset:
    rng = np.random.default_rng(42)
    rows = []
    for i in range(1, 301):
        cat = ["A", "B", "C", "D"][i % 4]
        grp = ["X", "Y", "Z"][i % 3]
        base = {"A": 10, "B": 20, "C": 30, "D": 25}[cat]
        rows.append({
            "id": i,
            "category": cat,
            "group": grp,
            "value": base + rng.normal(0, 3),
            "order": i,
            "step_y": float(np.sin(i * 0.1) * 5 + i * 0.03),
        })
    df = pd.DataFrame(rows)
    return Dataset(dataframe=df, key_column="id")


def main() -> None:
    out = Path(__file__).resolve().parent / "outputs" / "geom_demo"
    out.mkdir(parents=True, exist_ok=True)

    engine = FigureEngine()
    renderer = MatplotlibRenderer()
    ds = make_dataset()

    # ---- 1. Grouped box plot with points ----
    template = boxplot_with_points(
        mapping={"x": "category", "y": "value", "color": "group"},
        sort_mode="forward",
        jitter_width=0.08,
        point_alpha=0.25,
        point_size=8,
    )
    specs = engine.build_specs_from_template(
        ds, template,
        settings={"title": "Grouped Box Plot", "xlabel": "Category", "ylabel": "Value"},
    )
    fig = renderer.render(specs[0])
    fig.savefig(str(out / "01_grouped_box.png"))
    fig.clf()
    print("1/6  Grouped box plot saved")

    # ---- 2. Grouped violin plot ----
    violin_layers = [
        Layer(
            geom=GeomViolin(show_medians=True, sort_mode="forward"),
            stat=StatIdentity(),
            mapping={"x": "category", "y": "value", "color": "group"},
        )
    ]
    specs = engine.build_specs_from_layers(
        ds, violin_layers,
        settings={"title": "Grouped Violin Plot", "xlabel": "Category", "ylabel": "Value"},
    )
    fig = renderer.render(specs[0])
    fig.savefig(str(out / "02_grouped_violin.png"))
    fig.clf()
    print("2/6  Grouped violin plot saved")

    # ---- 3. Grouped bar chart (numeric x-positions pre-computed) ----
    grp_gap = 0.8
    bar_width = 0.2
    cat_order = ["A", "B", "C", "D"]
    grp_order = ["X", "Y", "Z"]

    rows = []
    for ci, cat in enumerate(cat_order):
        for gi, grp in enumerate(grp_order):
            offset = (gi - (len(grp_order) - 1) / 2) * bar_width
            x_pos = (ci + 1) + offset
            sub = ds.dataframe[(ds.dataframe["category"] == cat) & (ds.dataframe["group"] == grp)]
            rows.append({
                "id": f"{cat}_{grp}",
                "x_pos": x_pos,
                "mean_val": float(sub["value"].mean()),
                "category": cat,
                "group": grp,
            })
    bar_df = pd.DataFrame(rows)
    bar_ds = Dataset(dataframe=bar_df, key_column="id")

    bar_layers = [
        Layer(
            geom=GeomBar(),
            stat=StatIdentity(),
            mapping={"x": "x_pos", "y": "mean_val", "color": "group", "width": 0.2},
        )
    ]
    specs = engine.build_specs_from_layers(
        bar_ds, bar_layers,
        settings={
            "title": "Grouped Bar Chart",
            "xlabel": "Category",
            "ylabel": "Mean Value",
            "xticks": (list(range(1, 1 + len(cat_order))), cat_order),
        },
    )
    fig = renderer.render(specs[0])
    fig.savefig(str(out / "03_grouped_bar.png"))
    fig.clf()
    print("3/6  Grouped bar chart saved")

    # ---- 4. Step line plot ----
    step = ds.dataframe.sort_values("order")
    step_ds = Dataset(dataframe=step, key_column="id")
    step_layers = [
        Layer(
            geom=GeomStepLine(where="pre"),
            stat=StatIdentity(),
            mapping={"x": "order", "y": "step_y"},
        )
    ]
    specs = engine.build_specs_from_layers(
        step_ds, step_layers,
        settings={"title": "Step Line Plot", "xlabel": "Index", "ylabel": "Value"},
    )
    fig = renderer.render(specs[0])
    fig.savefig(str(out / "04_step_line.png"))
    fig.clf()
    print("4/6  Step line plot saved")

    # ---- 5. Histogram (density) ----
    tmpl = histogram(
        mapping={"x": "value", "alpha": 0.7},
        bins=20, density=True,
    )
    specs = engine.build_specs_from_template(
        ds, tmpl,
        settings={"title": "Histogram (Density)", "xlabel": "Value", "ylabel": "Density"},
    )
    fig = renderer.render(specs[0])
    fig.savefig(str(out / "05_histogram_density.png"))
    fig.clf()
    print("5/6  Density histogram saved")

    # ---- 6. Histogram (cumulative) ----
    tmpl = histogram(
        mapping={"x": "value", "color": "forestgreen", "alpha": 0.7},
        bins=20, density=True, cumulative=True,
    )
    specs = engine.build_specs_from_template(
        ds, tmpl,
        settings={
            "title": "Histogram (Cumulative Density)",
            "xlabel": "Value",
            "ylabel": "Cumulative Density",
        },
    )
    fig = renderer.render(specs[0])
    fig.savefig(str(out / "06_histogram_cumulative.png"))
    fig.clf()
    print("6/6  Cumulative histogram saved")

    print(f"\nAll figures saved to: {out}")


if __name__ == "__main__":
    main()
