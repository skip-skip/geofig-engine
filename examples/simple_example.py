"""Simple FigEngine example."""

from pathlib import Path

import pandas as pd
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.engine import render_template
from geofig_engine.templates import bivariate


def main() -> None:
    output_dir = Path(__file__).resolve().parent / "outputs" / "simple_output"

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

    iterator = DimensionIterator(channel="group", dimensions=["group"], mode=DimensionIterator.Mode.VALUE)
    specs, figures, legend_fig = render_template(
        dataset=dataset,
        template=template,
        settings={"xlabel": "X value", "ylabel": "Y value"},
        iterators=iterator,
        savedir=output_dir,
    )
    print(f"Created {len(specs)} figure specs")
    print("Example complete. See the generated PNG files in examples/outputs/simple_output.")


if __name__ == "__main__":
    main()
