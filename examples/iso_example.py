"""Isotope example: demonstrates water isotope reference lines with Idaho and global data."""

from pathlib import Path

import pandas as pd
from geofig_engine.core.dataset import Dataset
from geofig_engine.engine import render_template
from geofig_engine.templates import isotope
from geofig_engine.data.geom_presets import get_geom_preset_registry

output_dir = Path(__file__).resolve().parent / "outputs" / "iso_output"

input_path = Path(__file__).resolve().parent / "excel_input" / "example_iso.xlsx"
df = pd.read_excel(input_path)

color_column = "Location"
dataset = Dataset(dataframe=df, key_column="Sample ID", dimensions={})

registry = get_geom_preset_registry()
gmwl = registry.get("GMWL")
idaho_presets = [p for p in registry.filter(state="ID") if p.id != gmwl.id]
selected_function_ids = ["GMWL"] + [p.id for p in idaho_presets]

print(f"Selected functions: {selected_function_ids}")
print(f"  - Global: GMWL")
print(f"  - Idaho lines: {[p.id for p in idaho_presets]}")

template = isotope(functions=selected_function_ids, mapping={"x": "Oxygen 18", "y": "Deuterium", "color": color_column})

render_template(
    dataset=dataset,
    template=template,
    settings={"title": "Deuterium vs Oxygen 18", "figsize": (8, 5)},
    savedir=output_dir,
)
print(f"Done. See generated figures in {output_dir}.")
