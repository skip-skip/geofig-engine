"""
Engine orchestration for FigEngine.

This module builds renderer-ready FigureSpec objects from Dataset,
template, and mapping inputs, and optionally dispatches them to a renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from geofig_engine.core.attribute_mapping import SourceType, resolve_source
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.iterator import IteratorResult, expand
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
        context: dict[str, Any] | None = None,
        iterator_selectors: dict[str, SourceType] | None = None,
    ) -> list[FigureSpec]:
        """Build one or more fully resolved FigureSpec objects."""
        validate_dict(mappings, "mappings", key_type=str, allow_empty=True)
        validate_dict(settings or {}, "settings", key_type=str, allow_empty=True)
        validate_dict(context or {}, "context", key_type=str, allow_empty=True)
        validate_dict(iterator_selectors or {}, "iterator_selectors", key_type=str, allow_empty=True)

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
        final_context = {**self.config.default_context, **(context or {})}
        merged_mappings = {**template_default_mappings, **mappings}

        results = expand(dataset, iterator_selectors or {})
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
                merged_mappings,
                merged_context,
            )
            resolved_settings = self._resolve_settings(
                final_settings, 
                merged_context
            )

            spec = template.build_spec(
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
        context: dict[str, Any] | None = None,
        iterator_selectors: dict[str, SourceType] | None = None,
    ) -> list[Any]:
        """Build specs and render them with the provided renderer."""
        if renderer is None:
            raise ValueError("renderer must be provided")

        specs = self.build_specs(
            dataset=dataset,
            template=template,
            mappings=mappings,
            settings=settings,
            context=context,
            iterator_selectors=iterator_selectors,
        )
        return renderer.render_all(specs)

    def render_specs(self, specs: list[FigureSpec], renderer: BaseRenderer) -> list[Any]:
        """Render an existing list of FigureSpec objects."""
        validate_dict({str(i): spec for i, spec in enumerate(specs)}, "specs", key_type=str, allow_empty=True)
        if renderer is None:
            raise ValueError("renderer must be provided")

        return renderer.render_all(specs)

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