# API Reference — Engine

`geofig_engine.engine` provides the **declarative entry surface** (Phase 15,
unified in 18.4): a template-key registry (`TEMPLATES`), the canonical
`render_template` entry point, and the provider-driven `FigureGenerator`
orchestrator. Phase 19 adds `build_template_specs(...)`, the shared spec-only
step that `render_template` calls before rendering. The engine consumes
**only** [`DataProvider`](provider.md) objects — raw frames are wrapped for you
— resolves registry keys to native layer (`TemplateRecipe`) or composite
(`SpecRecipe`) builders, builds validated
[`FigureSpec`](core.md#layers--specs) objects, and dispatches them to a
renderer.

The legacy `Dataset`-based surface is deprecated (see
[Legacy entry & deprecations](#legacy-entry--deprecations)).

## Contents

- [render_template](#render_template)
- [build_template_specs](#build_template_specs)
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
    template: str | FigureTemplate | TemplateRecipe | SpecRecipe | dict,
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
| `template` | `str \| FigureTemplate \| TemplateRecipe \| SpecRecipe \| dict` | A registry **key** (resolved via `get_template`), or a `FigureTemplate` / duck-typed recipe (anything exposing `name`/`layers`/`coord`/`default_settings`) adapted via `recipe_from`. A `SpecRecipe` builds `FigureSpec`s directly. |
| `mapping` | `dict[str, Any] \| None` | Per-layer mapping override, merged over the recipe layers. Only channels the layer already binds to a **string source** are remapped, so scalar-literal channels (fixed annotation text, …) are left intact. For `SpecRecipe` keys it is passed to `build_specs`. |
| `settings` | `dict[str, Any] \| None` | User settings merged **on top of** the recipe's `default_settings`. For registry keys the flat template-specific keys below are also passed to the builder. |
| `iterators` | `list[DimensionIterator] \| None` | Optional dimension iterators for multi-figure expansion (a single iterator is also accepted). **Unsupported with `SpecRecipe` keys** (`piper` / `stiff`). |
| `facet` | `Facet \| None` | Optional facet spec; splits the data into panels within a single figure (renderer-side). One figure per iterator combination, each containing the full facet panel grid. Defaults to `FacetNull()`. **Unsupported with `SpecRecipe` keys.** |
| `coord` | `Coord \| None` | Overrides the recipe's coord when given (e.g. `CoordGeo(crs=...)`); defaults to the recipe's. |
| `savedir` | `str \| Path \| None` | If provided, each figure is persisted as `NNN_<iterator keys>.png` (zero-padded index + context values joined by `_`) plus a `legend.png`. |
| `renderer_name` | `str` | Backend name; only `"matplotlib"` is supported. |

**Returns:** `list[Figure]` — the rendered backend figures. Specs and the
legend figure are **not** returned here; they live in the legacy path
([`render_template_legacy`](#legacy-entry--deprecations)).

**Raises:**

- `KeyError` — unknown template key (the message lists the available keys).
- `TypeError` — unsupported `data` or `template` type.
- `ValueError` — unsupported `renderer_name`, missing required channels at
  spec-build time (informative message, not a generator-internals traceback),
  an invalid `point_size`, or `iterators` / `facet` combined with a
  `SpecRecipe` template.

**Style knobs** — `settings={"point_size": <float>}` supplies a constant marker
size for `point`/`site_point` layers. Layers that already bind a `size` channel
win; text/annotation `size` channels are untouched. Numeric strings are
accepted so an iterator-formatted value (e.g. `"{marker_size}"`) resolves per
figure. A non-positive or non-numeric value raises `ValueError`. Tick-label
font sizes follow `tick_fontsize`, then the generic `fontsize` fallback, then
matplotlib's rcParam default (see
[core.md](core.md#axisformat-frozen-dataclass)).

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

## build_template_specs

The **spec-only** half of the declarative path. It performs the same input
coercion, template resolution, override merging, iterator expansion, and spec
validation as `render_template`, then returns the resolved specs without
instantiating a renderer, drawing a legend figure, or writing PNGs. Import it
from the package root (or from `geofig_engine.engine.api`):

```python
from geofig_engine import build_template_specs
```

```python
def build_template_specs(
    data: pd.DataFrame | DataProvider | np.ndarray,
    template: str | FigureTemplate,
    mapping: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
    iterators: list[DimensionIterator] | None = None,
    facet: Facet | None = None,
    coord: Coord | None = None,
) -> list[FigureSpec]:
```

| Param | Type | Description |
| --- | --- | --- |
| `data` | `pd.DataFrame \| DataProvider \| np.ndarray` | Same coercion as `render_template`: a `DataProvider` passes through, a `pd.DataFrame` is wrapped in `DataFrameProvider`, and an ndarray becomes a frame with string positional columns (`"0"`, `"1"`, …). |
| `template` | `str \| FigureTemplate` | A registry key resolved via `get_template`, or a `FigureTemplate` / duck-typed recipe adapted via `recipe_from`. |
| `mapping` | `dict[str, Any] \| None` | Per-layer mapping override. Native builders that consume their own mapping skip the generic override pass. |
| `settings` | `dict[str, Any] \| None` | User settings merged over the recipe defaults; also passed to key builders as flat template-specific knobs. |
| `iterators` | `list[DimensionIterator] \| None` | Optional multi-figure expansion. A single iterator is accepted. |
| `facet` | `Facet \| None` | Stamped on each spec for renderer-side panel expansion. |
| `coord` | `Coord \| None` | Overrides the recipe coord when given. |

**Returns:** `list[FigureSpec]` — one validated spec per iterator combination.
The result is the same spec list `render_template` hands to
`MatplotlibRenderer`, and is also the input to the
[dashboard wire format](serialize.md#dashboard-wire-format).

`render_template(...)` calls `build_template_specs(...)` with `data`,
`template`, `mapping`, `settings`, `iterators`, `facet`, and `coord`, then adds
renderer gating, rendering, the grouped legend figure, and optional `savedir`
persistence. There is no `savedir` or `renderer_name` argument here. The
`SpecRecipe` restrictions for `piper` / `stiff` (`iterators` and `facet` are
unsupported) are unchanged. Raises `KeyError`, `TypeError`, and `ValueError`
with the same meanings as `render_template`.

---

## TEMPLATES registry

`TEMPLATES` is the exported registry mapping a **template key** to a builder
callable. Layer builders return a duck-typed recipe — `name` / `layers` /
`coord` / `default_settings`; composite builders return a `SpecRecipe` — so
third-party builders (`geochemmodel` workflows, downstream adapters) register
without engine changes.

```python
from geofig_engine import TEMPLATES, register_template, get_template
```

Every seeded builder is called as `builder(mapping=None, settings=None,
**kwargs)`. `render_template` supplies the user `mapping` and `settings`;
callers of `get_template(key)` may also pass factory kwargs directly. Flat
template-specific settings are read from `settings` (renderer keys such as
`figsize`, `title`, and `grid` live there too). The `piper` / `stiff` spec
builders consume only `mapping` / `settings`.

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
    mapping_consumed: bool = False
```

The canonical layer-recipe shape returned by template builders. Missing
*required channels* are not validated here — that check happens lazily at
spec-build time. `mapping_consumed=True` means the builder already bound the
user mapping into its layers/stats, so the generic override pass is skipped.

### `SpecRecipe` (frozen dataclass)

```python
@dataclass(frozen=True)
class SpecRecipe:
    name: str
    default_settings: dict[str, Any]
    build_specs: Callable[
        [pd.DataFrame, dict[str, Any] | None, dict[str, Any] | None, Coord | None],
        list[FigureSpec],
    ]
```

Used for composite linked-axes templates (`piper` / `stiff`) that cannot be
flattened into layer recipes without moving data math into the renderer.
`render_template` calls `build_specs(frame, mapping, settings, coord)` with the
coerced provider frame and then reuses the normal renderer, legend, and
`savedir` path. It deliberately skips `FigureGenerator` and does **not**
support `iterators` or `facet`. The `stiff` builder requires a one-row frame
with columns `ca`, `mg`, `na_k`, `cl`, `hco3`, `so4`; the `piper` builder
requires the six standard ion columns (or the columns named by `left_tri` /
`right_tri`). See [templates — Spec builders](templates.md#spec-builders).

### `recipe_from(template_or_recipe)`

Normalizes a template builder result to a recipe: `TemplateRecipe`,
`SpecRecipe`, and duck-typed recipes pass through unchanged; `FigureTemplate`
objects are adapted (layers / coord / default settings / name are copied
over). Anything else raises `TypeError`.

### Seeded keys

| Key | Builder | Recipe | Flat template-specific settings / contract |
| --- | --- | --- | --- |
| `bivariate` | `bivariate_builder` | `TemplateRecipe` | Pipeline builder (scatter). |
| `boxplot_with_points` | `boxplot_with_points_builder` | `TemplateRecipe` | Pipeline builder. |
| `dendrogram` | `dendrogram_builder` | `TemplateRecipe` | Pipeline builder (takes the linkage-matrix ndarray via `data`). |
| `particle_overlay` | `particle_overlay_builder` | `TemplateRecipe` | Pipeline builder. |
| `site_map` | `site_map_builder` | `TemplateRecipe` | Pipeline builder (geo; use with `CoordGeo`). Default-on DEM elevation contours — terrarium tiles, lazy 10%-buffered fetch, bbox-keyed cache, white 0.5 pt at alpha 0.6 with a relief-aware default interval (`None` = at least 10 m, ~20 lines across the DEM relief; set an explicit `interval` for old-geomapper 10 m parity; [DEM contract](dem.md)). Contour settings are builder-level (`site_map_builder(settings={"contours": ...})`): a dict overrides `interval`/`color`/`linewidth`/`alpha` (+ `dem_source` for synthetic DEMs and `dem_bounds=(west, south, east, north)` to pin the DEM fetch extent), `{"contours": None}` disables the layer; failures degrade to a warning + no contours. Default-on surface-water streams — blue 0.7 pt at alpha 0.7, no legend — query the public USGS `NHDPlus_HR` REST service for the frame's unbuffered lon/lat bbox ([stream contract](streams.md)). Stream settings are builder-level (`site_map_builder(settings={"streams": ...})`): a dict overrides `color`/`linewidth`/`alpha`/`service_url`/`layer_id`/`where`/`max_pages` or injects a `streams_source(bbox)` callable (never serialized); `{"streams": None}` or `{"enabled": False}` disables the layer and skips HTTP. Failures/truncation warn and render no lines; an empty successful query is silent. Basemap tiles configured via `settings={"basemap": ...}`; declared `xlim`/`ylim` drive the tile fetch extent (with a data-window fallback). |
| `histogram` | `histogram_builder` | `TemplateRecipe` | `bins`, `density`, `cumulative`; `scales` is also accepted as a direct builder kwarg. |
| `pie` | `pie_builder` | `TemplateRecipe` | `show_percent`, `show_count`, `show_name`. |
| `radar` | `radar_builder` | `TemplateRecipe` | `fill`, `fill_alpha`, `shared_axes`. |
| `timeseries` | `timeseries_builder` | `TemplateRecipe` | No template-specific flat keys; `scales` is accepted as a direct builder kwarg. |
| `isotope` | `isotope_builder` | `TemplateRecipe` | `functions`, `auto_filter`; `scales` is accepted as a direct builder kwarg. |
| `npr_nnp` | `npr_nnp_builder` | `TemplateRecipe` | `npr_crit`, `nnp_crit`; `scales` is accepted as a direct builder kwarg. |
| `anp_agp` | `anp_agp_builder` | `TemplateRecipe` | No template-specific flat keys; `scales` is accepted as a direct builder kwarg. |
| `nagph_nag` | `nagph_nag_builder` | `TemplateRecipe` | No template-specific flat keys; `scales` is accepted as a direct builder kwarg. |
| `piper` | `piper_builder` | `SpecRecipe` | `left_tri`, `right_tri`, `title`, `labels`, `axis_label_policy`, `fontsize`, `point_size`; standard ion frame. |
| `stiff` | `stiff_builder` | `SpecRecipe` | `title`, `figsize`, `fontsize`; one-row ion frame (`ca`/`mg`/`na_k`/`cl`/`hco3`/`so4`). |

All ten legacy keys are seeded directly to native builders; `legacy_adapter`
is retained as a deprecated compatibility shim and is not used by the registry.

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

For layer recipes, `render_template` composes exactly this: `_wrap_data(data)`
→ recipe layers + merged overrides → `FigureGenerator(...)` → `build_specs()`
→ `MatplotlibRenderer().render_all(specs)` (plus a legend figure and optional
PNG persistence). `SpecRecipe` keys substitute the direct `build_specs(frame,
...)` call for the generator but then share the same renderer, legend, and
persistence path.

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

The former root-level names still resolve, but access to the legacy symbols
emits an **import-time** `DeprecationWarning` (once per symbol per process);
`render_template_legacy` and `legacy_adapter` are importable without a warning
and warn at **call time**. All are removed no earlier than geofig-engine >=
1.0.0.

| Deprecated name | Recommended replacement | Warning |
| --- | --- | --- |
| `Dataset` | raw `DataFrame` + `DataFrameProvider(df)`, or `DatasetProvider` | import-time |
| `Dimension` | geodata metadata (provider `dimensions(column)`) | import-time |
| `DimensionSelector` / `ColumnSelector` | plain column names + `provider.resolve(selector)` | import-time |
| `IteratorEngine` | `provider.expand(iterators)` | import-time |
| `FigureEngine` | `FigureGenerator` + `render_template` | import-time |
| `render_template_legacy` | `render_template` (returns `list[Figure]`) | call-time |
| `legacy_adapter` | native `*_builder` keys via `get_template` / `render_template` | call-time |

`geofig_engine.engine` still exports `EngineConfig` and `FigureEngine` for the
legacy path; only the root-level names route through the warning shims, so
`from geofig_engine import render_template` stays warning-free.

---

*Next: [core.md](core.md) · [provider.md](provider.md) · [templates.md](templates.md) · [renderers.md](renderers.md) · [serialize.md](serialize.md) · [data.md](data.md) · [io.md](io.md)*