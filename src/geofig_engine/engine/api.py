"""
Declarative API: template registry + recipe shape (Phase 15 — interoperability M1).

The exported ``TEMPLATES`` registry maps a template key to a builder callable
that returns a duck-typed **template recipe** (``name`` / ``layers`` / ``coord``
/ ``default_settings``). ``FigureTemplate`` objects from the legacy template
set are adapted to the same shape via ``recipe_from`` so the whole legacy set
stays usable through the registry. This module never imports ``geodata`` or
``geochemmodel``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from geofig_engine.core.coord import Coord, CoordCartesian
from geofig_engine.core.layer import Layer
from geofig_engine.templates.base import FigureTemplate


@dataclass(frozen=True)
class TemplateRecipe:
    """Canonical template recipe shape returned by template builders.

    A recipe carries everything ``render_template`` needs to build specs:
    ``name`` (registry key), ``layers`` (Layer list), ``coord`` (the
    coordinate system), and ``default_settings`` (renderer defaults).
    Missing *required channels* are **not** validated here — that check
    happens lazily at spec-build time (see ``15_wp3`` / ``15_wp4``).
    """

    name: str
    layers: list[Layer]
    coord: Coord = field(default_factory=CoordCartesian)
    default_settings: dict[str, Any] = field(default_factory=dict)


def _is_recipe(obj: Any) -> bool:
    """Duck-typed recipe check (``name``/``layers``/``coord``/``default_settings``)."""
    if isinstance(obj, dict):
        return {"name", "layers", "coord", "default_settings"} <= set(obj)
    return all(
        hasattr(obj, attr) for attr in ("name", "layers", "coord", "default_settings")
    )


def recipe_from(template_or_recipe: Any) -> TemplateRecipe:
    """Normalize a template builder result to a recipe.

    - ``TemplateRecipe`` instances pass through unchanged.
    - Any other duck-typed recipe (e.g. a plain dict exposing
      ``name``/``layers``/``coord``/``default_settings``) passes through
      unchanged.
    - ``FigureTemplate`` objects are adapted to a ``TemplateRecipe`` (their
      layers / coord / default settings / name are copied over).
    """
    if isinstance(template_or_recipe, TemplateRecipe):
        return template_or_recipe
    if isinstance(template_or_recipe, FigureTemplate):
        return TemplateRecipe(
            name=template_or_recipe.name,
            layers=list(template_or_recipe.layers),
            coord=template_or_recipe.coord,
            default_settings=dict(template_or_recipe.default_settings),
        )
    if _is_recipe(template_or_recipe):
        return template_or_recipe
    raise TypeError(
        "Expected a TemplateRecipe, a duck-typed recipe (name/layers/coord/"
        f"default_settings), or a FigureTemplate; got {type(template_or_recipe).__name__}"
    )


# Exported registry: template key → builder callable. Plain dict semantics;
# builders may accept mapping/settings overrides and return a recipe.
TEMPLATES: dict[str, Callable[..., TemplateRecipe]] = {}


def register_template(name: str, builder: Callable[..., TemplateRecipe]) -> None:
    """Register (or override) a template builder under ``name``.

    ``name`` must be a string and ``builder`` must be callable; anything else
    raises ``ValueError``. Overriding an existing key is allowed so downstream
    adapters (e.g. ``geochemmodel`` workflows) can register or replace keys
    without engine changes.
    """
    if not isinstance(name, str):
        raise ValueError(f"template name must be a string, got {type(name).__name__}")
    if not callable(builder):
        raise ValueError(
            f"template builder for '{name}' must be callable, "
            f"got {type(builder).__name__}"
        )
    TEMPLATES[name] = builder


def get_template(name: str) -> Callable[..., TemplateRecipe]:
    """Return the builder registered under ``name``.

    Unknown keys raise ``KeyError`` with a helpful message listing the
    available keys.
    """
    if name not in TEMPLATES:
        available = ", ".join(sorted(TEMPLATES)) or "(none registered)"
        raise KeyError(f"Unknown template key: '{name}'. Available keys: {available}")
    return TEMPLATES[name]