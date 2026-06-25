"""Simple FigEngine example.

Creates a small dataset, builds figure specs using a bivariate preset,
and renders them with MatplotlibRenderer.
"""

from pathlib import Path

import pandas as pd

from geofig_engine.core.dataset import Dataset
from geofig_engine.engine import EngineConfig, FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.templates import bivariate
from geofig_engine.core.iterator import DimensionIterator


def main() -> None:
    output_dir = Path(__file__).resolve().parent / "outputs" / "simple_output"
    output_dir.mkdir(exist_ok=True)

    data = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6],
            "x": [1, 2, 3, 2, 4, 5],
            "y": [2, 3, 5, 4, 6, 8],
            "group": ["A", "A", "B", "B", "C", "C"],
            "size": [30, 40, 20, 50, 60, 30],
            "color": ["red", "red", "blue", "blue", "green", "green"],
        }
    )

    dataset = Dataset(dataframe=data, key_column="id")

    template = bivariate(mapping={"x": "x", "y": "y", "color": "color", "size": "size"})
    engine = FigureEngine(config=EngineConfig(default_settings={"xlabel": "X value", "ylabel": "Y value"}))
    renderer = MatplotlibRenderer()

    iterator = DimensionIterator(channel="group", dimensions=["group"], mode=DimensionIterator.Mode.VALUE)
    specs = engine.build_specs_from_template(dataset=dataset, template=template, iterators=iterator)

    print(f"Created {len(specs)} figure specs")

    for index, spec in enumerate(specs, start=1):
        fig = renderer.render(spec)
        group_value = spec.context.get("group", f"figure_{index}")
        output_file = output_dir / f"group_{group_value}.png"
        fig.savefig(output_file)
        fig.clf()
        print(f"Saved {output_file}")

    print("Example complete. See the generated PNG files in examples/output.")


if __name__ == "__main__":
    main()
