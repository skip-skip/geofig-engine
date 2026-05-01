"""
Renderer contract for FigEngine.

Renderers consume fully resolved FigureSpec objects and produce backend-specific
visual artifacts. The base renderer provides the minimal renderer interface and
default batch rendering support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable

from geofig_engine.core.spec import FigureSpec


class BaseRenderer(ABC):
    """Abstract base class for FigEngine renderers."""

    @abstractmethod
    def render(self, spec: FigureSpec) -> Any:
        """Render a single FigureSpec and return a backend object."""
        raise NotImplementedError

    def render_all(self, specs: Iterable[FigureSpec]) -> list[Any]:
        """Render multiple FigureSpecs in deterministic order."""
        return [self.render(spec) for spec in specs]

    def close(self) -> None:
        """Optional cleanup for stateful renderers."""
        return None

    def supports(self, spec: FigureSpec) -> bool:
        """Return whether this renderer supports the given spec."""
        return True
