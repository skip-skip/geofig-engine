"""
Thin adapters re-registering the legacy template factories (15_wp6).

``legacy_adapter(builder)`` wraps a legacy ``FigureTemplate`` factory and
returns a registry builder ``(mapping=None, settings=None, **kwargs)`` whose
product is normalized to the canonical recipe shape via ``recipe_from``. The
adapters keep the whole legacy factory set usable through the same
``TEMPLATES`` registry and ``render_template``.

The legacy ``FigureTemplate`` factories are all data-free builders:
``histogram``, ``pie``, ``radar``, ``timeseries``, ``isotope``, ``npr_nnp``,
``anp_agp``, ``nagph_nag``.

``piper`` (``build_piper_specs``) and ``stiff`` (``plot_stiff``) are
**spec builders** — they require ``data``/scalar arguments and return
``FigureSpec`` objects (child-spec/ternary/linked-axes figures that the
layer->recipe pipeline cannot express). Their registry keys still resolve
through ``get_template``, but invoking them through ``render_template``
raises an explicit, informative ``TypeError`` pointing at the spec-builder
route (``MatplotlibRenderer`` on the builder's specs).
"""

from __future__ import annotations

import functools
from typing import Any, Callable

from geofig_engine.templates.anp_agp import anp_agp
from geofig_engine.templates.histogram import histogram
from geofig_engine.templates.isotope import isotope
from geofig_engine.templates.nagph_nag import nagph_nag
from geofig_engine.templates.npr_nnp import npr_nnp
from geofig_engine.templates.pie import pie
from geofig_engine.templates.piper import build_piper_specs
from geofig_engine.templates.radar import radar
from geofig_engine.templates.stiff import plot_stiff
from geofig_engine.templates.timeseries import timeseries

#: Stub channels handed to the legacy factories whose constructors validate
#: required mapping keys (histogram/pie/radar) or whose point layers would
#: otherwise be built mapping-less. ``render_template`` merges the user's
#: ``mapping`` over these per layer afterwards, so the stubs are only ever
#: observed when the user supplies no mapping at all (matching the
#: ``bivariate`` recipe-default behaviour).
LEGACY_DEFAULT_MAPPING: dict[str, str] = {"x": "x", "y": "y"}

#: Legacy factory set keyed by the registry name they are seeded under.
LEGACY_FACTORIES: dict[str, Callable[..., Any]] = {
    "histogram": histogram,
    "pie": pie,
    "radar": radar,
    "timeseries": timeseries,
    "isotope": isotope,
    "npr_nnp": npr_nnp,
    "anp_agp": anp_agp,
    "nagph_nag": nagph_nag,
    # Spec builders: keys resolve; the recipe pipeline cannot render them.
    "piper": build_piper_specs,
    "stiff": plot_stiff,
}


def legacy_adapter(builder: Callable[..., Any]) -> Callable[..., Any]:
    """Adapt a legacy template factory to a registry builder.

    The returned builder accepts ``mapping``/``settings``/factory kwargs,
    calls the legacy factory, and normalizes the result to a recipe via
    ``recipe_from`` (imported lazily to keep ``templates`` decoupled from
    ``engine.api``). Spec-builder products (``FigureSpec``/lists) raise an
    informative ``TypeError``.
    """

    @functools.wraps(builder)
    def adapter(
        mapping: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        try:
            product = builder(
                mapping=mapping or dict(LEGACY_DEFAULT_MAPPING),
                **kwargs,
            )
        except TypeError as exc:
            raise TypeError(
                f"legacy template factory '{builder.__name__}' is not "
                f"registry-adaptable: it requires data/scalar arguments ({exc}). "
                "Call the factory with data directly and render the specs via "
                "MatplotlibRenderer."
            ) from exc
        from geofig_engine.core.spec import FigureSpec

        if isinstance(product, (FigureSpec, list, tuple)):
            raise TypeError(
                f"legacy template factory '{builder.__name__}' is not "
                "registry-adaptable: it returns FigureSpec object(s), not a "
                "FigureTemplate/recipe, so it cannot be registered as a "
                "mapping-free recipe. Call the factory with data directly and "
                "render the specs via MatplotlibRenderer."
            )
        from geofig_engine.engine.api import recipe_from

        recipe = recipe_from(product)
        if settings:
            from dataclasses import replace

            recipe = replace(
                recipe,
                default_settings={**recipe.default_settings, **settings},
            )
        return recipe

    return adapter