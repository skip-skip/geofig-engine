"""
Engine orchestration for FigEngine.

This module builds renderer-ready FigureSpec objects from Dataset,
template, and mapping inputs, and optionally dispatches them to a renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import pandas as pd

from geofig_engine.core.attribute_mapping import SourceType, resolve_source
from geofig_engine.core.coord import Coord, CoordCartesian
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.facet import Facet, FacetNull
from geofig_engine.core.iterator import DimensionIterator, IteratorResult, expand
from geofig_engine.core.layer import Layer, LayerSpec
from geofig_engine.core.scale import Scale
from geofig_engine.core.spec import FigureSpec, build_spec
from geofig_engine.renderers.base import BaseRenderer
from geofig_engine.renderers.matplotlib.legend import LegendAccumulator
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.validation import validate_dict
from geofig_engine.utils.typing import Mapping


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
                template_name="custom",
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
        """Resolve a list of Layer objects into fully concrete LayerSpecs.

        For each layer:
        1. Apply the Stat transformation to the data
        2. Resolve each channel's source (DimensionSelector → column names)
        3. Extract data series for column references
        4. Apply Scales to transform data → visual domain
        5. Package into LayerSpec
        """
        layer_specs: list[LayerSpec] = []

        for layer in layers:
            # 1. Apply stat transformation
            stat_data = layer.stat.compute(dataset.dataframe)

            # 2. Resolve each mapping channel
            visual_mapping: dict[str, Any] = {}
            for channel, source in layer.mapping.items():
                resolved = resolve_source(
                    source,
                    dataset,
                    strict=self.config.strict,
                    context=context,
                )

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
                            series = dataset.dataframe[resolved[0]]
                        else:
                            series = dataset.dataframe[resolved]

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

            layer_specs.append(LayerSpec(
                geom=layer.geom,
                stat=layer.stat,
                visual_mapping=visual_mapping,
                data_override=layer.data_override,
            ))

        return layer_specs

    def _summarize_mappings(
        self,
        layers: list[Layer],
        layer_specs: list[LayerSpec],
    ) -> dict[str, Any]:
        """Build a summary mappings dict from resolved layers for backward compat."""
        summary: dict[str, Any] = {}
        for spec in layer_specs:
            for channel, value in spec.visual_mapping.items():
                if channel not in summary:
                    summary[channel] = value
        return summary

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
        resolved = {}

        for key, value in settings.items():
            if isinstance(value, str):
                try:
                    resolved[key] = value.format(**context)
                except KeyError:
                    resolved[key] = value
            else:
                resolved[key] = value

        return resolved
    