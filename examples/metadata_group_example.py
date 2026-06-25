"""Example showing metadata-based dimension grouping with faceting."""

from pathlib import Path

import pandas as pd
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.dimension import Dimension
from geofig_engine.core.facet import FacetWrap
from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatIdentity
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.templates.base import FigureTemplate

output_dir = Path(__file__).resolve().parent / "outputs" / "metadata_output"
output_dir.mkdir(exist_ok=True)

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

temp_cols = dataset.query_dimensions("type", "temperature")
layers = [
    Layer(geom=GeomPoint(), stat=StatIdentity(), mapping={"x": "time", "y": col})
    for col in temp_cols
]
template = FigureTemplate(layers=layers, default_settings={"figsize": (10, 6), "xscale": "linear", "yscale": "linear", "grid": True})

specs = engine.build_specs_from_template(
    dataset=dataset, template=template,
    settings={"xlabel": "Time", "ylabel": "Temperature"},
    facet=FacetWrap(by="period"),
)
print(f"Generated {len(specs)} spec(s)")
for spec, fig in zip(specs, engine.render_specs(specs, renderer)):
    fig.savefig(output_dir / "temperature_faceted.png")
    print("Saved temperature_faceted.png")

print("Done. See generated figure in examples/metadata_output.")
