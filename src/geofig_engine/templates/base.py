"""
Base template abstractions for FigEngine.

Templates define the contract between resolved data mappings and a FigureSpec.
They apply required mapping validation, default settings, and spec creation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from geofig_engine.core.spec import FigureSpec, build_spec
from geofig_engine.utils.validation import validate_dict, validate_sequence, validate_string


@dataclass(frozen=True)
class FigureTemplate:
    name: str
    required_mappings: tuple[str, ...]
    optional_mappings: tuple[str, ...] = field(default_factory=tuple)
    default_settings: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_string(self.name, "name", allow_empty=False)
        validate_sequence(self.required_mappings, "required_mappings", str, allow_empty=False)
        validate_sequence(self.optional_mappings, "optional_mappings", str, allow_empty=True)
        validate_dict(self.default_settings, "default_settings", key_type=str, allow_empty=True)

    @property
    def supported_mappings(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.required_mappings + self.optional_mappings)))

    def validate_mappings(self, mappings: dict[str, Any]) -> None:
        validate_dict(mappings, "mappings", key_type=str, allow_empty=True)

        for required in self.required_mappings:
            if required not in mappings:
                raise ValueError(
                    f"Template '{self.name}' requires mapping '{required}'"
                )

        for mapping_key in mappings:
            if mapping_key not in self.supported_mappings:
                raise ValueError(
                    f"Unsupported mapping '{mapping_key}' for template '{self.name}'"
                )

    def build_spec(
        self,
        data: pd.DataFrame,
        mappings: dict[str, Any],
        settings: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        iterator_key: tuple[str, ...] = (),
    ) -> FigureSpec:
        """Build a validated FigureSpec using template defaults and mappings."""
        self.validate_mappings(mappings)

        template_settings = {
            key: value
            for key, value in self.default_settings.items()
            if key not in self.supported_mappings
        }
        final_settings = {**template_settings, **(settings or {})}
        final_context = context or {}

        return build_spec(
            data=data,
            mappings=mappings,
            settings=final_settings,
            context=final_context,
            template_name=self.name,
            iterator_key=iterator_key,
        )
