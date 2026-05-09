import curses
from pathlib import Path
from typing import Any

from geofig_cli.ui import center_text, message, safe_addstr, text_input
from geofig_engine.core import dataset
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.engine import FigureEngine
from geofig_engine.renderers import MatplotlibRenderer

from geofig_cli.selectors import build_dimension_iterator
from geofig_cli.state import ConfigState
from geofig_engine.templates.isotope import IsotopeTemplate


def materialize_mappings(state: ConfigState) -> dict[str, Any]:
    return {
        key: mapping.value_resolved
        for key, mapping in state.mappings.items()
    }


def materialize_iterators(
    state: ConfigState,
    dataset: Dataset,
) -> list[DimensionIterator]:
    return [
        build_dimension_iterator(iterator, dataset)
        for iterator in state.iterators
    ]


def render_to_folder(
    dataset: Dataset,
    template: Any,
    state: ConfigState,
    outdir: Path,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    renderer = MatplotlibRenderer()
    engine = FigureEngine()

    settings = dict(state.settings)

    if state.layer_settings:
        settings["layer_settings"] = dict(state.layer_settings)

    engine.render_and_save(
        dataset=dataset,
        template=template,
        mappings=materialize_mappings(state),
        iterators=materialize_iterators(state, dataset),
        renderer=renderer,
        outdir=str(outdir),
        settings=settings,
    )
def draw_progress_bar(
    stdscr,
    y: int,
    x: int,
    width: int,
    current: int,
    total: int,
    label: str = "",
) -> None:
    height, screen_width = stdscr.getmaxyx()

    if total <= 0:
        percent = 1.0
    else:
        percent = current / total

    percent = max(0.0, min(1.0, percent))

    usable_width = min(width, screen_width - x - 1)
    bar_width = max(10, usable_width - 12)

    filled_width = int(bar_width * percent)
    empty_width = bar_width - filled_width

    bar = "[" + "#" * filled_width + "-" * empty_width + "]"
    percent_text = f"{percent * 100:5.1f}%"

    safe_addstr(stdscr, y, x, " " * usable_width)
    safe_addstr(stdscr, y, x, f"{bar} {percent_text}")

    if label and y + 2 < height:
        safe_addstr(stdscr, y + 2, x, " " * usable_width)
        safe_addstr(stdscr, y + 2, x, label)

def render_figures(
    stdscr,
    dataset: Dataset,
    template: Any,
    state: ConfigState,
) -> None:
    outdir_raw = text_input(
        stdscr,
        "Render Figures",
        "Output directory",
    )

    if not outdir_raw:
        return

    outdir = Path(outdir_raw)
    outdir.mkdir(parents=True, exist_ok=True)

    renderer = MatplotlibRenderer()
    engine = FigureEngine()

    stdscr.clear()
    center_text(stdscr, 2, "Building figure specs...", curses.A_BOLD)
    stdscr.refresh()

    settings = dict(state.settings)

    if state.layer_settings:
        settings["layer_settings"] = dict(state.layer_settings)
    template = apply_layer_options_to_template(template, state)

    specs = engine.build_specs(
        dataset=dataset,
        template=template,
        mappings=materialize_mappings(state),
        iterators=materialize_iterators(state, dataset),
        settings=settings,
    )

    total = len(specs)
    if total == 0:
        message(stdscr, "No figures were generated. Check mappings, iterators, and settings.")
        return

    stdscr.clear()
    center_text(stdscr, 2, "Rendering figures...", curses.A_BOLD)

    height, width = stdscr.getmaxyx()

    draw_progress_bar(
        stdscr=stdscr,
        y=5,
        x=4,
        width=width - 8,
        current=0,
        total=total,
        label=f"Preparing to render {total} figure(s)...",
    )

    stdscr.refresh()

    for i, spec in enumerate(specs, start=1):
        label = f"Rendering figure {i} of {total}"

        draw_progress_bar(
            stdscr=stdscr,
            y=5,
            x=4,
            width=width - 8,
            current=i - 1,
            total=total,
            label=label,
        )

        stdscr.refresh()

        fig = renderer.render(spec)
        filename = f"{template.name}_{i - 1}.png"
        if hasattr(fig, "figname") and fig.figname:
            filename = f"{fig.figname}.png"
        fig.savefig(outdir / filename)

        draw_progress_bar(
            stdscr=stdscr,
            y=5,
            x=4,
            width=width - 8,
            current=i,
            total=total,
            label=f"Saved {filename}",
        )

        stdscr.refresh()

    message(stdscr, f"Done. Output saved to: {outdir}")

def apply_layer_options_to_template(template: Any, state: ConfigState) -> Any:
    """
    Apply toggled layer options back to the template before rendering.

    For isotope templates, selected MeteoricWaterLines become template.lines.
    """
    if isinstance(template, IsotopeTemplate):
        selected_lines = [
            option.value
            for option in state.layer_options
            if option.key == "lines" and option.selected
        ]
        return IsotopeTemplate(selected_lines)

    return template