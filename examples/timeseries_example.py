"""Timeseries example: generates time-series figures from lithology data."""

from pathlib import Path

import pandas as pd
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.engine import render_template
from geofig_engine.templates import timeseries

output_dir = Path(__file__).resolve().parent / "outputs" / "timeseries_output"

input_path = Path(__file__).resolve().parent / "excel_input" / "example_lith.xlsx"
df = pd.read_excel(input_path)

dims = {}
for analyte in df.columns.tolist():
    if "_PPM" in analyte:
        dims[analyte] = Dimension(name=analyte, labels={"analyte": True})
dataset = Dataset(
    dataframe=df,
    key_column="Index",
    dimensions=dims,
)

template = timeseries(mapping={"x": "Sample Date", "y": "{y}", "color": "hole_id"})

iters = [
    DimensionIterator(
        channel="y",
        dimensions=dataset.query_dimensions("analyte", True),
        mode=DimensionIterator.Mode.DIMENSION,
    ),
]

specs, figures, legend_fig = render_template(
    dataset=dataset,
    template=template,
    settings={
        "axis": {
            "xlabel": "Time",
            "ylabel": "{y}",
        },
        "figsize": (8, 5),
        "figname": "timeseries_{y}",
    },
    iterators=iters,
    savedir=output_dir,
)
print(f"Done. See generated figures in {output_dir}.")
