"""
Base layer abstractions for templates.

Layers define reusable building blocks for constructing FigureSpecs within templates.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

@dataclass(frozen=True)
class FigureLayer:

    def get_attribute_map(layer):
        return {
            f.metadata["attribute"]: getattr(layer, f.name)
            for f in fields(layer)
            if "attribute" in f.metadata
        }