"""
Deprecation shims for legacy geofig_engine symbols (Phase 15 interop M1).

The former root-level names (``Dataset``, ``Dimension``, ``DimensionSelector``,
``ColumnSelector``, ``IteratorEngine``, ``FigureEngine``) are re-exported
through this module as **deprecated** aliases. Accessing any of them emits an
import-time ``DeprecationWarning`` pointing at the recommended replacement from
the ARCHITECTURE.md §1a shim table — **once per symbol per process**. They are
removed no earlier than the next major version (>= 1.0.0).

Warnings are lazy (PEP 562 ``__getattr__``): merely importing this module (or
the ``geofig_engine`` package) stays silent; the warning fires only when a
legacy *name* is actually accessed. The package root routes deprecated-name
lookups here, so ``from geofig_engine import Dataset`` warns while
``from geofig_engine import render_template`` does not.

The shim values are referenced through submodule handles (never imported under
their deprecated names) so the names stay out of this module's namespace and
every access goes through ``__getattr__`` — guaranteeing the warning fires.
"""

from __future__ import annotations

import warnings
from typing import Any

from geofig_engine.core import dataset, dimension, dimension_selector, iterator
from geofig_engine.engine import generator

#: name -> (value, recommended replacement) per ARCHITECTURE.md §1a shim table.
#: Values come from submodule handles so the legacy names are not module
#: attributes here; only ``__getattr__`` resolves them (with the warning).
_SHIM_TABLE: dict[str, tuple[Any, str]] = {
    "Dataset": (
        dataset.Dataset,
        "DataFrameProvider(df) / GeoData.provider_for(data_ref) / DatasetProvider",
    ),
    "Dimension": (
        dimension.Dimension,
        "geodata.core.dimension.Dimension (metadata only)",
    ),
    "DimensionSelector": (
        dimension_selector.DimensionSelector,
        "plain column names + provider.resolve(selector)",
    ),
    "ColumnSelector": (
        dimension_selector.ColumnSelector,
        "plain column names + provider.resolve(selector)",
    ),
    # IteratorEngine never existed as a class in this lineage; the historical
    # expansion surface is the module-level ``expand()`` helper, aliased here.
    "IteratorEngine": (
        iterator.expand,
        "provider.expand(iterators)",
    ),
    "FigureEngine": (
        generator.FigureEngine,
        "FigureGenerator + render_template",
    ),
}

__all__ = list(_SHIM_TABLE)

_warned: set[str] = set()


def __getattr__(name: str) -> Any:
    """Resolve a deprecated legacy name, warning once per symbol per process."""
    entry = _SHIM_TABLE.get(name)
    if entry is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value, replacement = entry
    if name not in _warned:
        warnings.warn(
            f"geofig_engine.{name} is deprecated; use {replacement} instead. "
            "It will be removed in geofig-engine >= 1.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        _warned.add(name)
    return value