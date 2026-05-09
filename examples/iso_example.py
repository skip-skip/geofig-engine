"""Excel example: cluster marker shapes and color grouping."""

from pathlib import Path
import sys

from geofig_engine.templates.isotope import IsotopeTemplate

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

engine = FigureEngine()
renderer = MatplotlibRenderer()
template = IsotopeTemplate([IsotopeTemplate.MeteoricWaterLines.GLOBAL, 
                            IsotopeTemplate.MeteoricWaterLines.ID_FALLS,
                            IsotopeTemplate.MeteoricWaterLines.ID_SOUTHEAST,
                            IsotopeTemplate.MeteoricWaterLines.ID_SNAKERIVER])

mappings = {
    "x": "Oxygen 18",
    "y": "Deuterium",
    "color": color_column,
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
