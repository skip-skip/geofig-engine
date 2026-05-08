"""Excel example: cluster marker shapes and color grouping."""

from pathlib import Path
import sys

from geofig_engine.templates.timeseries import TimeseriesTemplate

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib.pyplot as plt
import pandas as pd
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.dimension_selector import DimensionSelector
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer

output_dir = Path(__file__).resolve().parent / "outputs" / "timeseries_output"
output_dir.mkdir(exist_ok=True)

input_path = Path(__file__).resolve().parent / "excel_input" / "example_lith.xlsx"
df = pd.read_excel(input_path)

dims = {}
for analyte in df.columns.tolist():
    if "_PPM" in analyte:
        dims[analyte] = Dimension(name=analyte, attributes={"analyte": True})
# Create a dataset from the Excel sheet.
dataset = Dataset(
    dataframe=df,
    key_column="Index", # Try Sample ID
    dimensions=dims,
)

engine = FigureEngine()
renderer = MatplotlibRenderer()
template = TimeseriesTemplate()

iters = [
    DimensionIterator(
        attribute="y",
        dimensions = dataset.get_dimensions("analyte", True),
        mode=DimensionIterator.Mode.DIMENSION,
    ),
]

mappings = {
    "x": "Sample Date",
    "y": "{y}",
    "color": "hole_id",
}
engine.render_and_save(
    dataset=dataset,
    template=template,
    mappings=mappings,
    iterators=iters,
    renderer=renderer,
    outdir=output_dir,
    #filename="timeseries_{y}.png",
    settings={
        "xlabel": "Time",
        "ylabel": "{y}",
        "title": None,
        "figsize": (8, 5),
    },
)
print(f"Done. See generated figures in {output_dir}.")
