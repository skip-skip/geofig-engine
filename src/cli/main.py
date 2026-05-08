from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer
from geofig_engine.templates.timeseries import TimeseriesTemplate
from geofig_engine.templates.isotope import IsotopeTemplate


# ---------------------------------------------------
# TEMPLATE REGISTRY
# ---------------------------------------------------
TEMPLATE_REGISTRY = {
    "timeseries": TimeseriesTemplate,
    "isotope": IsotopeTemplate,
}


# ---------------------------------------------------
# DATA LOADING
# ---------------------------------------------------
def load_dataset(path: Path, key_column: str) -> Dataset:
    if path.suffix.lower() not in {".xlsx", ".xls", ".csv"}:
        raise ValueError("Only .xlsx, .xls, or .csv files are supported")

    return Dataset.load_dataset(filepath=path, key_column=key_column)


# ---------------------------------------------------
# USER INPUT HELPERS
# ---------------------------------------------------
def prompt(msg: str) -> str:
    return input(f"{msg}: ").strip()


def choose_option(title: str, options: list[str]) -> str:
    print(f"\n{title}")
    for i, opt in enumerate(options):
        print(f"{i + 1}. {opt}")
    idx = int(prompt("Select")) - 1
    return options[idx]


# ---------------------------------------------------
# TEMPLATE SELECTION
# ---------------------------------------------------
def select_template() -> Any:
    name = choose_option("Available templates", list(TEMPLATE_REGISTRY.keys()))
    template_cls = TEMPLATE_REGISTRY[name]

    # special handling for isotope lines
    if name == "isotope":
        lines = list(IsotopeTemplate.MeteoricWaterLines)

        print("\nAvailable isotope lines:")
        for i, line in enumerate(lines):
            print(f"{i + 1}. {line.name}")

        raw = prompt("Select lines (comma-separated indices, or blank for none)")

        selected = []
        if raw:
            selected = [
                lines[int(i) - 1]
                for i in raw.split(",")
                if i.strip().isdigit()
            ]

        return template_cls(lines=selected)

    return template_cls()


# ---------------------------------------------------
# ITERATOR CONFIGURATION
# ---------------------------------------------------
def build_iterators(dataset: Dataset) -> list[DimensionIterator]:
    iters: list[DimensionIterator] = []

    if prompt("Create iterators? (y/n)").lower() != "y":
        return iters

    dims = list(dataset.get_all_attributes().keys())

    while True:
        print("\nAvailable dimensions:")
        for i, d in enumerate(dims):
            print(f"{i + 1}. {d}")

        attr = prompt("Iterator channel (or blank to stop)")
        if not attr:
            break

        dim = dims[int(prompt("Select dimension")) - 1]

        iters.append(
            DimensionIterator(
                attribute=attr,
                dimensions=dataset.get_dimensions(dim, True),
                mode=DimensionIterator.Mode.DIMENSION,
            )
        )

    return iters


# ---------------------------------------------------
# MAPPING CONFIGURATION
# ---------------------------------------------------
def build_mappings(template, dataset: Dataset) -> dict[str, Any]:
    mappings: dict[str, Any] = {}

    print("\nConfigure mappings (leave blank to skip)\n")

    for key in template.supported_mappings:
        value = prompt(f"{key}")
        if value:
            mappings[key] = value

    return mappings


# ---------------------------------------------------
# SETTINGS CONFIGURATION
# ---------------------------------------------------
def build_settings(template) -> dict[str, Any]:
    settings = dict(template.default_settings)

    print("\nConfigure settings (leave blank to keep default)\n")

    for key, default in template.default_settings.items():
        value = prompt(f"{key} [{default}]")
        if value:
            settings[key] = value

    return settings


# ---------------------------------------------------
# OUTPUT DIRECTORY
# ---------------------------------------------------
def get_output_dir() -> Path:
    path = Path(prompt("Output directory"))
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------
# MAIN CLI WORKFLOW
# ---------------------------------------------------
def run_cli():
    print("\n=== FigEngine CLI ===\n")

    input_path = Path(prompt("Input file path (xlsx/csv)"))
    key_column = prompt("Key column")

    dataset = load_dataset(input_path, key_column)

    template = select_template()
    renderer = MatplotlibRenderer()
    engine = FigureEngine()

    iterators = build_iterators(dataset)
    mappings = build_mappings(template, dataset)
    settings = build_settings(template)
    outdir = get_output_dir()

    print("\nRendering...\n")

    engine.render_and_save(
        dataset=dataset,
        template=template,
        mappings=mappings,
        iterators=iterators,
        renderer=renderer,
        outdir=str(outdir),
        settings=settings,
    )

    print(f"\nDone. Output saved to: {outdir}\n")


if __name__ == "__main__":
    run_cli()