"""Timeseries example: generates time-series figures from lithology data."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.templates import timeseries

output_dir = Path(__file__).resolve().parent / "outputs" / "timeseries_output"
output_dir.mkdir(exist_ok=True)

input_path = Path(__file__).resolve().parent / "excel_input" / "example_lith.xlsx"
df = pd.read_excel(input_path)

dims = {}
for analyte in df.columns.tolist():
    if "_PPM" in analyte:
        dims[analyte] = Dimension(name=analyte, labels={"analyte": True})
# Create a dataset from the Excel sheet.
dataset = Dataset(
    dataframe=df,
    key_column="Index",
    dimensions=dims,
)

engine = FigureEngine()
renderer = MatplotlibRenderer()
template = timeseries(mapping={"x": "Sample Date", "y": "{y}", "color": "hole_id"})

iters = [
    DimensionIterator(
        channel="y",
        dimensions=dataset.query_dimensions("analyte", True),
        mode=DimensionIterator.Mode.DIMENSION,
    ),
]

specs = engine.build_specs_from_template(
    dataset=dataset,
    template=template,
    settings={
        "xlabel": "Time",
        "ylabel": "{y}",
        "title": None,
        "figsize": (8, 5),
        "figname": "timeseries_{y}",
    },
    iterators=iters,
)

figures = engine.render_specs(specs, renderer)
for spec, fig in zip(specs, figures):
    figname = spec.settings.get("figname", "timeseries")
    fig.savefig(output_dir / f"{figname}.png")
    plt.close(fig)

legend_fig = engine.render_legend(renderer)
legend_fig.savefig(output_dir / "legend.png")
plt.close(legend_fig)
print(f"Done. See generated figures in {output_dir}.")
