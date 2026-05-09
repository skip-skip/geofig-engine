from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class Dimension:
    name: str
    labels: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("Dimension.name must be a string")

        if not isinstance(self.labels, dict):
            raise TypeError("Dimension.labels must be a dict[str, Any]")

        for key in self.labels:
            if not isinstance(key, str):
                raise TypeError("Dimension.labels keys must be strings")

    def get_label(self, key: str, default: Any = None) -> Any:
        return self.labels.get(key, default)

    def has_label(self, key: str) -> bool:
        return key in self.labels
