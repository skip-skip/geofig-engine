"""
Pipeline registry builder for the ``boxplot_with_points`` key (15_wp6).

Thin wrapper over the legacy ``boxplot_with_points`` factory: it composes a
``GeomBox`` layer (dodged boxes, optional fliers/means/``show_n``) with an
overlaid jittered ``GeomPoint`` layer sharing the same x/y/color mapping, and
normalizes the factory's ``FigureTemplate`` to the canonical recipe shape.
Usable with no mapping beside ``data``/``template`` (defaults ``x``/``y``).
"""

from __future__ import annotations

from typing import Any

from geofig_engine.templates.boxplot import boxplot_with_points


def boxplot_with_points_builder(
    mapping: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
    **kwargs: Any,
) -> "TemplateRecipe":
    """Pipeline registry builder for ``boxplot_with_points``.

    Forwards ``mapping`` and factory kwargs (``box_width``, ``jitter_width``,
    ``point_size``, ``point_alpha``, ``sort_mode``, ``smush``, ``showfliers``,
    ``showmeans``, ``show_n``, ``min_box_n``) to the legacy factory and adapts
    its ``FigureTemplate`` to a recipe via ``recipe_from``. User ``settings``
    merge on top of the recipe defaults.

    The ``engine.api`` imports are deferred to call time so this template
    module never depends on ``engine.api`` at import time.
    """
    from dataclasses import replace

    from geofig_engine.engine.api import TemplateRecipe, recipe_from

    template = boxplot_with_points(
        mapping=mapping or {"x": "x", "y": "y"},
        **kwargs,
    )
    recipe = recipe_from(template)
    if settings:
        recipe = replace(
            recipe,
            default_settings={**recipe.default_settings, **settings},
        )
    return recipe