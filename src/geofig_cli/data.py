from pathlib import Path

from geofig_engine.core.dataset import Dataset


def load_dataset(path: Path, key_column: str|None=None) -> Dataset:
    if path.suffix.lower() not in {".xlsx", ".xls", ".csv"}:
        raise ValueError("Only .xlsx, .xls, or .csv files are supported")

    return Dataset.load_dataset(filepath=path)