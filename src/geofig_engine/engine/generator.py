"""
Engine orchestration for FigEngine.

This module builds renderer-ready FigureSpec objects from Dataset,
template, and mapping inputs, and optionally dispatches them to a renderer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Sequence

import pandas as pd

from geofig_engine.core.attribute_mapping import SourceType, resolve_source
from geofig_engine.core.coord import Coord, CoordCartesian
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.facet import Facet, FacetNull
from geofig_engine.core.geom import GeomFunctionLine
from geofig_engine.core.iterator import DimensionIterator, IteratorResult, expand
from geofig_engine.core.layer import Layer, LayerSpec
from geofig_engine.core.link import LinkTransform
from geofig_engine.core.scale import Scale
from geofig_engine.core.spec import FigureSpec, build_spec
from geofig_engine.provider import DataProvider
from geofig_engine.renderers.base import BaseRenderer
from geofig_engine.renderers.matplotlib.legend import LegendAccumulator
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.validation import validate_dict
from geofig_engine.utils.typing import Mapping


def _normalize_point_size(value: Any) -> float | None:
    """Return ``value`` as a positive float, or ``None`` when unset."""
    if value is None:
        return None
    message = f"point_size must be a positive real number or None, got {value!r}"
    if isinstance(value, bool):
        raise ValueError(message)
    try:
        size = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(message) from exc
    if not math.isfinite(size) or size <= 0:
        raise ValueError(message)
    return size


def resolve_layer_sources(
    layers: list[Layer],
    frame: pd.DataFrame,
    resolve: Callable[[Any], Any],
    point_size: float | None = None,
) -> list[LayerSpec]:
    """Resolve a list of Layer objects into fully concrete LayerSpecs.

    Shared by ``FigureEngine`` (legacy) and ``FigureGenerator`` (Phase 15) so
    both engines reuse the same resolution code path.

    For each layer:
    1. Apply the Stat transformation to the data
    2. Resolve each channel's source (DimensionSelector → column names)
    3. Extract data series for column references
    4. Apply Scales to transform data → visual domain
    5. Package into LayerSpec

    ``resolve(source)`` maps a channel source to either a list of concrete
    column names (present in ``frame``) or a constant value, mirroring
    ``resolve_source`` semantics against a frame instead of a Dataset.

    ``point_size`` supplies a constant ``size`` for point/site_point layers
    that do not already bind a size channel.
    """
    point_size = _normalize_point_size(point_size)
    layer_specs: list[LayerSpec] = []

    for layer in layers:
        # 1. Apply stat transformation
        stat_data = layer.stat.compute(frame)

        # 2. Resolve each mapping channel
        visual_mapping: dict[str, Any] = {}
        for channel, source in layer.mapping.items():

            # Check if source is a stat-produced column first
            if isinstance(source, str) and source in stat_data.columns:
                series = stat_data[source]
                if layer.scales and channel in layer.scales:
                    series = layer.scales[channel].transform(series)
                visual_mapping[channel] = series
                continue

            resolved = resolve(source)

            # 3. Extract data and apply scales
            if isinstance(resolved, list):
                # Column reference(s) — extract from stat-transformed data
                if all(col in stat_data.columns for col in resolved):
                    if len(resolved) == 1:
                        series = stat_data[resolved[0]]
                    else:
                        series = stat_data[resolved]
                else:
                    # Fall back to original dataframe
                    if len(resolved) == 1:
                        series = frame[resolved[0]]
                    else:
                        series = frame[resolved]

                # 4. Apply scale if present
                if layer.scales and channel in layer.scales:
                    series = layer.scales[channel].transform(series)
                visual_mapping[channel] = series
            else:
                # Constant value — apply scale if available
                if layer.scales and channel in layer.scales:
                    values = pd.Series([resolved] * len(stat_data))
                    visual_mapping[channel] = layer.scales[channel].transform(values)
                else:
                    visual_mapping[channel] = resolved

        # A recipe-level "point_size" knob injects a constant size onto point
        # geoms (scatter markers) unless the layer already binds a size
        # channel. Text/annotation geoms share the "size" channel name for
        # font size, so only point-style geoms are scaled.
        if (
            point_size is not None
            and "size" not in visual_mapping
            and layer.geom.name in ("point", "site_point")
        ):
            visual_mapping["size"] = point_size

        layer_specs.append(LayerSpec(
            geom=layer.geom,
            stat=layer.stat,
            visual_mapping=visual_mapping,
            data_override=layer.data_override,
            zorder=layer.zorder,
            xlim=layer.xlim,
            ylim=layer.ylim,
        ))

    return layer_specs


def summarize_mappings(
    layers: list[Layer],
    layer_specs: list[LayerSpec],
) -> dict[str, Any]:
    """Build a summary mappings dict from resolved layers for backward compat."""
    summary: dict[str, Any] = {}
    for spec in layer_specs:
        for channel, value in spec.visual_mapping.items():
            if channel not in summary and not isinstance(value, dict):
                summary[channel] = value
    return summary


def resolve_settings(
    settings: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Format string settings values against the iteration context."""
    resolved: dict[str, Any] = {}

    for key, value in settings.items():
        if isinstance(value, str):
            try:
                resolved[key] = value.format(**context)
            except KeyError:
                resolved[key] = value
        else:
            resolved[key] = value

    return resolved


