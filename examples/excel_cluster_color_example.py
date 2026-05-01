"""Excel example: cluster marker shapes and color grouping."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib.pyplot as plt
import pandas as pd
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.dimension_selector import DimensionSelector
from geofig_engine.core.iterator import ColumnSelector
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.templates import BivariateTemplate

output_dir = Path(__file__).resolve().parent / "excel_output"
output_dir.mkdir(exist_ok=True)

input_path = Path(__file__).resolve().parent / "excel_input" / "example_table.xlsx"
df = pd.read_excel(input_path, sheet_name="FINAL CLASSIFICATIONS")

# Define analytes and color grouping columns.
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

# Assign metadata to analyte and marker dimensions.
dimensions = {
    "sulfate_mg_L": Dimension("sulfate_mg_L", {"role": "x"}),
    "cluster": Dimension("cluster", {"role": "marker"}),
}
for analyte in analytes:
    dimensions[analyte] = Dimension(analyte, {"type": "analyte"})
for color_col in color_columns:
    dimensions[color_col] = Dimension(color_col, {"role": "color"})

# Create a dataset from the Excel sheet.
dataset = Dataset(
    dataframe=df,
    key_column="sample_id",
    dimensions=dimensions,
)

engine = FigureEngine()
renderer = MatplotlibRenderer()
template = BivariateTemplate()

mappings = {
    "x": "sulfate_mg_L",
    "y": "{y}",
    "color": "{color}",
    "marker": "cluster",
}

iterator_selectors = {
    "y": ColumnSelector(DimensionSelector({"type": "analyte"})),
    "color": ColumnSelector(color_columns),
}

specs = engine.build_specs(
    dataset=dataset,
    template=template,
    mappings=mappings,
    iterator_selectors=iterator_selectors,
    settings={
        "xlabel": "sulfate_mg_L",
        "title": "Analyte vs sulfate_mg_L",
        "figsize": (8, 5),
    },
)

figures = engine.render_specs(specs, renderer)

for spec, fig in zip(specs, figures):
    analyte = spec.context["y"]
    color_trait = spec.context["color"]
    filename = output_dir / f"{analyte}_by_{color_trait}.png"
    fig.savefig(filename)
    plt.close(fig)
    print(f"Saved {filename}")

print("Done. See generated figures in examples/excel_output.")
