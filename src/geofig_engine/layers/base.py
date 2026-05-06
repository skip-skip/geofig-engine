"""
Base layer abstractions for templates.

Layers define reusable building blocks for constructing FigureSpecs within templates.
"""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class FigureLayer:
    pass