def _check_required_channels(layer_specs: list[LayerSpec]) -> None:
    """Raise an informative error when a layer is missing a required channel.

    Checked lazily at spec-build time — no eager validation at recipe/registry
    time (Phase 15 lazy default resolution). ``GeomFunctionLine`` layers with
    a ``func`` expression are exempt: their x domain is derived from the
    function (the legacy render handler falls back to the current axes limits
    when no x is mapped), so x is not required from the data mapping.
    """
    for spec in layer_specs:
        geom = spec.geom
        if isinstance(geom, GeomFunctionLine) and geom.func:
            continue
        missing = [
            channel
            for channel in geom.required_channels
            if channel not in spec.visual_mapping
        ]
        if missing:
            raise ValueError(
                f"Geom '{geom.name}' requires channel(s) "
                f"{', '.join(missing)}; mapping supplies only "
                f"{', '.join(spec.visual_mapping) or '(none)'}"
            )


@dataclass(frozen=True)
class EngineConfig:
    """Configuration for the FigEngine orchestration layer."""

    default_settings: dict[str, Any] = field(default_factory=dict)
    default_context: dict[str, Any] = field(default_factory=dict)
    strict: bool = False ## Enables/Disables single value literals (ex. 'Blue')


class FigureEngine:
    """Orchestrates data expansion, template building, and rendering."""

    def __init__(self, config: EngineConfig | None = None) -> None:
        self.config = config or EngineConfig()
        self._legend_accumulator = LegendAccumulator()

    # ------------------------------------------------------------------
    # NEW API: layers / template
    # ------------------------------------------------------------------

    def build_specs_from_layers(
        self,
        dataset: Dataset,
        layers: list[Layer],
        settings: dict[str, Any] | None = None,
        iterators: Sequence[DimensionIterator] | DimensionIterator | None = None,
        coord: Coord | None = None,
        facet: Facet | None = None,
        _template_name: str = "custom",
    ) -> list[FigureSpec]:
        """Build FigureSpecs from Layer objects (Grammar of Graphics path)."""
        if isinstance(iterators, DimensionIterator):
            iterators = [iterators]

        final_settings = {**self.config.default_settings, **(settings or {})}
        final_context = {**self.config.default_context}

        results = expand(dataset, iterators or [])
        specs: list[FigureSpec] = []
        for result in results:
            merged_context = {**final_context, **result.context.values}
            resolved_settings = self._resolve_settings(final_settings, merged_context)

            layer_specs = self._resolve_layers(layers, dataset, merged_context)

            data = dataset.dataframe if not result.subset_df.empty else result.subset_df

            spec = FigureSpec(
                data=data,
                mappings=self._summarize_mappings(layers, layer_specs),
                settings=resolved_settings,
                context=merged_context,
                template_name=_template_name,
                iterator_key=result.iterator_key,
                layers=layer_specs,
                coord=coord or CoordCartesian(),
                facet=facet or FacetNull(),
            )
            specs.append(spec)

        # Accumulate legend data from resolved specs
        for spec in specs:
            self._legend_accumulator.add_from_spec(spec)

        return specs

    def build_specs_from_template(
        self,
        dataset: Dataset,
        template: FigureTemplate,
        settings: dict[str, Any] | None = None,
        iterators: Sequence[DimensionIterator] | DimensionIterator | None = None,
        facet: Facet | None = None,
    ) -> list[FigureSpec]:
        """Build FigureSpecs from a FigureTemplate."""
        merged_settings = {**template.default_settings, **(settings or {})}
        return self.build_specs_from_layers(
            dataset=dataset,
            layers=template.layers,
            settings=merged_settings,
            iterators=iterators,
            coord=template.coord,
            facet=facet,
            _template_name=template.name,
        )



    def render_specs(self, specs: list[FigureSpec], renderer: BaseRenderer) -> list[Any]:
        """Render an existing list of FigureSpec objects."""
        validate_dict({str(i): spec for i, spec in enumerate(specs)}, "specs", key_type=str, allow_empty=True)
        if renderer is None:
            raise ValueError("renderer must be provided")

        return renderer.render_all(specs)
    
    def render_spec(self, spec: FigureSpec, renderer: BaseRenderer) -> Any:
        if renderer is None:
            raise ValueError("renderer must be provided")

        return renderer.render(spec)

    def render_legend(self, renderer: BaseRenderer) -> Any:
        if renderer is None:
            raise ValueError("renderer must be provided")
        if not hasattr(renderer, "render_legend"):
            raise NotImplementedError("Renderer does not support render_legend")
        return renderer.render_legend(self._legend_accumulator)

    def clear_legend(self) -> None:
        self._legend_accumulator.clear()

    # ------------------------------------------------------------------
    # Resolver: Layer → LayerSpec
    # ------------------------------------------------------------------

    def _resolve_layers(
        self,
        layers: list[Layer],
        dataset: Dataset,
        context: dict[str, Any],
    ) -> list[LayerSpec]:
        """Resolve Layer objects into LayerSpecs (delegates to the shared helper)."""
        return resolve_layer_sources(
            layers,
            frame=dataset.dataframe,
            resolve=lambda source: resolve_source(
                source,
                dataset,
                strict=self.config.strict,
                context=context,
            ),
        )

    def _summarize_mappings(
        self,
        layers: list[Layer],
        layer_specs: list[LayerSpec],
    ) -> dict[str, Any]:
        """Build a summary mappings dict (delegates to the shared helper)."""
        return summarize_mappings(layers, layer_specs)

    # ------------------------------------------------------------------
    # Old resolve helpers
    # ------------------------------------------------------------------

    def _align_required_mappings(
        self,
        mappings: dict[Mapping, SourceType],
        required_keys: tuple[Mapping, ...],
    ) -> dict[Mapping, SourceType]:
        """
        Align required mappings by broadcasting single values.
        """
        lengths = {}
        for key in required_keys:
            value = mappings.get(key)
            if isinstance(value, list):
                lengths[key] = len(value)
            elif isinstance(value, str):
                lengths[key] = 1
            else:
                lengths[key] = 1
        unique_lengths = set(lengths.values())
        if len(unique_lengths) == 1:
            target_len = unique_lengths.pop()
        else:
            non_one_lengths = {l for l in unique_lengths if l != 1}
            if len(non_one_lengths) > 1:
                raise ValueError(
                    f"Dimension mismatch in required mappings: {lengths}"
                )
            target_len = max(non_one_lengths) if non_one_lengths else 1
        aligned = {}
        for key, value in mappings.items():
            if key in required_keys:
                if isinstance(value, list):
                    if len(value) == target_len:
                        aligned[key] = value
                    elif len(value) == 1:
                        aligned[key] = value * target_len
                    else:
                        raise ValueError(
                            f"Cannot align mapping '{key}' of length {len(value)} "
                            f"to target length {target_len}"
                        )
                else:
                    aligned[key] = [value] * target_len
            else:
                aligned[key] = value
        return aligned

    def _resolve_mappings(
        self,
        dataset: Dataset,
        mappings: dict[Mapping, SourceType],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Convert Mapping enum keys to string names and resolve sources."""
        resolved: dict[str, Any] = {}

        for mapping_enum, source in mappings.items():
            mapping_name = mapping_enum.value.name
            resolved[mapping_name] = resolve_source(
                source,
                dataset,
                strict=self.config.strict,
                context=context,
            )

        return resolved
    
    def _resolve_settings(
        self, 
        settings: dict[str, Any],
        context: dict[str, Any]
    )-> dict[str, Any]:
        """Resolve context-formatted settings (delegates to the shared helper)."""
        return resolve_settings(settings, context)


class FigureGenerator:
    """Provider-driven orchestrator (ARCHITECTURE.md §12, Phase 15).

    The ONLY component allowed to orchestrate multiple subsystems. It consumes
    **only** ``DataProvider`` (``provider.resolve`` / ``provider.expand`` /
    ``provider.subset``) — it never touches a ``Dataset`` object directly.
    Legacy ``Dataset`` input reaches this generator through ``DatasetProvider``.
    """

    def __init__(
        self,
        provider: DataProvider,
        layers: list[Layer],
        coord: Coord,
        facet: Facet = FacetNull(),
        scales: dict[str, Scale] | None = None,
        settings: dict | None = None,
        iterators: list[DimensionIterator] | None = None,
    ) -> None:
        self.provider = provider
        self.layers = list(layers)
        self.coord = coord or CoordCartesian()
        self.facet = facet or FacetNull()
        self.scales = dict(scales or {})
        self.settings = dict(settings or {})
        self.iterators = iterators

    # ------------------------------------------------------------------
    # Layer / source resolution (provider-based)
    # ------------------------------------------------------------------

    def _effective_layers(self) -> list[Layer]:
        """Layers with generator-level scale defaults merged in (per-layer wins)."""
        if not self.scales:
            return self.layers
        effective: list[Layer] = []
        for layer in self.layers:
            effective.append(
                replace(layer, scales={**self.scales, **(layer.scales or {})})
            )
        return effective

    def _resolve_source(
        self,
        source: Any,
        frame: pd.DataFrame,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Resolve a channel source against ``frame`` via the provider.

        Mirrors legacy ``resolve_source`` semantics without a Dataset:
        column names resolve through ``provider.resolve``; non-column strings
        and other values are treated as constants (non-strict).
        """
        if isinstance(source, str):
            if context:
                try:
                    source = source.format(**context)
                except KeyError:
                    pass
            if source in frame.columns:
                return self.provider.resolve(source)
            return source  # constant value (non-strict)

        if isinstance(source, list):
            return self.provider.resolve(source)

        # DimensionSelector-like objects (incl. duck-typed selectors) → provider
        if hasattr(source, "selector") and not isinstance(source, tuple):
            return self.provider.resolve(source)

        # Constant value (incl. tuples like literal colors)
        return source

    # ------------------------------------------------------------------
    # Spec building + rendering
    # ------------------------------------------------------------------

    def build_specs(self) -> list[FigureSpec]:
        """Expand the provider and build one validated FigureSpec per
        iterator combination.

        Resolution order:
        1. expand the provider (``provider.expand``) — one ``(frame,
           context)`` per iterator combination; no iterators yields the full
           frame
        2. resolve channel selectors (``provider.resolve``) + scales
        3. package into validated ``FigureSpec``(s)

        Facets are **not** pre-split here (Phase 18.1): the full
        iterator-context frame and the facet spec are stamped on each
        FigureSpec, and the renderer applies the facet panel-wise (one
        multi-panel figure per spec) — matching the legacy
        ``FigureEngine.build_specs_from_layers`` behavior and the documented
        facet/iterator distinction (panels within one figure vs. independent
        figures).
        """
        specs: list[FigureSpec] = []
        for frame, iter_ctx in self.provider.expand(self.iterators or []):
            context = {**iter_ctx}
            resolved_settings = resolve_settings(self.settings, context)
            if "point_size" in resolved_settings:
                resolved_settings["point_size"] = _normalize_point_size(
                    resolved_settings["point_size"]
                )
            layers = self._effective_layers()
            layer_specs = resolve_layer_sources(
                layers,
                frame=frame,
                resolve=lambda source, _f=frame, _c=context: (
                    self._resolve_source(source, _f, _c)
                ),
                point_size=resolved_settings.get("point_size"),
            )
            _check_required_channels(layer_specs)
            specs.append(
                FigureSpec(
                    data=frame,
                    mappings=summarize_mappings(layers, layer_specs),
                    settings=resolved_settings,
                    context=context,
                    template_name="custom",
                    iterator_key=tuple(sorted(context)),
                    layers=layer_specs,
                    coord=self.coord,
                    facet=self.facet,
                )
            )
        return specs

    def render(
        self,
        renderer: BaseRenderer | None = None,
        renderer_name: str = "matplotlib",
    ) -> list[Any]:
        """Build the specs and hand them to a renderer; returns backend figures.

        Missing required channels surface here as an informative error at
        spec-build time (no eager validation earlier).
        """
        from geofig_engine.renderers import MatplotlibRenderer

        if renderer is None:
            if renderer_name != "matplotlib":
                raise ValueError(
                    f"Unsupported renderer: '{renderer_name}'. "
                    "Only 'matplotlib' is available."
                )
            renderer = MatplotlibRenderer()
        specs = self.build_specs()
        return list(renderer.render_all(specs))
