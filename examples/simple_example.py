"""Simple FigEngine example.

This example creates a small dataset, builds one or more figure specs using
FigureEngine and BivariateTemplate, and renders them with MatplotlibRenderer.
"""

from pathlib import Path

import pandas as pd

from geofig_engine.core.dataset import Dataset
from geofig_engine.engine import EngineConfig, FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.templates import BivariateTemplate


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

    template = BivariateTemplate()
    engine = FigureEngine(config=EngineConfig(default_settings={"xlabel": "X value", "ylabel": "Y value"}))
    renderer = MatplotlibRenderer()

    mappings = {
        "x": "x",
        "y": "y",
        "color": "color",
        "size": "size",
    }

    iterator_selectors = {"group": "group"}

    specs = engine.build_specs(
        dataset=dataset,
        template=template,
        mappings=mappings,
        iterator_selectors=iterator_selectors,
    )

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
