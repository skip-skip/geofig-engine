"""Minimal batch figure generation example."""

from pathlib import Path

import pandas as pd
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.templates import bivariate

out = Path(__file__).resolve().parent / "outputs" / "batch_output"
out.mkdir(exist_ok=True)

data = pd.DataFrame(
    {
        "id": [1, 2, 3, 4, 5, 6],
        "x": [1, 2, 3, 4, 5, 6],
        "y": [2, 1, 4, 3, 6, 5],
        "group": ["A", "A", "B", "B", "C", "C"],
        "color": ["red", "red", "blue", "blue", "green", "green"],
    }
)

engine = FigureEngine()
dataset = Dataset(dataframe=data, key_column="id")
template = bivariate(mapping={"x": "x", "y": "y", "color": "color"})

iterator = DimensionIterator(channel="group", dimensions=["group"], mode=DimensionIterator.Mode.VALUE)
specs = engine.build_specs_from_template(dataset, template=template, iterators=iterator)

renderer = MatplotlibRenderer()
figures = engine.render_specs(specs, renderer)
for spec, fig in zip(specs, figures):
    fig.savefig(out / f"group_{spec.context['group']}.png")
