"""
Base template abstractions for FigEngine.

Templates define the contract between resolved data mappings and a FigureSpec.
They apply required mapping validation, default settings, and spec creation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum

import pandas as pd

from geofig_engine.core.spec import FigureSpec, build_spec
from geofig_engine.utils.validation import validate_dict, validate_sequence, validate_string
from geofig_engine.layers.base import FigureLayer
from geofig_engine.utils.typing import MappingData

@dataclass(frozen=True)
class FigureTemplate:
    class ProjectionType(Enum):
        CARTESIAN = 'cartesian'
        POLAR = 'polar'
        THREE_D = '3d'
        TERNARY = 'ternary'
    name: str
    required_mappings: tuple[MappingData, ...]
    optional_mappings: tuple[MappingData, ...] = field(default_factory=tuple)
    default_settings: dict[str, Any] = field(default_factory=dict)
    projection: ProjectionType = ProjectionType.CARTESIAN
    layers: list[FigureLayer] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        validate_string(self.name, "name", allow_empty=False)
        validate_sequence(self.required_mappings, "required_mappings", MappingData, allow_empty=False)
        validate_sequence(self.optional_mappings, "optional_mappings", MappingData, allow_empty=True)
        validate_dict(self.default_settings, "default_settings", key_type=str, allow_empty=True)

    @property
    def supported_mapping_names(self) -> tuple[str, ...]:
        """Extract mapping names from MappingData."""
        required_names = [m.name for m in self.required_mappings]
        optional_names = [m.name for m in self.optional_mappings]
        return tuple(sorted(set(required_names + optional_names)))
    
    @property
    def supported_mapping_channels(self) -> tuple[str, ...]:
        """Extract channel values from MappingData."""
        required_channels = [m.channel.value for m in self.required_mappings]
        optional_channels = [m.channel.value for m in self.optional_mappings]
        return tuple(sorted(set(required_channels + optional_channels)))

    
    def fill_mappings(self, mappings: dict[str, Any]) -> dict[str, Any]:
        """Fill missing mappings from layer defaults using channel metadata."""
        for layer in self.layers:
            for mapping_data in self.required_mappings + self.optional_mappings:
                channel_key = mapping_data.channel.value
                if channel_key not in mappings and hasattr(layer, channel_key):
                    mappings[channel_key] = getattr(layer, channel_key)
        return mappings
    def validate_mappings(self, mappings: dict[str, Any]) -> None:
        validate_dict(mappings, "mappings", key_type=str, allow_empty=True)

        for required in [m.name for m in self.required_mappings]:
            if required not in mappings:
                raise ValueError(
                    f"Template '{self.name}' requires mapping '{required}'"
                )

        for mapping_key in mappings:
            if mapping_key not in self.supported_mapping_names:
                raise ValueError(
                    f"Unsupported mapping '{mapping_key}' for template '{self.name}'"
                )

    def build_template_spec(
        self,
        data: pd.DataFrame,
        mappings: dict[str, Any],
        settings: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        iterator_key: tuple[str, ...] = (),
    ) -> FigureSpec:
        """Build a validated FigureSpec using template defaults and mappings."""
        self.validate_mappings(mappings)
        mappings = self.fill_mappings(mappings)

        template_settings = {
            key: value
            for key, value in self.default_settings.items()
            if key not in self.supported_mapping_channels
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
            layers=self.layers,
        )
