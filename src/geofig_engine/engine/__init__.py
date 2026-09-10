"""
Engine interface for FigEngine.

Provides the top-level classes used by the engine orchestration layer,
plus the canonical ``render_template`` entry point (Phase 15). The legacy
tuple-form entry lives in ``engine/entry.py`` (renamed to
``render_template_legacy`` in ``15_wp5``).
"""

from .api import render_template
from .generator import EngineConfig, FigureEngine

__all__ = ["EngineConfig", "FigureEngine", "render_template"]
