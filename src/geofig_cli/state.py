from dataclasses import dataclass, field
from typing import Any

from geofig_engine.core.iterator import DimensionIterator

@dataclass
class IteratorConfig:
    channel: str
    selector: str
    mode: DimensionIterator.Mode

@dataclass
class MappingValue:
    mapping_type: str
    value: str
    value_resolved: Any

    def render(self) -> str:
        if self.mapping_type == "value":
            return self.value
        if self.mapping_type == "dimension":
            return f'"{self.value}"'
        if self.mapping_type == "label":
            return f"[{self.value}]"
        if self.mapping_type == "iterator":
            return f"{'{'}{self.value}{'}'}"
        return f"{self.mapping_type}:{self.value}"
    
@dataclass
class LayerOption:
    key: str
    value: Any
    selected: bool = False

    def display_name(self) -> str:
        if hasattr(self.value, "name"):
            return str(self.value.name)

        return str(self.value)

@dataclass
class ConfigState:
    iterators: list[IteratorConfig] = field(default_factory=list)
    mappings: dict[str, MappingValue] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    layer_settings: dict[str, Any] = field(default_factory=dict)
    layer_options: list[LayerOption] = field(default_factory=list)

@dataclass
class Cell:
    group: str
    key: str
    display: str
    action: str
    payload: Any = None
