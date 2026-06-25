"""Isotope example: demonstrates water isotope reference lines with Idaho and global data."""

from pathlib import Path
import sys

from geofig_engine.templates.isotope import IsotopeTemplate
from geofig_engine.data import get_function_registry
from geofig_engine.utils.typing import Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib.pyplot as plt
import pandas as pd
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.dimension_selector import DimensionSelector
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer

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
template = IsotopeTemplate(functions=selected_function_ids)

mappings = {
    Mapping.OXYGEN_18: "Oxygen 18",
    Mapping.DEUTERIUM: "Deuterium",
    Mapping.COLOR: color_column,
}

iters = [
    DimensionIterator(
        channel="color",
        dimensions = color_column,
        mode=DimensionIterator.Mode.VALUE,
    ),
]
iters = None
engine.render_and_save(
    dataset=dataset,
    template=template,
    mappings=mappings,
    iterators=iters,
    renderer=renderer,
    outdir=output_dir,
    #filename="iso_{color}.png",
    settings={
        "xlabel": "Oxygen 18",
        "ylabel": "Deuterium",
        "title": "Deuterium vs Oxygen 18",
        "figsize": (8, 5),
    },
)
print(f"Done. See generated figures in {output_dir}.")
