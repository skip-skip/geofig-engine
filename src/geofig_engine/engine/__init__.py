"""
Engine interface for FigEngine.

Provides the top-level classes used by the engine orchestration layer,
plus a simplified ``render_template`` entry point.
"""

from .generator import EngineConfig, FigureEngine
from .entry import render_template

__all__ = ["EngineConfig", "FigureEngine", "render_template"]
