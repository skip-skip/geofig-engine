# API Reference — Engine

`geofig_engine.engine` orchestrates everything: it expands a `Dataset` over
iterators, resolves `Layer` objects into concrete `LayerSpec`s (applying stats
and scales), builds renderer-ready [`FigureSpec`](core.md#layers--specs)
objects, and dispatches them to a renderer.

```python
from geofig_engine.engine import EngineConfig, FigureEngine, render_template
```

## Contents

- [EngineConfig](#engineconfig)
- [FigureEngine](#figureengine)
- [render_template](#render_template)

---

## EngineConfig

```python
@dataclass(frozen=True)
class EngineConfig:
    default_settings: dict[str, Any] = {}
    default_context: dict[str, Any] = {}
    strict: bool = False
```

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `default_settings` | `dict[str, Any]` | `{}` | Base settings merged under every produced `FigureSpec`. |
| `default_context` | `dict[str, Any]` | `{}` | Base iterator context values available to every produced `FigureSpec`. |
| `strict` | `bool` | `False` | Enables/disables single-value literals: when `True`, a string mapping source that is not a column raises `KeyError` instead of being treated as a constant (passed through to `resolve_source`). |

---

## FigureEngine

```python
class FigureEngine:
    def __init__(self, config: EngineConfig | None = None) -> None:
```

Creates an engine with an optional `EngineConfig`. Each engine carries its own
`LegendAccumulator` for collecting legend entries from resolved specs.

### `build_specs_from_layers(dataset, layers, settings=None, iterators=None, coord=None, facet=None, _template_name="custom")`

Builds `FigureSpec`s from `Layer` objects (the grammar-of-graphics path).

| Param | Type | Description |
| --- | --- | --- |
| `dataset` | `Dataset` | Data to visualize. |
| `layers` | `list[Layer]` | Declarative layers (see [core — Layers](core.md#layers--specs)). |
| `settings` | `dict[str, Any] \| None` | Settings merged on top of `config.default_settings`. |
| `iterators` | `Sequence[DimensionIterator] \| DimensionIterator \| None` | Iterators driving multi-figure expansion (a single iterator is accepted). |
| `coord` | `Coord \| None` | Coordinate system; defaults to `CoordCartesian()`. |
| `facet` | `Facet \| None` | Panel-splitting facet; defaults to `FacetNull()`. |
| `_template_name` | `str` | Template name stamped on the specs. |

**Returns:** `list[FigureSpec]`. Resolution per layer: (1) run the layer's
`Stat.compute` on the dataset, (2) resolve each mapping channel via
`resolve_source` (honoring `config.strict` and iterator context), (3) extract
the series (from stat output, else the original dataframe), (4) apply the
channel's `Scale.transform`, (5) package a `LayerSpec`. Legend data is
accumulated from the resolved specs.

### `build_specs_from_template(dataset, template, settings=None, iterators=None, facet=None)`

Builds `FigureSpec`s from a [`FigureTemplate`](templates.md#figuretemplate).

| Param | Type | Description |
| --- | --- | --- |
| `dataset` | `Dataset` | Data to visualize. |
| `template` | `FigureTemplate` | Template whose layers, coord, and defaults define the figure. |
| `settings` | `dict[str, Any] \| None` | Overrides merged on top of `template.default_settings`. |
| `iterators` | `Sequence[DimensionIterator] \| DimensionIterator \| None` | Optional iterators. |
| `facet` | `Facet \| None` | Optional facet. |

**Returns:** `list[FigureSpec]`. Delegates to `build_specs_from_layers` with
the template's `coord`, its name as `_template_name`, and merged settings.

### `render_specs(specs, renderer)`

Renders an existing list of `FigureSpec`s.

| Param | Type | Description |
| --- | --- | --- |
| `specs` | `list[FigureSpec]` | Specs to render; validated first (raises on empty unless empty is allowed — empty lists are accepted). |
| `renderer` | `BaseRenderer` | Must not be `None`. |

**Returns:** `list[Any]` of backend figure objects (via `renderer.render_all`).

### `render_spec(spec, renderer)`

Renders a single `FigureSpec`.

**Returns:** a backend figure object.

### `render_legend(renderer)`

Renders the accumulated legend for everything the engine has built so far.

| Param | Type | Description |
| --- | --- | --- |
| `renderer` | `BaseRenderer` | Must support a `render_legend(accumulator)` method. |

**Returns:** a backend figure object. **Raises:** `ValueError` if `renderer`
is `None`; `NotImplementedError` if the renderer lacks `render_legend`.

### `clear_legend()`

Clears the engine's `LegendAccumulator`.

---

## `render_template`

The simplified single-call entry point: engine → build specs → render →
optionally save.

```python
def render_template(
    dataset: Dataset,
    template: FigureTemplate,
    iterators: Sequence[DimensionIterator] | DimensionIterator | None = None,
    settings: dict[str, Any] | None = None,
    facet: Facet | None = None,
    renderer_name: str = "matplotlib",
    savedir: str | Path | None = None,
) -> tuple[list, list, Any]:
```

| Param | Type | Description |
| --- | --- | --- |
| `dataset` | `Dataset` | The data to visualize. |
| `template` | `FigureTemplate` | Template defining layers, coord, defaults. |
| `iterators` | `Sequence[DimensionIterator] \| DimensionIterator \| None` | Optional iterators for multi-figure expansion. |
| `settings` | `dict[str, Any] \| None` | Override settings merged on top of template defaults. |
| `facet` | `Facet \| None` | Optional facet spec for subplot splitting. |
| `renderer_name` | `str` | Backend name; only `"matplotlib"` is supported. |
| `savedir` | `str \| Path \| None` | If provided, renders each figure as `NNN_<iterator keys>.png` (zero-padded index + context values joined by `_`) and a `legend.png`. |

**Returns:** `(specs, figures, legend_fig)` — the list of `FigureSpec` objects,
the list of rendered matplotlib figures, and the accumulated legend figure (an
empty figure if there are no legend entries).

**Raises:** `ValueError` if `renderer_name` is not `"matplotlib"`.

```python
from geofig_engine.templates import bivariate

specs, figures, legend = render_template(
    dataset=df,
    template=bivariate(mapping={"x": "x", "y": "y", "color": "well"}),
    settings={"figsize": (8, 6)},
)
```

---

*See [core.md](core.md) for the spec/layer model, [templates.md](templates.md)
for available templates, and [renderers.md](renderers.md) for the renderer
contract.*