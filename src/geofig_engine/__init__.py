"""
geofig_engine

A modular plotting engine for structured, multi-dimensional data visualization.

Phase 15 interop M1 exposes the provider-driven declarative surface from the
package root: ``build_template_specs`` (returns ``list[FigureSpec]`` without
rendering), ``render_template`` (returns ``list[Figure]``), the ``TEMPLATES``
registry (``register_template`` / ``get_template``), the provider protocol
(``DataProvider`` / ``DataFrameProvider`` / ``DatasetProvider``), and
``FigureGenerator`` / ``FigureSpec``. The dashboard snapshot helpers
(``specs_to_dashboard_dict`` / ``specs_to_dashboard_json``) and patch helpers
(``diff_dashboard_payload`` / ``apply_dashboard_patch`` /
``validate_dashboard_patch``) are also importable from the root for
browser-safe display payloads.

Legacy names (``Dataset``, ``Dimension``, ``DimensionSelector``,
``ColumnSelector``, ``IteratorEngine``, ``FigureEngine``) resolve lazily
through ``deprecated.py`` with an import-time ``DeprecationWarning`` (once per
symbol per process) and are removed no earlier than geofig-engine >= 1.0.0.
``render_template_legacy`` (the old tuple-form entry) is importable without a
warning; it warns at call time.
"""

# Public API (Phase 15): provider-driven, no upstream imports
from .engine.api import (
    TEMPLATES,
    build_template_specs,
    get_template,
    register_template,
    render_template,
    render_template_legacy,
)
from .engine.generator import FigureGenerator
from .provider import DataProvider, DataFrameProvider, DatasetProvider
from .core.spec import FigureSpec
from .renderers import MatplotlibRenderer
from .serialize.dashboard import specs_to_dashboard_dict, specs_to_dashboard_json
from .serialize.dashboard_patch import (
    apply_dashboard_patch,
    diff_dashboard_payload,
    validate_dashboard_patch,
)

# Deprecated legacy re-exports (import-time DeprecationWarning via __getattr__)
from . import deprecated as _deprecated

__all__ = [
    # Public
    "build_template_specs",
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
    # Deprecated (resolve with an import-time DeprecationWarning)
    "Dataset",
    "Dimension",
    "DimensionSelector",
    "ColumnSelector",
    "IteratorEngine",
    "FigureEngine",
    "render_template_legacy",
]

#: Deprecated legacy names. Kept separate from the public ``__all__`` section
#: above so consumers can programmatically distinguish the deprecated surface.
__deprecated__ = [
    "Dataset",
    "Dimension",
    "DimensionSelector",
    "ColumnSelector",
    "IteratorEngine",
    "FigureEngine",
    "render_template_legacy",
]


def __getattr__(name: str):
    """Resolve deprecated legacy names lazily (import-time DeprecationWarning).

    ``render_template_legacy`` is bound eagerly above, so this fires only for
    the six ``deprecated.py`` shims — and only on actual access, keeping
    ``from geofig_engine import render_template`` warning-free.
    """
    if name in __deprecated__:
        return getattr(_deprecated, name)
    raise AttributeError(f"module 'geofig_engine' has no attribute {name!r}")