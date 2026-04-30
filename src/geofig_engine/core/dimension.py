from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class Dimension:
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("Dimension.name must be a string")

        if not isinstance(self.attributes, dict):
            raise TypeError("Dimension.attributes must be a dict[str, Any]")

        for key in self.attributes:
            if not isinstance(key, str):
                raise TypeError("Dimension.attributes keys must be strings")

    def get_attribute(self, key: str, default: Any = None) -> Any:
        return self.attributes.get(key, default)

    def has_attribute(self, key: str) -> bool:
        return key in self.attributes

    def is_role(self, role_name: str) -> bool:
        return self.attributes.get("role") == role_name
