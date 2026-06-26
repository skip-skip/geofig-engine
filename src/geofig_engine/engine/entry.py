"""
Simplified entry point for FigEngine.

Provides a single ``render_template()`` function that wraps the common
pattern of: engine → build_specs_from_template → render → save.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.engine.generator import FigureEngine


def render_template(
    dataset: Dataset,
    template: FigureTemplate,
    iterators: Sequence[DimensionIterator] | DimensionIterator | None = None,
    settings: dict[str, Any] | None = None,
    renderer_name: str = "matplotlib",
    savedir: str | Path | None = None,
) -> tuple[list, list, Any]:
    """Build, render, and optionally save figures from a template.

    Args:
        dataset: The data to visualize.
        template: A ``FigureTemplate`` defining layers, coord, defaults.
        iterators: Optional iterators for multi-figure expansion.
        settings: Override settings merged on top of template defaults.
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
