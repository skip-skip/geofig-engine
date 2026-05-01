"""Example showing metadata-based dimension grouping and iteration."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.dimension_selector import DimensionSelector
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.templates import BivariateTemplate

output_dir = Path(__file__).resolve().parent / "metadata_output"
output_dir.mkdir(exist_ok=True)

# A simple dataset with time series values for two sensors and two periods.
data = pd.DataFrame(
    {
        "time": [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3],
        "temp_A": [10, 11, 12, 15, 16, 17, 9, 10, 11, 14, 15, 16],
        "temp_B": [8, 9, 10, 12, 13, 14, 7, 8, 9, 11, 12, 13],
        "humidity_A": [60, 62, 61, 64, 65, 63, 59, 60, 62, 63, 64, 62],
        "humidity_B": [55, 56, 57, 58, 59, 60, 54, 55, 56, 57, 58, 59],
        "period": ["morning"] * 6 + ["afternoon"] * 6,
    }
)

# Define metadata for each column so we can group dimensions by their attributes.
dimensions = {
    "time": Dimension("time", {"role": "index"}),
    "temp_A": Dimension("temp_A", {"sensor": "A", "type": "temperature"}),
    "temp_B": Dimension("temp_B", {"sensor": "B", "type": "temperature"}),
    "humidity_A": Dimension("humidity_A", {"sensor": "A", "type": "humidity"}),
    "humidity_B": Dimension("humidity_B", {"sensor": "B", "type": "humidity"}),
    "period": Dimension("period", {"role": "category"}),
}

dataset = Dataset(dataframe=data, key_column="time", dimensions=dimensions)
engine = FigureEngine()
renderer = MatplotlibRenderer()
template = BivariateTemplate()

# Use metadata to select all temperature columns as the y source.
# Build one figure per period using the standard period column as the iterator.
mappings = {
    "x": ["time", "time"],  # duplicate time values for each grouped temperature series
    "y": DimensionSelector({"type": "temperature"}),
}

specs = engine.build_specs(
    dataset=dataset,
    template=template,
    mappings=mappings,
    iterator_selectors={"period": "period"},
    settings={"xlabel": "Time", "ylabel": "Temperature"},
)

print(f"Generated {len(specs)} specs using metadata grouping")
for spec, fig in zip(specs, engine.render_specs(specs, renderer)):
    period = spec.context["period"]
    filename = output_dir / f"temperature_{period}.png"
    fig.savefig(filename)
    print(f"Saved {filename}")

print("Done. See generated figures in examples/metadata_output.")
