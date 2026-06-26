"""Isotope example: demonstrates water isotope reference lines with Idaho and global data."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from geofig_engine.core.dataset import Dataset
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.templates import isotope
from geofig_engine.data import get_function_registry

output_dir = Path(__file__).resolve().parent / "outputs" / "iso_output"
output_dir.mkdir(exist_ok=True)

input_path = Path(__file__).resolve().parent / "excel_input" / "example_iso.xlsx"
df = pd.read_excel(input_path)

color_column = "Location"
# Create a dataset from the Excel sheet.
dataset = Dataset(
    dataframe=df,
    key_column="Sample ID",
    dimensions={},
)

# Query the function registry for water isotope lines
registry = get_function_registry()

# Get the global meteoric water line
gmwl_func = registry.get("GMWL")

# Get all Idaho water isotope lines
idaho_funcs = registry.get_by_state("ID")

# Combine GMWL with all Idaho lines
selected_function_ids = ["GMWL"] + [f.id for f in idaho_funcs if f.id != "GMWL"]

print(f"Selected functions: {selected_function_ids}")
print(f"  - Global: GMWL")
print(f"  - Idaho lines: {[f.id for f in idaho_funcs if f.id != 'GMWL']}")

engine = FigureEngine()
renderer = MatplotlibRenderer()
template = isotope(functions=selected_function_ids, mapping={"x": "Oxygen 18", "y": "Deuterium", "color": color_column})

specs = engine.build_specs_from_template(
    dataset=dataset,
    template=template,
    settings={
        "title": "Deuterium vs Oxygen 18",
        "figsize": (8, 5),
    },
)

figures = engine.render_specs(specs, renderer)
for spec, fig in zip(specs, figures):
    fig.savefig(output_dir / "iso.png")
    plt.close(fig)
print(f"Done. See generated figures in {output_dir}.")
