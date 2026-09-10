"""
Legacy tuple-form entry point for FigEngine (deprecated — Phase 15).

The former ``render_template()`` is preserved verbatim as
``render_template_legacy`` and emits a call-time ``DeprecationWarning``. New
work goes through the canonical ``geofig_engine.render_template``
(``engine/api.py``), which returns ``list[Figure]``. Removed no earlier than
the next major version (>= 1.0.0).
"""

from __future__ import annotations

import warnings

from pathlib import Path
from typing import Any, Sequence

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.facet import Facet
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.engine.generator import FigureEngine

__all__ = ["render_template_legacy"]


def render_template_legacy(
    dataset: Dataset,
    template: FigureTemplate,
    iterators: Sequence[DimensionIterator] | DimensionIterator | None = None,
    settings: dict[str, Any] | None = None,
    facet: Facet | None = None,
    renderer_name: str = "matplotlib",
    savedir: str | Path | None = None,
) -> tuple[list, list, Any]:
    """Build, render, and optionally save figures from a template (legacy).

    Deprecated: use ``render_template(data, template=...)`` (returns
    ``list[Figure]``) instead. This tuple-form entry is kept verbatim and
    removed no earlier than geofig-engine >= 1.0.0.

    Args:
        dataset: The data to visualize.
        template: A ``FigureTemplate`` defining layers, coord, defaults.
        iterators: Optional iterators for multi-figure expansion.
        settings: Override settings merged on top of template defaults.
        facet: Optional facet spec for subplot splitting.
        renderer_name: Backend name. Only ``"matplotlib"`` is supported.
        savedir: If provided, each rendered figure is saved here as a PNG,
                 including a ``legend.png``.

    Returns:
        Tuple of ``(specs, figures, legend_fig)`` where ``specs`` is the
        list of ``FigureSpec`` objects, ``figures`` is the list of rendered
        backend figure objects, and ``legend_fig`` is the accumulated legend
        figure (or an empty figure if no legend entries exist).

    Raises:
        ValueError: If ``renderer_name`` is not ``"matplotlib"``.
    """
    warnings.warn(
        "geofig_engine.render_template_legacy is deprecated; use "
        "render_template(data, template=...) which returns list[Figure]. "
        "It will be removed in geofig-engine >= 1.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    from geofig_engine.renderers import MatplotlibRenderer

    if renderer_name != "matplotlib":
        raise ValueError(
            f"Unsupported renderer: '{renderer_name}'. Only 'matplotlib' is available."
        )

    engine = FigureEngine()
    specs = engine.build_specs_from_template(
        dataset=dataset,
        template=template,
        settings=settings,
        iterators=iterators,
        facet=facet,
    )

    renderer = MatplotlibRenderer()
    figures = list(renderer.render_all(specs))
    legend_fig = engine.render_legend(renderer)
    engine.clear_legend()

    if savedir is not None:
        save_dir = Path(savedir)
        save_dir.mkdir(parents=True, exist_ok=True)
        for idx, (spec, fig) in enumerate(zip(specs, figures), start=1):
            parts = [str(idx).zfill(3)]
            for key in spec.iterator_key:
                val = spec.context.get(key, "unknown")
                parts.append(str(val))
            filename = "_".join(parts) + ".png"
            fig.savefig(str(save_dir / filename))
            fig.clf()
        legend_fig.savefig(str(save_dir / "legend.png"))
        legend_fig.clf()

    return specs, figures, legend_fig