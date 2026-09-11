# API Reference — Engine

`geofig_engine.engine` provides the **declarative entry surface** (Phase 15):
a template-key registry (`TEMPLATES`), the canonical `render_template` entry
point, and the provider-driven `FigureGenerator` orchestrator. The engine
consumes **only** [`DataProvider`](provider.md) objects — raw frames are
wrapped for you — resolves `Layer` objects into concrete `LayerSpec`s
(applying stats and scales), builds validated
[`FigureSpec`](core.md#layers--specs) objects, and dispatches them to a
renderer.

The legacy `Dataset`-based surface is deprecated (see
[Legacy entry & deprecations](#legacy-entry--deprecations)).

## Contents

- [render_template](#render_template)
- [TEMPLATES registry](#templates-registry)
- [FigureGenerator](#figuregenerator)
- [Providers](#providers)
- [Legacy entry & deprecations](#legacy-entry--deprecations)

---

## render_template

The **canonical single-call entry point**: coerce data → provider, resolve the
template key (or object) → recipe, merge `mapping`/`coord`/`settings`
overrides, build specs, render, optionally save. Import it from the package
root (or from `geofig_engine.engine`):

```python
from geofig_engine import render_template
```

```python
def render_template(
    data: pd.DataFrame | DataProvider | np.ndarray,
    template: str | FigureTemplate | TemplateRecipe | dict,
    mapping: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
    iterators: list[DimensionIterator] | None = None,
    facet: Facet | None = None,
    coord: Coord | None = None,
    savedir: str | Path | None = None,
    renderer_name: str = "matplotlib",
) -> list[Any]:
```

| Param | Type | Description |
| --- | --- | --- |
| `data` | `pd.DataFrame \| DataProvider \| np.ndarray` | A `DataProvider` passes through; a `pd.DataFrame` is wrapped in `DataFrameProvider`; an ndarray is wrapped in a frame with **string positional columns** (`"0"`, `"1"`, …) so mappings can address it (e.g. a dendrogram linkage matrix). |
| `template` | `str \| FigureTemplate \| TemplateRecipe \| dict` | A registry **key** (resolved via `get_template`), or a `FigureTemplate` / duck-typed recipe (anything exposing `name`/`layers`/`coord`/`default_settings`) adapted via `recipe_from`. |
| `mapping` | `dict[str, Any] \| None` | Per-layer mapping override, merged over the recipe layers. Only channels the layer already binds to a **string source** are remapped, so scalar-literal channels (fixed annotation text, …) are left intact. |
| `settings` | `dict[str, Any] \| None` | User settings merged **on top of** the recipe's `default_settings`. |
| `iterators` | `list[DimensionIterator] \| None` | Optional dimension iterators for multi-figure expansion (a single iterator is also accepted). |
| `facet` | `Facet \| None` | Optional facet spec; splits the data into panels within a single figure (renderer-side). One figure per iterator combination, each containing the full facet panel grid. Defaults to `FacetNull()`. |
| `coord` | `Coord \| None` | Overrides the recipe's coord when given (e.g. `CoordGeo(crs=...)`); defaults to the recipe's. |
| `savedir` | `str \| Path \| None` | If provided, each figure is persisted as `NNN_<iterator keys>.png` (zero-padded index + context values joined by `_`) plus a `legend.png`. |
| `renderer_name` | `str` | Backend name; only `"matplotlib"` is supported. |

**Returns:** `list[Figure]` — the rendered backend figures. Specs and the
legend figure are **not** returned here; they live in the legacy path
([`render_template_legacy`](#legacy-entry--deprecations)).

**Raises:**

- `KeyError` — unknown template key (the message lists the available keys).
- `TypeError` — unsupported `data` or `template` type.
- `ValueError` — unsupported `renderer_name`, or missing required channels at
  spec-build time (informative message, not a generator-internals traceback).

```python
import pandas as pd
from geofig_engine import render_template

df = pd.DataFrame({
    "x": [1, 2, 3, 4, 5],
    "y": [2, 3, 5, 7, 11],
    "well": ["A", "A", "B", "B", "B"],
})

figures = render_template(
    data=df,
    template="bivariate",
    mapping={"x": "x", "y": "y", "color": "well"},
    settings={"figsize": (8, 6)},
)
figures[0].show()
```

---

## TEMPLATES registry

`TEMPLATES` is the exported registry mapping a **template key** to a builder
callable. Recipes returned by the builders are duck-typed — they expose
`name` / `layers` / `coord` / `default_settings` — so third-party builders
(`geochemmodel` workflows, downstream adapters) register without engine
changes.

```python
from geofig_engine import TEMPLATES, register_template, get_template
```

### `register_template(name, builder)`

Registers (or **overrides**) a builder under `name`. `name` must be a string
and `builder` must be callable — anything else raises `ValueError`. Overriding
an existing key is allowed.

### `get_template(name)`

Returns the builder registered under `name`. Unknown keys raise `KeyError`
listing the available keys.

### `TemplateRecipe` (frozen dataclass)

```python
@dataclass(frozen=True)
class TemplateRecipe:
    name: str
    layers: list[Layer]
    coord: Coord = CoordCartesian()
    default_settings: dict[str, Any] = {}
```

The canonical recipe shape returned by template builders. Missing *required
channels* are not validated here — that check happens lazily at spec-build
time.

### `recipe_from(template_or_recipe)`

Normalizes a template builder result to a recipe: `TemplateRecipe` and
duck-typed recipes pass through unchanged; `FigureTemplate` objects are
adapted (layers / coord / default settings / name are copied over). Anything
else raises `TypeError`.

### Seeded keys

| Key | Builder | Notes |
| --- | --- | --- |
| `bivariate` | `bivariate_builder` | Pipeline builder (scatter). |
| `boxplot_with_points` | `boxplot_with_points_builder` | Pipeline builder. |
| `dendrogram` | `dendrogram_builder` | Pipeline builder (takes the linkage-matrix ndarray via `data`). |
| `particle_overlay` | `particle_overlay_builder` | Pipeline builder. |
| `site_map` | `site_map_builder` | Pipeline builder (geo; use with `CoordGeo`). Default-on DEM elevation contours — terrarium tiles, lazy 10%-buffered fetch, bbox-keyed cache, old-geomapper defaults (10 m white 0.5 pt at alpha 0.6; [DEM contract](dem.md)). Contour settings are builder-level (`site_map_builder(settings={"contours": ...})`): a dict overrides `interval`/`color`/`linewidth`/`alpha` (+ `dem_source` for synthetic DEMs), `{"contours": None}` disables the layer; failures degrade to a warning + no contours. Basemap tiles configured via `settings={"basemap": ...}`. |
| `histogram`, `pie`, `radar`, `timeseries`, `isotope`, `npr_nnp`, `anp_agp`, `nagph_nag` | legacy factories adapted via `legacy_adapter` | The shipped [`geofig_engine.templates`](templates.md) factories re-registered as registry builders. |
| `piper`, `stiff` | spec builders | Keys resolve via `get_template`, but invoking them through `render_template` raises an informative `TypeError` pointing at the spec-builder route (these build `FigureSpec`s the layer→recipe pipeline cannot express — see [templates — Spec builders](templates.md#spec-builders)). |

---

## FigureGenerator

Provider-driven orchestrator and the **only** component allowed to orchestrate
multiple subsystems. It consumes only `DataProvider` (`.resolve` / `.expand` /
`.subset`) — it never touches a `Dataset` object directly; legacy `Dataset`
input reaches it through `DatasetProvider`.

```python
from geofig_engine import FigureGenerator

class FigureGenerator:
    def __init__(
        self,
        provider: DataProvider,
        layers: list[Layer],
        coord: Coord,
        facet: Facet = FacetNull(),
        scales: dict[str, Scale] | None = None,
        settings: dict | None = None,
        iterators: list[DimensionIterator] | None = None,
    ) -> None: ...
```

| Method | Signature | Description |
| --- | --- | --- |
| `build_specs` | `build_specs(self) -> list[FigureSpec]` | Expands the provider iterators (`provider.expand`) and builds one validated `FigureSpec` per iterator combination. Resolution order: expand → resolve channel selectors (`provider.resolve`) + scales → package into validated specs. Facets are stamped on each spec and applied panel-wise by the renderer (one multi-panel figure per spec). Missing required channels raise the informative spec-build error here. |
| `render` | `render(self, renderer=None, renderer_name="matplotlib") -> list[Any]` | Builds the specs and hands them to a renderer (default `MatplotlibRenderer`); returns backend figures. `renderer_name` must be `"matplotlib"` unless an explicit `renderer` is passed. |

`render_template` composes exactly this: `_wrap_data(data)` → recipe layers +
merged overrides → `FigureGenerator(...)` → `build_specs()` +
`MatplotlibRenderer().render_all(specs)` (plus a legend figure and optional
PNG persistence).

---

## Providers

Every input the engine consumes must satisfy the `DataProvider` protocol
(`columns` / `resolve` / `expand` / `subset` / `unique_values` / `dimensions`).
`render_template` coerces raw frames ndarrays for you; you only construct
providers (or implement the protocol) when you go through `FigureGenerator`
directly.

See [Providers](provider.md) for the protocol, the `DataFrameProvider` and
`DatasetProvider` implementations, and the selector forms.

---

## Legacy entry & deprecations

The former root-level names still resolve, but access to the six legacy
symbols emits an **import-time** `DeprecationWarning` (once per symbol per
process); `render_template_legacy` — the old tuple-form entry
`(specs, figures, legend_fig)` — is importable without a warning and warns at
**call time**. All are removed no earlier than geofig-engine >= 1.0.0.

| Deprecated name | Recommended replacement | Warning |
| --- | --- | --- |
| `Dataset` | raw `DataFrame` + `DataFrameProvider(df)`, or `DatasetProvider` | import-time |
| `Dimension` | geodata metadata (provider `dimensions(column)`) | import-time |
| `DimensionSelector` / `ColumnSelector` | plain column names + `provider.resolve(selector)` | import-time |
| `IteratorEngine` | `provider.expand(iterators)` | import-time |
| `FigureEngine` | `FigureGenerator` + `render_template` | import-time |
| `render_template_legacy` | `render_template` (returns `list[Figure]`) | call-time |

`geofig_engine.engine` still exports `EngineConfig` and `FigureEngine` for the
legacy path; only the root-level names route through the warning shims, so
`from geofig_engine import render_template` stays warning-free.

---

*Next: [core.md](core.md) · [provider.md](provider.md) · [templates.md](templates.md) · [renderers.md](renderers.md) · [serialize.md](serialize.md) · [data.md](data.md) · [io.md](io.md)*