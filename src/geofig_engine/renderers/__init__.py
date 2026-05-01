"""
Renderers for FigEngine.

This package exposes renderer implementations used by the engine.
"""

from .base import BaseRenderer
from .matplotlib_renderer import MatplotlibRenderer

__all__ = ["BaseRenderer", "MatplotlibRenderer"]
