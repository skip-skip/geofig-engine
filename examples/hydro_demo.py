"""Demonstration of hydrogeochemistry plot types: Piper, Stiff, and
ARD classification diagrams (NAGpH, ANP/AGP, NPR/NNP)."""

from pathlib import Path

import numpy as np
import pandas as pd

from geofig_engine.core.dataset import Dataset
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.templates import (
    anp_agp,
    build_piper_specs,
    nagph_nag,
    npr_nnp,
    plot_stiff,
)


def make_piper_data() -> Dataset:
    rng = np.random.default_rng(42)
    rows = []
    water_types = {
        "Ca-HCO3": {"Ca": 60, "Mg": 10, "Na+K": 10,
                      "HCO3": 150, "SO4": 10, "Cl": 10},
        "Na-Cl":   {"Ca": 10, "Mg": 10, "Na+K": 60,
                      "HCO3": 10, "SO4": 10, "Cl": 150},
        "Ca-SO4":  {"Ca": 60, "Mg": 10, "Na+K": 10,
                      "HCO3": 10, "SO4": 150, "Cl": 10},
        "Na-HCO3": {"Ca": 10, "Mg": 10, "Na+K": 60,
                      "HCO3": 150, "SO4": 10, "Cl": 10},
    }
    for wt, base in water_types.items():
        for _ in range(8):
            row = {}
            for k, v in base.items():
                row[k] = max(v + rng.uniform(-v * 0.1, v * 0.1), 0.1)
            row["site"] = wt
            rows.append(row)
    df = pd.DataFrame(rows)
    return Dataset(dataframe=df, key_column="Ca")


def make_classification_data() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    for typ in ["Fresh", "Transition", "Mine"]:
        if typ == "Fresh":
            centre = (5, 15)
        elif typ == "Transition":
            centre = (4, 8)
        else:
            centre = (3, 4)
        for _ in range(15):
            rows.append({
                "npr": max(rng.normal(centre[0], 1.5), 0.1),
                "nnp": max(rng.normal(centre[1], 5), 0.1),
                "agp": max(2 + rng.normal(centre[0], 1), 0.1),
                "anp": max(5 + rng.normal(centre[1], 3), 0.1),
                "nag_ph": max(rng.normal(centre[1] / 4, 1), 1),
                "nag": max(rng.normal(20 - centre[0] * 3, 5), 0),
                "type": typ,
            })
    return pd.DataFrame(rows)


def main() -> None:
    out = Path(__file__).resolve().parent / "outputs" / "hydro_demo"
    out.mkdir(parents=True, exist_ok=True)

    engine = FigureEngine()
    renderer = MatplotlibRenderer()

    # ------------------------------------------------------------------
    # 1. Piper diagram — colour by site category
    # ------------------------------------------------------------------
    pipe_ds = make_piper_data()
    specs = build_piper_specs(
        data=pipe_ds.dataframe,
        left_tri=("Ca", "Mg", "Na+K"),
        right_tri=("HCO3", "SO4", "Cl"),
        mapping={"color": "site", "marker": "site"},
        title="1 – Piper Diagram (colour by site)",
    )
    fig = renderer.render(specs[0])
    fig.savefig(out / "01_piper.png", dpi=150)
    fig.clf()
    print("1/7  Piper diagram saved")

    # ------------------------------------------------------------------
    # 2. Piper with extra data
    # ------------------------------------------------------------------
    extra = pd.DataFrame({
        "Ca": [30.0], "Mg": [20.0], "Na+K": [10.0],
        "HCO3": [100.0], "SO4": [40.0], "Cl": [15.0],
        "site": ["X"],
    })
    extra_specs = build_piper_specs(
        extra,
        mapping={"color": "site", "marker": "site"},
        title="2 – Piper Extra Sample",
    )
    fig = renderer.render(extra_specs[0])
    fig.savefig(out / "02_piper_overlay.png", dpi=150)
    fig.clf()
    print("2/7  Piper extra sample saved")

    # ------------------------------------------------------------------
    # 3. Stiff diagram — single sample
    # ------------------------------------------------------------------
    spec = plot_stiff(ca=45, mg=12, na_k=20, cl=15, hco3=130, so4=25,
                      title="3 – Stiff Diagram (Sample X)")
    fig = renderer.render(spec)
    fig.savefig(out / "03_stiff_single.png", dpi=150)
    fig.clf()
    print("3/7  Stiff diagram saved")

    # ------------------------------------------------------------------
    # 4. Stiff diagram — large sample
    # ------------------------------------------------------------------
    spec2 = plot_stiff(ca=250, mg=80, na_k=310, cl=420, hco3=360, so4=580,
                       title="4 – Stiff Diagram (high TDS)")
    fig = renderer.render(spec2)
    fig.savefig(out / "04_stiff_large.png", dpi=150)
    fig.clf()
    print("4/7  Stiff diagram (high TDS) saved")

    # ------------------------------------------------------------------
    # 5. NAG pH vs NAG classification
    # ------------------------------------------------------------------
    cls_df = make_classification_data()
    cls_ds = Dataset(dataframe=cls_df, key_column="npr")
    tmpl = nagph_nag(mapping={"x": "nag_ph", "y": "nag", "color": "type"})
    specs = engine.build_specs_from_template(
        cls_ds, tmpl,
        settings={"axis": {"title": "5 – NAG pH vs NAG Classification"}},
    )
    fig = renderer.render(specs[0])
    fig.savefig(out / "05_nagph_nag.png", dpi=150)
    fig.clf()
    print("5/7  NAG pH vs NAG saved")

    # ------------------------------------------------------------------
    # 6. ANP vs AGP classification
    # ------------------------------------------------------------------
    tmpl = anp_agp(mapping={"x": "agp", "y": "anp", "color": "type"})
    specs = engine.build_specs_from_template(
        cls_ds, tmpl,
        settings={"axis": {"title": "6 – ANP vs AGP Classification"}},
    )
    fig = renderer.render(specs[0])
    fig.savefig(out / "06_anp_agp.png", dpi=150)
    fig.clf()
    print("6/7  ANP vs AGP saved")

    # ------------------------------------------------------------------
    # 7. NPR vs NNP ARD classification
    # ------------------------------------------------------------------
    tmpl = npr_nnp(mapping={"x": "npr", "y": "nnp", "color": "type"},
                   npr_crit=3, nnp_crit=20)
    specs = engine.build_specs_from_template(
        cls_ds, tmpl,
        settings={"axis": {"title": "7 – NPR vs NNP ARD Classification"}},
    )
    fig = renderer.render(specs[0])
    fig.savefig(out / "07_npr_nnp.png", dpi=150)
    fig.clf()
    print("7/7  NPR vs NNP saved")

    print(f"\nAll figures saved to: {out}")


if __name__ == "__main__":
    main()
