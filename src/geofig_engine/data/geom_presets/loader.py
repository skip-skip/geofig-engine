"""
Load geometry preset JSON files.

Bundled presets live next to this module (one JSON file per category).
User-supplied files can be merged into a registry via
GeomPresetRegistry.merge_path().
"""

import json
from pathlib import Path

from geofig_engine.data.geom_presets.models import GeomPreset
from geofig_engine.data.geom_presets.validation import validate_preset_data


class GeomPresetLoadError(Exception):
    """Raised when preset JSON loading or validation fails."""


class GeomPresetLoader:
    """Load and validate geom presets from JSON files/directories."""

    @staticmethod
    def bundled_dir() -> Path:
        """Directory containing the package's bundled preset JSON files."""
        return Path(__file__).parent

    @classmethod
    def load_dir(cls, dir_path: Path | str) -> list[GeomPreset]:
        """
        Load all preset JSON files in a directory (sorted by filename).

        Args:
            dir_path: Directory containing *.json preset files

        Returns:
            List of validated GeomPreset instances

        Raises:
            GeomPresetLoadError: If directory missing, empty, or invalid
        """
        directory = Path(dir_path)
        if not directory.is_dir():
            raise GeomPresetLoadError(f"Preset directory not found: {directory}")

        files = sorted(directory.glob("*.json"))
        if not files:
            raise GeomPresetLoadError(f"No preset JSON files found in {directory}")

        presets: list[GeomPreset] = []
        for path in files:
            presets.extend(cls.load_file(path))
        return presets

    @classmethod
    def load_file(cls, file_path: Path | str) -> list[GeomPreset]:
        """
        Load presets from a single JSON file.

        Expected schema::

            {"presets": [ {<preset entry>}, ... ]}

        Args:
            file_path: Path to the JSON file

        Returns:
            List of validated GeomPreset instances

        Raises:
            GeomPresetLoadError: If file missing, JSON invalid, or schema violated
        """
        path = Path(file_path)

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as e:
            raise GeomPresetLoadError(f"Preset file not found: {path}") from e
        except json.JSONDecodeError as e:
            raise GeomPresetLoadError(f"Invalid JSON in {path}: {e}") from e

        if not isinstance(raw, dict) or "presets" not in raw:
            raise GeomPresetLoadError(
                f"{path}: root must be an object containing a 'presets' key"
            )

        entries = raw["presets"]
        if not isinstance(entries, list):
            raise GeomPresetLoadError(f"{path}: 'presets' must be an array")

        presets: list[GeomPreset] = []
        for idx, entry in enumerate(entries):
            pid = entry.get("id", "unknown") if isinstance(entry, dict) else "unknown"
            try:
                presets.append(validate_preset_data(entry))
            except Exception as e:
                raise GeomPresetLoadError(
                    f"{path}: failed to load preset at index {idx} (id: {pid}): {e}"
                ) from e

        return presets
