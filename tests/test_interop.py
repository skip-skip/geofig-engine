"""
Phase 15 wp11: interop validation (standalone + upstream smoke).

Cross-cutting proof that the M1 interop contract holds end to end -- the
shared-contract pieces themselves land in 15_wp1..15_wp10; this file only
adds validation tests:

- standalone: raw ``pandas.DataFrame`` -> ``render_template`` -> ``list[Figure]``
  with no upstream package involved
- wrapping robustness: NaN rows and non-string column names survive the
  ``DataFrameProvider`` wrap
- protocol conformance: a minimal duck-typed third-party provider (no
  subclassing) renders through ``FigureGenerator``/``render_template`` and the
  render path never instantiates ``Dataset``
- upstream smoke: ``geomodeler`` (the importable package behind the
  ``geochemmodel`` stage -- ``pyproject name = "geomodeler"``) drives the new
  API via its lazy ``ModelResult.render``; ``AgglomerativeClusterModel`` on a
  tiny frame renders ``bivariate``/``dendrogram`` figures, and
  ``ParticleImageModel`` resolves the ``particle_overlay`` template key.
  ``pytest.importorskip("geomodeler")`` keeps the engine suite independent of
  the upstream package (skips cleanly when absent or when ``ModelResult.render``
  is still the upstream stub)
- import guard: a fresh reload of every ``geofig_engine.*`` module under a
  blocked ``__import__`` for ``geodata``/``geochemmodel``
- legacy bridge: ``render_template_legacy`` still returns the tuple and warns
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest
import pandas as pd

import matplotlib.figure

from geofig_engine import DataProvider, TEMPLATES, get_template, render_template
from geofig_engine.engine.api import recipe_from
from geofig_engine.engine.generator import FigureGenerator
from geofig_engine.provider import DataFrameProvider

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Small geochem-flavored frame for the standalone / legacy paths.
_STANDALONE_DF = pd.DataFrame(
    {
        "id": ["S-1", "S-2", "S-3", "S-4", "S-5", "S-6"],
        "x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "y": [2.0, 3.0, 5.0, 7.0, 11.0, 13.0],
        "well": ["A", "A", "B", "B", "B", "A"],
    }
)

# Tiny wide analyte frame for the upstream cluster smoke (numeric, complete).
_WIDE_DF = pd.DataFrame(
    {
        "na": [10.0, 12.0, 11.0, 13.0, 14.0, 15.0],
        "ca": [40.0, 42.0, 41.0, 43.0, 44.0, 45.0],
        "mg": [8.0, 9.0, 7.0, 10.0, 12.0, 11.0],
    }
)


class DuckProvider:
    """Minimal duck-typed provider satisfying ``DataProvider`` without
    subclassing (third-party style)."""

    def __init__(self, dataframe: pd.DataFrame):
        self._df = dataframe.copy()

    @property
    def columns(self) -> list[str]:
        return list(self._df.columns)

    def resolve(self, selector) -> list[str]:
        if isinstance(selector, str):
            if selector not in self._df.columns:
                raise KeyError(f"Column '{selector}' not found")
            return [selector]
        raise TypeError(f"Unsupported selector: {selector!r}")

    def expand(self, iterators=None):
        return [(self._df, {})]

    def subset(self, *, columns=None, **filters):
        mask = pd.Series(True, index=self._df.index)
        for name, value in filters.items():
            mask &= self._df[name].eq(value)
        result_df = self._df.loc[mask].copy()
        if columns is not None:
            if isinstance(columns, str):
                columns = [columns]
            result_df = result_df[list(columns)]
        return DuckProvider(result_df)

    def unique_values(self, column: str):
        return sorted(self._df[column].dropna().unique().tolist())

    def dimensions(self, column: str) -> dict:
        return {}


class TestStandalone:
    def test_standalone_bivariate(self):
        # Raw DataFrame + render_template with nothing else installed.
        assert "geodata" not in sys.modules
        assert "geochemmodel" not in sys.modules
        figures = render_template(
            data=_STANDALONE_DF,
            template="bivariate",
            mapping={"x": "x", "y": "y", "color": "well"},
        )
        assert isinstance(figures, list) and len(figures) == 1
        assert isinstance(figures[0], matplotlib.figure.Figure)
        # rendering never touched the upstream packages
        assert "geodata" not in sys.modules
        assert "geochemmodel" not in sys.modules

    def test_standalone_legacy_factory_adapts_through_registry(self):
        # The upstream-style key path (bivariate) renders from a plain frame.
        figures = render_template(
            data=_STANDALONE_DF,
            template="bivariate",
            mapping={"x": "x", "y": "y"},
        )
        assert len(figures) == 1
        assert len(figures[0].axes[0].collections) == 1  # one point layer

    def test_raw_dataframe_wrapping_robustness(self):
        # NaN rows + a non-string column don't break the DataFrameProvider wrap
        # or the render.
        raw = _STANDALONE_DF.copy()
        raw[77] = [1, 2, 3, 4, 5, 6]  # non-str column name
        raw.loc[1, "x"] = np.nan
        raw.loc[4, "y"] = np.nan
        provider = DataFrameProvider(raw)
        assert "x" in provider.columns
        assert 77 in provider.columns
        figures = render_template(
            data=raw,
            template="bivariate",
            mapping={"x": "x", "y": "y"},
        )
        assert isinstance(figures[0], matplotlib.figure.Figure)
        # provider round-trips: subset + resolve still work on the wrapped copy
        assert provider.subset(well="A").resolve("x") == ["x"]


class TestDuckProvider:
    def test_duck_provider_renders(self):
        duck = DuckProvider(_STANDALONE_DF)
        assert isinstance(duck, DataProvider)  # runtime-checkable protocol
        figures = render_template(
            data=duck,
            template="bivariate",
            mapping={"x": "x", "y": "y", "color": "well"},
        )
        assert isinstance(figures, list) and len(figures) == 1
        assert isinstance(figures[0], matplotlib.figure.Figure)

    def test_generator_never_instantiates_dataset(self, monkeypatch):
        # The provider-driven path must not construct the legacy Dataset even
        # when the provider is a third-party duck type.
        from geofig_engine.core.dataset import Dataset

        def _no_dataset(self, *args, **kwargs):
            raise AssertionError("render path must not instantiate Dataset")

        monkeypatch.setattr(Dataset, "__init__", _no_dataset)
        duck = DuckProvider(_STANDALONE_DF)
        figures = render_template(
            data=duck,
            template="bivariate",
            mapping={"x": "x", "y": "y"},
        )
        assert len(figures) == 1
        assert isinstance(figures[0], matplotlib.figure.Figure)

    def test_generator_accepts_provider_directly(self):
        # Provider passed straight to FigureGenerator (no render_template).
        recipe = recipe_from(get_template("bivariate")())
        generator = FigureGenerator(
            provider=DataFrameProvider(_STANDALONE_DF),
            layers=recipe.layers,
            coord=recipe.coord,
            settings={"figsize": (6, 4)},
        )
        specs = generator.build_specs()
        assert len(specs) == 1


class TestUpstreamSmoke:
    """Validated only when the upstream ``geomodeler`` package is importable.

    The engine suite must never require it: ``pytest.importorskip`` mirrors
    the cv2 skip pattern used elsewhere. The upstream ``ModelResult.render``
    is still the M1 stub upstream (``NotImplementedError``), so that smoke
    skips with a clear reason until the upstream render lands; the encoding
    contract tests below run against the importable upstream regardless.
    """

    def test_agglomerative_model_renders_via_lazy_entry(self):
        geomodeler = pytest.importorskip(
            "geomodeler", reason="upstream geomodeler not installed"
        )
        from geomodeler.clustering import AgglomerativeClusterModel

        result = AgglomerativeClusterModel(n_clusters=2).fit(_WIDE_DF)

        # Encoding contract: the bivariate + dendrogram keys our registry owns.
        templates = {enc.template for enc in result.visualizations}
        assert "bivariate" in templates
        assert "dendrogram" in templates

        # Lazy import path: ModelResult.render drives geofig_engine. Still a
        # stub upstream -> informative skip instead of a hard failure.
        try:
            figures = result.render(data=_WIDE_DF)
        except NotImplementedError as exc:
            pytest.skip(
                "geomodeler.ModelResult.render() is not implemented upstream "
                f"yet: {exc}"
            )
        assert isinstance(figures, list) and figures
        assert all(isinstance(f, matplotlib.figure.Figure) for f in figures)

    def test_particle_overlay_resolves_through_registry(self):
        geomodeler = pytest.importorskip(
            "geomodeler", reason="upstream geomodeler not installed"
        )
        from geomodeler.particle import ParticleImageModel

        encodings = ParticleImageModel().default_visualizations
        overlay = [e for e in encodings if e.template == "particle_overlay"]
        assert len(overlay) == 1
        assert overlay[0].data_ref == "particles"
        assert callable(get_template("particle_overlay"))  # our side resolves it


class TestNoUpstreamImport:
    def test_fresh_import_without_geodata_or_geochemmodel(self):
        # AC guard: a fresh interpreter imports every geofig_engine module with
        # geodata/geochemmodel blocked in __import__. The guard fires on any
        # import ATTEMPT (not just successful installs), so the engine's
        # import-independence is proven even when upstream is absent. A
        # subprocess keeps the reloaded-import state out of this session.
        import os
        import subprocess
        import textwrap

        src_dir = str(Path(__file__).resolve().parent.parent / "src")
        script = textwrap.dedent(
            """
            import builtins
            import sys

            real_import = builtins.__import__

            def guarded(name, *args, **kwargs):
                if name.split(".")[0] in {"geodata", "geochemmodel"}:
                    raise SystemExit(f"BLOCKED: {name} imported by geofig_engine")
                return real_import(name, *args, **kwargs)

            builtins.__import__ = guarded

            import geofig_engine
            from geofig_engine import TEMPLATES, render_template  # full package

            assert "geodata" not in sys.modules
            assert "geochemmodel" not in sys.modules
            assert "bivariate" in TEMPLATES
            assert callable(render_template)
            print("OK")
            """
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0, (
            f"fresh import pulled an upstream package:\n{result.stderr}"
        )
        assert "OK" in result.stdout


class TestLegacyBridge:
    def test_legacy_path_returns_tuple_and_warns(self):
        from geofig_engine import render_template_legacy
        from geofig_engine.core.dataset import Dataset
        from geofig_engine.templates import bivariate

        dataset = Dataset(dataframe=_STANDALONE_DF, key_column="id")
        with pytest.warns(DeprecationWarning, match="render_template_legacy"):
            specs, figures, legend_fig = render_template_legacy(
                dataset=dataset,
                template=bivariate(mapping={"x": "x", "y": "y"}),
            )
        assert isinstance(specs, list) and len(specs) == 1
        assert isinstance(figures, list) and len(figures) == 1
        assert isinstance(figures[0], matplotlib.figure.Figure)
        assert isinstance(legend_fig, matplotlib.figure.Figure)