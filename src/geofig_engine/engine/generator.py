"""
Engine orchestration for FigEngine.

This module builds renderer-ready FigureSpec objects from Dataset,
template, and mapping inputs, and optionally dispatches them to a renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from geofig_engine.core.attribute_mapping import SourceType, resolve_source
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.iterator import DimensionIterator, IteratorResult, expand
from geofig_engine.core.spec import FigureSpec
from geofig_engine.renderers.base import BaseRenderer
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.validation import validate_dict


@dataclass(frozen=True)
class EngineConfig:
    """Configuration for the FigEngine orchestration layer."""

    default_settings: dict[str, Any] = field(default_factory=dict)
    default_context: dict[str, Any] = field(default_factory=dict)
    strict: bool = False


class FigureEngine:
    """Orchestrates data expansion, template building, and rendering."""

    def __init__(self, config: EngineConfig | None = None) -> None:
        self.config = config or EngineConfig()

    def build_specs(
        self,
        dataset: Dataset,
        template: FigureTemplate,
        mappings: dict[str, SourceType],
        settings: dict[str, Any] | None = None,
        iterators: Sequence[DimensionIterator] | DimensionIterator | None = None,
    ) -> list[FigureSpec]:
        """Build one or more fully resolved FigureSpec objects."""
        validate_dict(mappings, "mappings", key_type=str, allow_empty=True)
        validate_dict(settings or {}, "settings", key_type=str, allow_empty=True)

        if isinstance(iterators, DimensionIterator):
            iterators = [iterators]

        template_defaults = template.default_settings or {}
        template_default_mappings = {
            key: value
            for key, value in template_defaults.items()
            if key in template.supported_mappings
        }
        template_default_settings = {
            key: value
            for key, value in template_defaults.items()
            if key not in template.supported_mappings
        }

        final_settings = {
            **template_default_settings,
            **self.config.default_settings,
            **(settings or {}),
        }
        final_context = {**self.config.default_context}
        merged_mappings = {**template_default_mappings, **mappings}
        alligned_mappings = self._align_required_mappings(
            merged_mappings, template.required_mappings
        )
        results = expand(dataset, iterators or [])
        specs: list[FigureSpec] = []
        for result in results:
            subset_dataset = Dataset(
                dataframe=result.subset_df,
                key_column=dataset.key_column,
                dimensions=dataset.dimensions,
            )
            merged_context = {**final_context, **result.context.values}
            resolved_mappings = self._resolve_mappings(
                subset_dataset,
                alligned_mappings,
                merged_context,
            )
            resolved_settings = self._resolve_settings(
                final_settings, 
                merged_context
            )

            spec = template.build_template_spec(
                data=subset_dataset.dataframe,
                mappings=resolved_mappings,
                settings=resolved_settings,
                context=merged_context,
                iterator_key=result.iterator_key,
            )
            specs.append(spec)
        return specs

    def render(
        self,
        dataset: Dataset,
        template: FigureTemplate,
        mappings: dict[str, SourceType],
        renderer: BaseRenderer,
        settings: dict[str, Any] | None = None,
        iterators: Sequence[DimensionIterator] | DimensionIterator | None = None,
    ) -> list[Any]:
        """Build specs and render them with the provided renderer."""
        if renderer is None:
            raise ValueError("renderer must be provided")
        if isinstance(iterators, DimensionIterator):
            iterators = [iterators]
        specs = self.build_specs(
            dataset=dataset,
            template=template,
            mappings=mappings,
            settings=settings,
            iterators=iterators,
        )
        return renderer.render_all(specs)

    def render_and_save(
        self,
        dataset: Dataset,
        template: FigureTemplate,
        mappings: dict[str, SourceType],
        renderer: BaseRenderer,
        outdir: str,
        settings: dict[str, Any] | None = None,
        iterators: Sequence[DimensionIterator] | DimensionIterator | None = None,
    ) -> list[Any]:
        """Render and save all figures to the specified output directory. 
        Filename can be a template string with context keys, or defaults to '{template.name}_{i}.png'."""
        figures = self.render(dataset, template, mappings, renderer, settings, iterators)
        for i, fig in enumerate(figures):
            filename = f"{template.name}_{i}.png"
            if hasattr(fig, "figname") and fig.figname:
                filename = f"{fig.figname}.png"
            fig.savefig(f"{outdir}/{filename}")

    def render_specs(self, specs: list[FigureSpec], renderer: BaseRenderer) -> list[Any]:
        """Render an existing list of FigureSpec objects."""
        validate_dict({str(i): spec for i, spec in enumerate(specs)}, "specs", key_type=str, allow_empty=True)
        if renderer is None:
            raise ValueError("renderer must be provided")

        return renderer.render_all(specs)

    def _align_required_mappings(
        self,
        mappings: dict[str, Any],
        required_keys: tuple[str, ...],
    ) -> dict[str, Any]:
        """
        Align required mappings by broadcasting single values.

        Rules:
        - Only keys in `required_keys` are aligned.
        - Strings and single-item lists are broadcast to match the target length.
        - If multiple required mappings have list values, they must all have the same length.
        - If mismatched lengths are found → raise ValueError.

        Returns:
            A new mappings dict with aligned required mappings.

        Raises:
            ValueError: If required mappings have incompatible lengths.
        """
        # Determine lengths of list-based required mappings
        lengths = {}
        for key in required_keys:
            value = mappings.get(key)
            if isinstance(value, list):
                lengths[key] = len(value)
            elif isinstance(value, str):
                lengths[key] = 1
            else:
                # treat other scalars as length 1
                lengths[key] = 1
        # Determine target length
        unique_lengths = set(lengths.values())
        if len(unique_lengths) == 1:
            target_len = unique_lengths.pop()
        else:
            # allow broadcasting only if mismatch is between 1 and N
            non_one_lengths = {l for l in unique_lengths if l != 1}
            if len(non_one_lengths) > 1:
                raise ValueError(
                    f"Dimension mismatch in required mappings: {lengths}"
                )
            target_len = max(non_one_lengths) if non_one_lengths else 1
        # Build aligned mapping
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
                    # scalar or string → broadcast
                    aligned[key] = [value] * target_len
            else:
                # leave non-required mappings untouched
                aligned[key] = value
        return aligned
    def _resolve_mappings(
        self,
        dataset: Dataset,
        mappings: dict[str, SourceType],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved: dict[str, Any] = {}

        for name, source in mappings.items():
            resolved[name] = resolve_source(
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
                    # Leave unchanged if missing context key
                    resolved[key] = value
            else:
                resolved[key] = value

        return resolved
    