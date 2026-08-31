"""Excel example: cluster marker shapes and color grouping."""

from pathlib import Path

import pandas as pd
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.engine import render_template
from geofig_engine.templates import bivariate

output_dir = Path(__file__).resolve().parent / "outputs" / "excel_output"

input_path = Path(__file__).resolve().parent / "excel_input" / "example_table.xlsx"
df = pd.read_excel(input_path, sheet_name="FINAL CLASSIFICATIONS")

analytes = [
    "sulfate_mg_L",
    "ca_ug_L",
    "mg_ug_l",
    "k_ug_L",
    "na_ug_L",
    "cl_mg_L",
    "ph",
    "temp",
    "alkalinity_mg_L",
]
color_columns = ["mag_anom", "corridor", "divide"]

dimensions = {
    "sulfate_mg_L": Dimension("sulfate_mg_L", {"role": "x"}),
    "cluster": Dimension("cluster", {"role": "marker"}),
}

for analyte in analytes:
    dimensions[analyte] = Dimension(analyte, {"type": "analyte"})
for color_col in color_columns:
    dimensions[color_col] = Dimension(color_col, {"role": "color"})

dataset = Dataset(dataframe=df, key_column="sample_id", dimensions=dimensions)
template = bivariate(mapping={"x": "sulfate_mg_L", "y": "{y}", "color": "{color}"})

iters = [
    DimensionIterator(
        channel="y",
        dimensions={"type": "analyte"},
        mode=DimensionIterator.Mode.DIMENSION,
    ),
    DimensionIterator(
        channel="color",
        dimensions={"role": "color"},
        mode=DimensionIterator.Mode.DIMENSION,
    )
]
specs, figures, legend_fig = render_template(
    dataset=dataset,
    template=template,
    settings={
        "xlabel": "sulfate_mg_L",
        "ylabel": "{y}",
        "title": "{y} vs sulfate_mg_L",
        "figsize": (8, 5),
    },
    iterators=iters,
    savedir=output_dir,
)
print(f"Saved {len(specs)} figures to {output_dir}")
