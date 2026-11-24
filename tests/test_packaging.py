"""Packaging metadata regressions for shareable v0.5.0 distributions."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def _requirement_names(requirements: list[str]) -> set[str]:
    return {
        re.split(r"[<>=!~\[;]", requirement, maxsplit=1)[0]
        .strip()
        .lower()
        .replace("_", "-")
        for requirement in requirements
    }


class TestPackagingMetadata:
    def test_runtime_dependencies_cover_import_time_packages(self):
        project = _pyproject()["project"]
        assert project["requires-python"] == ">=3.11"
        names = _requirement_names(project["dependencies"])
        assert {"pandas", "matplotlib", "numpy", "openpyxl"} <= names

    def test_optional_extras_are_declared(self):
        extras = _pyproject()["project"]["optional-dependencies"]
        assert {"dev", "geo", "network", "full"} <= set(extras)
        assert {"pytest", "pytest-cov", "build"} <= _requirement_names(extras["dev"])
        assert {"pyproj", "pyshp"} <= _requirement_names(extras["geo"])
        assert {"requests", "pillow", "xyzservices"} <= _requirement_names(
            extras["network"]
        )
        assert _requirement_names(extras["geo"]) | _requirement_names(
            extras["network"]
        ) <= _requirement_names(extras["full"])

    def test_all_subpackages_are_discovered(self):
        setuptools = _pyproject()["tool"]["setuptools"]
        assert list(setuptools["packages"]) == ["find"]
        assert setuptools["packages"]["find"]["where"] == ["src"]
        assert setuptools["packages"]["find"]["include"] == ["geofig_engine*"]

    def test_package_data_includes_presets_and_typing_marker(self):
        package_data = _pyproject()["tool"]["setuptools"]["package-data"][
            "geofig_engine"
        ]
        assert "py.typed" in package_data
        assert "data/geom_presets/*.json" in package_data
        assert (ROOT / "src" / "geofig_engine" / "py.typed").is_file()
        assert (
            ROOT
            / "src"
            / "geofig_engine"
            / "data"
            / "geom_presets"
            / "water_isotope.json"
        ).is_file()

    def test_constraints_pin_validated_runtime_versions(self):
        text = (ROOT / "constraints.txt").read_text(encoding="utf-8")
        for pinned in (
            "pandas==",
            "matplotlib==",
            "numpy==",
            "openpyxl==",
            "pytest==",
        ):
            assert pinned in text
