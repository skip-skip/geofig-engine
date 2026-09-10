# API Reference — Renderers

Renderers consume fully resolved [`FigureSpec`](core.md#layers--specs) objects
and produce backend-specific visual artifacts. The engine dispatches to a
renderer through [`BaseRenderer`](#baserenderer); the shipped matplotlib
backend is [`MatplotlibRenderer`](#matplotlibrenderer).

```python
from geofig_engine.renderers import BaseRenderer, MatplotlibRenderer
from geofig_engine.renderers.matplotlib.legend import (
    LegendEntry, LegendGroup, LegendAccumulator,
    build_dimension_legend, render_legend_figure,
)
```

## Contents

- [BaseRenderer](#baserenderer)
- [MatplotlibRenderer](#matplotlibrenderer)
- [Legend API](#legend-api)

---

## BaseRenderer

Abstract base class defining the renderer contract.

### `render(spec)` *(abstract)*

`render(self, spec: FigureSpec) -> Any` — renders a single `FigureSpec` and
returns a backend object (for matplotlib, a `plt.Figure`).

### `render_all(specs)`

`render_all(self, specs: Iterable[FigureSpec]) -> list[Any]` — renders specs
in order. Default implementation loops `self.render`.

### `close()`

Optional cleanup hook for stateful renderers; no-op by default.

### `supports(spec)`

`supports(self, spec: FigureSpec) -> bool` — reports whether the renderer can
handle a spec. Base returns `True`.

---

## MatplotlibRenderer

```python
class MatplotlibRenderer(BaseRenderer)
```

The bundled matplotlib backend. Renders point, line, function-line, bar, area,
polygon, ribbon, text, errorbar, box, violin, step-line, hspan, vspan, rect,
and abline geoms (geometry handled in `renderers/matplotlib/handlers.py`).
Also renders linked-axes [`FigureSpec`](core.md#links) children with
`LinkTransform` placement and the unified custom cartesian/ternary/polar frame
pipeline driven by `AxisFormat` (see [core — Axis & plot settings](core.md#axis--plot-settings)).

### `render(spec)`

`render(self, spec: FigureSpec) -> plt.Figure` — renders one spec. Singleton
framed figures, plain figures, faceted figures, and linked-axis parents
(with `children`) are all supported; the renderer inspects the spec (layers,
`coord`, `children`, facets) to choose the path.

### `render_legend(legend_data, fontsize=9)`

`render_legend(self, legend_data: LegendAccumulator, fontsize: float = 9) -> plt.Figure`
— renders the accumulated legend figure (delegates to `render_legend_figure`).

### `supports(spec)`

Returns `True` for specs whose `template_name` is in
`("test", "bivariate", "isotope", "timeseries")`, or whose layers' geoms (or,
for linked-axis parents, children's layers' geoms) all have registered
handlers. Otherwise `False`.

```python
from geofig_engine.templates import bivariate
from geofig_engine.engine import render_template

specs, figures, legend = render_template(dataset=df, template=bivariate(...))
```

---

## Legend API

Legend construction is separate from plotting: it inspects a resolved spec's
visual mapping (`color`/`marker`/`style` and `subgroup` channels) and builds
per-column groups of entries.

### `VISUAL_CHANNELS`

`("color", "marker", "style")` — the channels observed by the legend.

### `LegendEntry` (frozen dataclass)

```python
@dataclass(frozen=True)
class LegendEntry:
    label: str
    marker: str = "o"
    color: str = "#888888"
    linestyle: str = "-"
    alpha: float = 1.0
    subgroup: str | None = None
```

### `LegendGroup` (frozen dataclass)

```python
@dataclass(frozen=True)
class LegendGroup:
    column: str
    entries: list[LegendEntry] = []
```

| Method | Signature | Returns |
| --- | --- | --- |
| `set_order` | `set_order(labels)` | New group with entries reordered by `labels` (unknown labels sort last). |
| `filter_entries` | `filter_entries(keep_labels=None, drop_labels=None)` | New group keeping only `keep_labels` and/or dropping `drop_labels`. |

### `build_dimension_legend(data, color_col=None, marker_col=None, linetype_col=None, subgroup_col=None, palette=DEFAULT_PALETTE, markers=DEFAULT_MARKERS)`

Builds legend groups directly from a dataframe and column names.

| Param | Type | Description |
| --- | --- | --- |
| `data` | `pd.DataFrame` | Source dataframe. |
| `color_col` | `str \| None` | Column driving color entries. |
| `marker_col` | `str \| None` | Column driving marker entries. |
| `linetype_col` | `str \| None` | Column driving linestyle entries. |
| `subgroup_col` | `str \| None` | Subgroup label for entries (used when a single unique subgroup corresponds to a value). |
| `palette` | `tuple[str, ...]` | `DEFAULT_PALETTE` by default (see [IO — markers](io.md#markers)). |
| `markers` | `tuple[str, ...]` | `DEFAULT_MARKERS` by default. |

**Returns:** `list[LegendGroup]` — one group per non-None present column.

### `LegendAccumulator`

Collects legend data incrementally as specs are built/rendered.

| Method | Signature | Description |
| --- | --- | --- |
| `add_from_spec` | `add_from_spec(spec: FigureSpec)` | Scans `spec.layers` visual mappings for color/marker/style series, dedupes per column, and merges entries into groups. |
| `groups` | property | `list[LegendGroup]` in insertion order. |
| `clear` | `clear()` | Resets the accumulator. |

### `render_legend_figure(legend_data, figsize=(6, 4), fontsize=9)`

`render_legend_figure(legend_data: LegendAccumulator, figsize=(6, 4), fontsize=9) -> plt.Figure`
— renders one legend column per group. Group headers are bold; subgroup
headers are semibold and slightly smaller. Returns a small empty figure when
there are no groups.

---

*Next: [core.md](core.md) · [engine.md](engine.md) · [templates.md](templates.md) · [serialize.md](serialize.md) · [data.md](data.md) · [io.md](io.md)*