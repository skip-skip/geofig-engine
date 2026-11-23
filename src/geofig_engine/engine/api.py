"""
Declarative API: template registry + recipe shape + canonical ``render_template``
(Phase 15 — interoperability M1).

The exported ``TEMPLATES`` registry maps a template key to a builder callable
that returns either a duck-typed **template recipe** (``name`` / ``layers`` /
``coord`` / ``default_settings``) or a :class:`SpecRecipe` for composite
templates. Native builders own the legacy factory set; the ``FigureTemplate``
factories remain compatibility wrappers and are still adapted via
``recipe_from`` when passed directly.

``render_template`` is the **one canonical entry point**: it coerces raw
``pandas.DataFrame``/ndarray input into a ``DataProvider``, resolves the
template key or object to a recipe, merges ``mapping``/``coord``/``settings``
overrides on top of the recipe defaults, and hands layer recipes to a
``FigureGenerator`` (``15_wp3``) or spec recipes directly to the renderer
(``18.4``). It returns ``list[Figure]`` — the old ``(specs, figures,
legend_fig)`` tuple form lives in the legacy path (``render_template_legacy``,
``15_wp5``).

This module never imports ``geodata`` or ``geochemmodel``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from geofig_engine.core.coord import Coord, CoordCartesian
from geofig_engine.core.facet import Facet, FacetNull
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.core.layer import Layer
from geofig_engine.core.spec import FigureSpec
from geofig_engine.engine.entry import render_template_legacy
from geofig_engine.engine.generator import FigureGenerator
from geofig_engine.provider import DataProvider, DataFrameProvider
from geofig_engine.renderers.matplotlib.legend import LegendAccumulator
from geofig_engine.templates.anp_agp import anp_agp_builder
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.templates.bivariate import bivariate_builder
from geofig_engine.templates.boxplot_with_points import boxplot_with_points_builder
from geofig_engine.templates.dendrogram import dendrogram_builder
from geofig_engine.templates.histogram import histogram_builder
from geofig_engine.templates.isotope import isotope_builder
from geofig_engine.templates.nagph_nag import nagph_nag_builder
from geofig_engine.templates.npr_nnp import npr_nnp_builder
from geofig_engine.templates.particle_overlay import particle_overlay_builder
from geofig_engine.templates.pie import pie_builder
from geofig_engine.templates.piper import piper_builder
from geofig_engine.templates.radar import radar_builder
from geofig_engine.templates.site_map import site_map_builder
from geofig_engine.templates.stiff import stiff_builder
from geofig_engine.templates.timeseries import timeseries_builder


#: Stub channels native builders merge under a user mapping so registry keys
#: stay usable without one. Kept separate from ``legacy.py`` so adapter and
#: native paths can evolve independently.
DEFAULT_TEMPLATE_MAPPING: dict[str, str] = {"x": "x", "y": "y"}


@dataclass(frozen=True)
class TemplateRecipe:
    """Canonical template recipe shape returned by template builders.

    A recipe carries everything ``render_template`` needs to build specs:
    ``name`` (registry key), ``layers`` (Layer list), ``coord`` (the
    coordinate system), and ``default_settings`` (renderer defaults).
    ``mapping_consumed`` marks builders that already bound the user mapping
    into their layers/stats, so the generic override pass is skipped for them.
    Missing *required channels* are **not** validated here — that check
    happens lazily at spec-build time (see ``15_wp3`` / ``15_wp4``).
    """

    name: str
    layers: list[Layer]
    coord: Coord = field(default_factory=CoordCartesian)
    default_settings: dict[str, Any] = field(default_factory=dict)
    mapping_consumed: bool = False


@dataclass(frozen=True)
class SpecRecipe:
    """Recipe for composite templates that emit ``FigureSpec`` objects directly.

    Linked-axes builders (``piper`` / ``stiff``) cannot be flattened into layer
    recipes without moving data-derived spec math into the renderer. A
    ``SpecRecipe`` keeps the ``Data -> Spec -> Render`` boundary intact: the
    builder receives the coerced provider frame plus resolved overrides and
    returns the specs for the renderer.
    """

    name: str
    default_settings: dict[str, Any]
    build_specs: Callable[
        [
            pd.DataFrame,
            dict[str, Any] | None,
            dict[str, Any] | None,
            Coord | None,
        ],
        list[FigureSpec],
    ]


Recipe = TemplateRecipe | SpecRecipe


def _is_recipe(obj: Any) -> bool:
    """Duck-typed recipe check (``name``/``layers``/``coord``/``default_settings``)."""
    if isinstance(obj, dict):
        return {"name", "layers", "coord", "default_settings"} <= set(obj)
    return all(
        hasattr(obj, attr) for attr in ("name", "layers", "coord", "default_settings")
    )


def recipe_from(template_or_recipe: Any) -> Recipe:
    """Normalize a template builder result to a recipe.

    - ``TemplateRecipe`` and ``SpecRecipe`` instances pass through unchanged.
    - Any other duck-typed recipe (e.g. a plain dict exposing
      ``name``/``layers``/``coord``/``default_settings``) passes through
      unchanged.
    - ``FigureTemplate`` objects are adapted to a ``TemplateRecipe`` (their
      layers / coord / default settings / name are copied over).
    """
    if isinstance(template_or_recipe, (TemplateRecipe, SpecRecipe)):
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
        "Expected a TemplateRecipe, a SpecRecipe, a duck-typed recipe "
        "(name/layers/coord/default_settings), or a FigureTemplate; got "
        f"{type(template_or_recipe).__name__}"
    )


# Exported registry: template key → builder callable. Plain dict semantics;
# builders may accept mapping/settings overrides and return a recipe.
TEMPLATES: dict[str, Callable[..., Recipe]] = {}


def register_template(name: str, builder: Callable[..., Recipe]) -> None:
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


def get_template(name: str) -> Callable[..., Recipe]:
    """Return the builder registered under ``name``.

    Unknown keys raise ``KeyError`` with a helpful message listing the
    available keys.
    """
    if name not in TEMPLATES:
        available = ", ".join(sorted(TEMPLATES)) or "(none registered)"
        raise KeyError(f"Unknown template key: '{name}'. Available keys: {available}")
    return TEMPLATES[name]


# ---------------------------------------------------------------------------
# Seed the registry (18.4): native layer + spec builders
# ---------------------------------------------------------------------------

TEMPLATES["bivariate"] = bivariate_builder
TEMPLATES["boxplot_with_points"] = boxplot_with_points_builder
TEMPLATES["dendrogram"] = dendrogram_builder
TEMPLATES["particle_overlay"] = particle_overlay_builder
TEMPLATES["site_map"] = site_map_builder
TEMPLATES["histogram"] = histogram_builder
TEMPLATES["pie"] = pie_builder
TEMPLATES["radar"] = radar_builder
TEMPLATES["timeseries"] = timeseries_builder
TEMPLATES["isotope"] = isotope_builder
TEMPLATES["npr_nnp"] = npr_nnp_builder
TEMPLATES["anp_agp"] = anp_agp_builder
TEMPLATES["nagph_nag"] = nagph_nag_builder
TEMPLATES["piper"] = piper_builder
TEMPLATES["stiff"] = stiff_builder


# ---------------------------------------------------------------------------
# render_template — canonical entry point
# ---------------------------------------------------------------------------


def _wrap_data(data: pd.DataFrame | DataProvider | np.ndarray) -> DataProvider:
    """Coerce the ``data`` input into a ``DataProvider``.

    - ``DataProvider`` instances pass through unchanged.
    - ``pd.DataFrame`` is wrapped in a ``DataFrameProvider``.
    - ``np.ndarray`` is wrapped in a frame with **string positional columns**
      (``"0"``, ``"1"``, ...) so provider mappings can address them — e.g. the
      dendrogram linkage matrix input.
    """
    if isinstance(data, DataProvider):
        return data
    if isinstance(data, pd.DataFrame):
        return DataFrameProvider(data)
    if isinstance(data, np.ndarray):
        n_cols = data.shape[1] if data.ndim >= 2 else 1
        frame = pd.DataFrame(
            data if data.ndim >= 2 else data.reshape(-1, 1),
            columns=[str(i) for i in range(n_cols)],
        )
        return DataFrameProvider(frame)
    raise TypeError(
        "data must be a pandas.DataFrame, a DataProvider, or an ndarray; "
        f"got {type(data).__name__}"
    )


def _apply_mapping_override(
    layers: list[Layer],
    mapping: dict[str, Any] | None,
) -> list[Layer]:
    """Merge a user ``mapping`` over each recipe layer's mapping (per-layer).

    Only channels the layer already binds to a **data source** (a string
    reference) are remapped, so scalar-literal channels on annotation layers
    (e.g. the fixed zone text of the ARD ternary templates) are left intact —
    matching the legacy behaviour where the mapping is bound to the data
    layers only. Unmapped recipe channels are kept.
    """
    if not mapping:
        return layers
    overridden: list[Layer] = []
    for layer in layers:
        layer_mapping = dict(layer.mapping)
        for channel, source in mapping.items():
            if isinstance(layer_mapping.get(channel), str):
                layer_mapping[channel] = source
        overridden.append(replace(layer, mapping=layer_mapping))
    return overridden


def _mapping_consumed(recipe: Any) -> bool:
    """Whether a recipe bound the user mapping itself (native legacy builders)."""
    if isinstance(recipe, dict):
        return bool(recipe.get("mapping_consumed", False))
    return bool(getattr(recipe, "mapping_consumed", False))


def render_template(
    data: pd.DataFrame | DataProvider,
    template: str | FigureTemplate,
    mapping: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
    iterators: list[DimensionIterator] | None = None,
    facet: Facet | None = None,
    coord: Coord | None = None,
    savedir: str | Path | None = None,
    renderer_name: str = "matplotlib",
) -> list[Any]:
    """Render a template to a list of figures (canonical Phase 15 entry).

    Args:
        data: ``DataProvider`` (passed through), ``pd.DataFrame`` (wrapped in
            ``DataFrameProvider``), or an ndarray (wrapped in a frame with
            positional columns — e.g. dendrogram linkage matrices).
        template: Registry key (``str``) resolved via ``get_template`` and
            called with ``mapping``/``settings``, or a ``FigureTemplate`` /
            duck-typed recipe adapted via ``recipe_from``.
        mapping: Per-layer mapping override, merged over the recipe layers for
            templates that do not consume it themselves.
        settings: User settings merged on top of the recipe defaults (and
            passed to key builders as flat template-specific knobs).
        iterators: Optional dimension iterators for multi-figure expansion.
            Not supported by ``SpecRecipe`` templates (``piper`` / ``stiff``).
        facet: Optional facet spec; splits the data into panels within a
            single figure (renderer-side). One figure per iterator
            combination, each containing the full facet panel grid. Not
            supported by ``SpecRecipe`` templates.
        coord: Overrides the recipe coord when given.
        savedir: If provided, each figure is persisted as a PNG using the
            legacy naming convention (zero-padded index + iterator key parts),
            plus a ``legend.png``.
        renderer_name: Backend name; only ``"matplotlib"`` is supported.

    Returns:
        ``list[Figure]`` — the rendered backend figures. ``specs`` and the
        legend figure are **not** returned here; they live in the legacy path
        (``render_template_legacy``, ``15_wp5``).

    Raises:
        KeyError: Unknown template key (message lists the available keys).
        TypeError: Unsupported ``data`` or ``template`` type.
        ValueError: Unsupported ``renderer_name``, unsupported ``iterators`` /
            ``facet`` with a ``SpecRecipe``, or missing required channels at
            spec-build time (informative message, not a traceback into
            generator internals).
    """
    # 1. Coerce data → provider
    provider = _wrap_data(data)

    # 2. Resolve template → recipe (registry key or FigureTemplate/recipe)
    if isinstance(template, str):
        recipe = recipe_from(get_template(template)(mapping=mapping, settings=settings))
    else:
        recipe = recipe_from(template)

    # 3. Merge user overrides with recipe defaults. Native builders already
    #    bound the mapping into their stats/layers, so skip the generic pass.
    merged_settings = {**recipe.default_settings, **(settings or {})}
    final_coord = coord if coord is not None else getattr(recipe, "coord", None)

    generator: FigureGenerator | None = None
    if isinstance(recipe, SpecRecipe):
        if iterators or facet is not None:
            raise ValueError(
                f"Unsupported combination: 'iterators' and 'facet' are not "
                f"supported for spec recipe '{recipe.name}' in v0.4.0"
            )
        frame_pairs = provider.expand(None)
        if len(frame_pairs) != 1:
            raise ValueError(
                f"Spec recipe '{recipe.name}' requires exactly one provider "
                f"frame; got {len(frame_pairs)}"
            )
        frame = frame_pairs[0][0]
        specs = list(recipe.build_specs(frame, mapping, merged_settings, final_coord))
    else:
        effective_mapping = None if _mapping_consumed(recipe) else mapping
        layers = _apply_mapping_override(recipe.layers, effective_mapping)
        if isinstance(iterators, DimensionIterator):
            iterators = [iterators]

        # 4. Compose the provider-driven generator
        generator = FigureGenerator(
            provider=provider,
            layers=layers,
            coord=final_coord,
            facet=facet if facet is not None else FacetNull(),
            settings=merged_settings,
            iterators=iterators,
        )

    # 5. Renderer gating
    from geofig_engine.renderers import MatplotlibRenderer

    if renderer_name != "matplotlib":
        raise ValueError(
            f"Unsupported renderer: '{renderer_name}'. Only 'matplotlib' is available."
        )
    renderer = MatplotlibRenderer()

    # 6. Build + render — missing required channels raise the informative
    #    spec-build error here (lazy default resolution, no eager validation)
    if generator is not None:
        specs = generator.build_specs()
    figures = list(renderer.render_all(specs))

    # 7. Legend figure (replicates the legacy entry path)
    accumulator = LegendAccumulator()
    for spec in specs:
        accumulator.add_from_spec(spec)
    legend_fig = renderer.render_legend(accumulator)

    # 8. Optional persistence — legacy naming + legend.png
    if savedir is not None:
        save_dir = Path(savedir)
        save_dir.mkdir(parents=True, exist_ok=True)
        for idx, (spec, fig) in enumerate(zip(specs, figures), start=1):
            parts = [str(idx).zfill(3)]
            for key in spec.iterator_key:
                val = spec.context.get(key, "unknown")
                parts.append(str(val))
            filename = "_".join(parts) + ".png"
            fig.savefig(str(save_dir / filename))
            fig.clf()
        legend_fig.savefig(str(save_dir / "legend.png"))
        legend_fig.clf()

    return figures