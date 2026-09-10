"""
Phase 15 wp5 — legacy path + deprecation shims.

Covers:
- ``render_template_legacy`` (engine/entry.py): importable without warning,
  tuple return, call-time ``DeprecationWarning``.
- ``deprecated.py`` shims (Dataset, Dimension, DimensionSelector,
  ColumnSelector, IteratorEngine, FigureEngine): import-time warning, once per
  symbol per process, bound to the real legacy symbols.
- Package-root ``__all__`` split: public names warning-free, deprecated names
  warning-carrying, ``__deprecated__`` lists the legacy surface.
- ``geofig_cli`` still wireable (curses-free registry smoke; no warnings).
"""

from __future__ import annotations

import warnings

import pandas as pd
import pytest

import geofig_engine
import geofig_engine.deprecated as _deprecated
from geofig_engine.templates import bivariate


def make_df():
    return pd.DataFrame({
        "id": [1, 2, 3, 4],
        "x": [1.0, 2.0, 3.0, 4.0],
        "y": [2.0, 3.0, 5.0, 7.0],
        "group": ["A", "A", "B", "B"],
    })


DEPRECATED_SHIMS = [
    "Dataset",
    "Dimension",
    "DimensionSelector",
    "ColumnSelector",
    "IteratorEngine",
    "FigureEngine",
]

PUBLIC_NAMES = [
    "render_template",
    "register_template",
    "get_template",
    "TEMPLATES",
    "DataProvider",
    "DataFrameProvider",
    "DatasetProvider",
    "FigureGenerator",
    "FigureSpec",
    "MatplotlibRenderer",
]


class TestRenderTemplateLegacy:
    """Old tuple-form entry: importable silently, warns at call time."""

    def test_import_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            from geofig_engine import render_template_legacy

            assert callable(render_template_legacy)

    def test_call_returns_tuple_and_warns(self):
        from geofig_engine.core.dataset import Dataset

        dataset = Dataset(dataframe=make_df(), key_column="id")
        template = bivariate(mapping={"x": "x", "y": "y"})

        with pytest.warns(DeprecationWarning, match="render_template_legacy"):
            specs, figures, legend_fig = geofig_engine.render_template_legacy(
                dataset=dataset,
                template=template,
            )

        import matplotlib.figure

        assert isinstance(specs, list) and len(specs) == 1
        assert isinstance(figures, list) and len(figures) == 1
        assert isinstance(figures[0], matplotlib.figure.Figure)
        assert isinstance(legend_fig, matplotlib.figure.Figure)


class TestDeprecatedShims:
    """Import-time DeprecationWarning, once per symbol per process."""

    @pytest.mark.parametrize("name", DEPRECATED_SHIMS)
    def test_access_warns_once_per_symbol(self, name):
        _deprecated._warned.clear()  # deterministic start within the process

        with pytest.warns(DeprecationWarning, match=name):
            first = getattr(geofig_engine, name)

        # Second access in the same process must be silent (one warning per
        # symbol per process) — escalated filter would raise if it warned.
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            second = getattr(geofig_engine, name)

        assert first is second

    def test_shims_point_at_legacy_symbols(self):
        from geofig_engine.core import dataset as core_dataset
        from geofig_engine.core import dimension as core_dimension
        from geofig_engine.core import dimension_selector as core_ds
        from geofig_engine.core.iterator import expand as legacy_expand
        from geofig_engine.engine.generator import FigureEngine

        _deprecated._warned.clear()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert geofig_engine.Dataset is core_dataset.Dataset
            assert geofig_engine.Dimension is core_dimension.Dimension
            assert geofig_engine.DimensionSelector is core_ds.DimensionSelector
            assert geofig_engine.ColumnSelector is core_ds.ColumnSelector
            assert geofig_engine.IteratorEngine is legacy_expand
            assert geofig_engine.FigureEngine is FigureEngine

    def test_unknown_attribute_raises_attribute_error(self):
        with pytest.raises(AttributeError):
            geofig_engine.does_not_exist  # noqa: B018


class TestPublicSurface:
    """Public names stay warning-free at the package root."""

    def test_public_names_do_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            for name in PUBLIC_NAMES:
                assert getattr(geofig_engine, name) is not None


class TestAllSplit:
    """Public + deprecated ``__all__`` split with ``__deprecated__`` marker."""

    def test_all_splits_public_from_deprecated(self):
        expected_public = set(PUBLIC_NAMES)
        expected_deprecated = set(DEPRECATED_SHIMS) | {"render_template_legacy"}

        assert set(geofig_engine.__all__) == expected_public | expected_deprecated
        assert set(geofig_engine.__deprecated__) == expected_deprecated

    def test_star_import_binds_public_and_deprecated(self):
        _deprecated._warned.clear()
        namespace = {}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            exec("from geofig_engine import *", namespace)  # noqa: S102

        assert "render_template" in namespace
        assert "Dataset" in namespace
        assert namespace["Dataset"] is geofig_engine.core.dataset.Dataset


class TestGeofigCliSmoke:
    """geofig_cli stays wireable and warning-free (untouched by the shims)."""

    def test_cli_registry_imports_without_warnings(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            from geofig_cli.registry import TEMPLATE_REGISTRY

        assert "bivariate" in TEMPLATE_REGISTRY
        assert "timeseries" in TEMPLATE_REGISTRY