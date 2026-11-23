# FigEngine Architecture

## Overview

FigEngine is a declarative visualization system built around the **Grammar of Graphics** (GoG) – a formal framework where statistical graphics are composed from independent, reusable components.

### Position in the Pipeline

FigEngine is **Stage 4** (Visualization) of the pipeline defined in
`../PIPELINE_MODULES.md`:

```
Data Ingestion → Normalization / QA/QC → Modeling → Visualization
    (geodata)        (geodata)          (geochemmodel)   (geofig-engine)
```

Components that used to live here — `Dataset`, `Dimension`, `DimensionSelector`,
`IteratorEngine` — **moved to `geodata`** and remain in figEngine only as
**deprecated shims** (kept for backward compatibility with existing figEngine
scripts; scheduled for removal in the next major version).

**Dependency rules (unchanged and enforced):**

1. `geofig_engine` **never imports** `geodata` (or `geochemmodel`).
2. `geofig_engine` consumes upstream carriers **duck-typed** through a structural
   **`DataProvider` Protocol** defined in-geom-engine (`utils/typing.py`).
3. `geochemmodel` consumes `geodata`, and imports `geofig_engine` **lazily** in
   `ModelResult.render()` only. `geodata` imports neither engine nor model.

```python
# Structural provider contract (duck-typed; no geodata import)
class DataProvider(Protocol):
    @property
    def columns(self) -> list[str]: ...
    def resolve(self, selector) -> list[str]: ...        # DimensionSelector resolution
    def expand(self, iterators: list | None = None) -> list[tuple[pd.DataFrame, dict]]: ...
    def subset(self, *, columns=None, **filters) -> "DataProvider": ...
    def unique_values(self, column: str) -> list: ...
    def dimensions(self, column: str) -> dict: ...        # column metadata labels
```

Entry points:

- `render_template(data: DataFrame | DataProvider, template=<key> | FigureTemplate,
  mapping=..., settings=..., iterators=..., facet=..., coord=...,
  savedir=...) -> list[Figure]` — the **one canonical entry point**. All
  inputs after `data`/`template` are optional (defaults live in the template
  recipe and are applied lazily). Raw `pandas.DataFrame` is accepted and
  wrapped by `DataFrameProvider`, so figEngine stays usable **standalone**
  (no geodata/geochemmodel, no modeling stage) for basic analysis.
- `render_template_legacy(dataset=Dataset, template=FigureTemplate, ...) ->
  (specs, figures, legend_fig)` — the former entry, retained verbatim; warns
  on call (`DeprecationWarning`) and routes new work to `render_template`.
- `TEMPLATES` (exported registry) + `register_template(name, builder)` +
  `get_template(name)` — template keys resolve to builders; consumers
  (e.g. `geochemmodel.results`) can register/override without engine changes.
- `DataProvider` Protocol + `DataFrameProvider` + `DatasetProvider` (defined
  in `geofig_engine/provider.py`).
- `FigureGenerator` (lower-level, provider-driven; `FigureEngine` remains a
  deprecated shim).

### Implementation status (documented plan ahead of code)

The API changes below were the **agreed target design**, captured ahead of
implementation so downstream packages (`geochemmodel`, workflows) could be
written against the contract. Every M1 row is now **shipped in v0.2.0**:

| Piece | Status |
| --- | --- |
| `DataProvider` / `DataFrameProvider` / `DatasetProvider` | implemented (provider.py) |
| New `render_template` (figures return, optional args) | implemented (engine/api.py) |
| `render_template_legacy` (old entry, warns) | implemented (engine/api.py) |
| `TEMPLATES` registry + `register_template` | implemented |
| `FigureGenerator` (provider-driven) | implemented (engine/generator.py) |
| Geoms: site point, label, boundary, annotation-inset, image | implemented |
| `CoordGeo` + `[geo]` extra | implemented |
| Templates `dendrogram`, `site_map`, `particle_overlay` | implemented |
| Deprecated shims with import-time warnings | implemented (deprecated.py) |
| Basemap tiles (site_map default imagery, opt-out) | implemented (wp14 pull-forward) |
| DEM contour (site_map, 18.2) / stream geoms | both implemented (streams shipped in 18.3) |

### Core GoG Concepts

1. **Tidy dataset**
2. **Semantic dimension metadata**
3. **Aesthetic mappings + Scales** (data → visual domain)
4. **Geoms** (visual marks – points, lines, bars, etc.)
5. **Stats** (statistical transformations – identity, bin, smooth, etc.)
6. **Coord** (coordinate system – Cartesian, polar, geo)
7. **Facet** (subplot splitting)
8. **Layer** (Geom + Stat + mapping bound to data)
9. **Rendering backends**

### Pipeline

```
DataProvider  (DataFrame | GeoData | ModelResult table view)
→ resolve selectors / columns
→ provider.expand(iterators)      (multi-figure contexts; delegated to provider)
→ Facet (panels within a figure)
→ Layers (Geom + Stat + mapping)
→ Scale resolution (data → visual domain)
→ Coord transform
→ FigureSpec
→ Renderer
→ Figures
```

---

## Core Design Principles

### 1. Strict Separation: Data → Spec → Render

- Data is never mutated by visualization logic
- Dimension metadata is independent of rendering
- Layers define structure, not execution
- Scales are pure transformations (data domain → visual domain)
- Renderers only draw (no business logic, no data transforms)

### 2. Declarative Configuration

Figures are defined by *what they represent*, not *how to draw them*.

```python
layer = Layer(
    geom=GeomPoint(),
    stat=StatIdentity(),
    mapping={
        "x": DimensionSelector(analyte=True),
        "y": "chem1",
        "color": "group",
    },
    scales={
        "x": ScaleContinuous(),
        "y": ScaleContinuous(),
        "color": ScaleOrdinal(palette="Set1"),
    },
)
```

### 3. Extensibility

The system must support:

- new Geom types (geometric marks)
- new Stat transformations
- new Coord systems
- new Facet strategies
- new Scale types
- new rendering backends

Without modifying core logic.

---

## Core Components

---

### 1. DataProvider (input abstraction)

The single input abstraction for the engine. Consumers pass a `DataProvider`
(often `GeoData.provider_for(data_ref)` from `geodata`, or the in-engine
`DataFrameProvider` wrapper around raw data). The engine never imports the
provider's package.

```python
DataProvider:
    columns: list[str]
    resolve(selector) -> list[str]            # DimensionSelector → columns
    expand(iterators) -> list[(subset_df, context)]
    subset(*, columns=None, **filters) -> DataProvider
    unique_values(column) -> list
    dimensions(column) -> dict                # column metadata labels
```

Rules:
- the engine calls `provider.expand(...)` and never re-implements iterator expansion
- `subset()` returns a view; producers decide whether views are lazy or copies

`DataFrameProvider` wraps a plain `DataFrame`: `resolve` is identity-only,
`dimensions` return `{}`, `expand` starts from a single context. This preserves
standalone figEngine usage.

### 1a. Declarative API surface (implemented in v0.2.0)

Post-implementation, the engine exposes a single declarative call plus an
extensible registry over one input abstraction:

```python
from geofig_engine import render_template, DataFrameProvider, register_template

# basic standalone analysis — no modeling stage, no geodata
figs = render_template(DataFrameProvider(df), template="bivariate",
                       mapping={"x": "SO4", "y": "Cl", "color": "group"})

# pipeline entry (geochemmodel.ModelResult.render) — identical call shape
figs = render_template(
    data=dl.provider_for("long") | result.tables["particles"],
    template=enc.template,           # "dendrogram" | "site_map" | "particle_overlay" | ...
    mapping=enc.mapping,
    settings=enc.settings,
    iterators=enc.iterators,
    facet=enc.facet,
    coord=enc.coord,
)

# extend the registry (projects, geochemmodel adapter, workflows)
register_template("isotope_matrix", builder)
```

Rules:

- **Input coercion**: `data` accepts a `DataProvider` (passed through), a raw
  `pd.DataFrame` (wrapped in `DataFrameProvider`), or an ndarray (wrapped in a
  frame with positional string columns `"0"`, `"1"`, ... — e.g. dendrogram
  linkage matrices).
- **Template recipe**: a builder returns a duck-typed recipe
  (`layers`, `coord`, `default_settings`, `name`); `FigureTemplate` objects
  are adapted to the same shape so the legacy template set keeps working.
- **All args optional**: `mapping`, `settings`, `iterators`, `facet`,
  `coord` default to `None`; defaults resolve from the template's recipe.
  Missing *required channels* are checked lazily at spec-build time, giving
  each template a usable no-argument behavior.
- **One return**: `render_template(...)` returns `list[Figure]`; `savedir=`
  persists them. The old `(specs, figures, legend_fig)` tuple form is
  `render_template_legacy(...)`, deprecated.
- **`FigureGenerator`** consumes only `DataProvider` and calls
  `provider.resolve/expand/subset`; it shares the Layer→LayerSpec resolution
  helpers extracted from `FigureEngine` (legacy engine untouched, behavior
  unchanged). `Dataset` reaches the same generator through `DatasetProvider`.

#### Deprecation shims (`geofig_engine/deprecated.py`, `__init__.py`)

Legacy symbols are re-exported with **import-time `DeprecationWarning`**
pointing at the replacement. `geofig_cli` is untouched.

| Legacy | Recommended replacement |
| --- | --- |
| `Dataset` | `DataFrameProvider(df)` / `GeoData.provider_for(data_ref)` / `DatasetProvider` |
| `Dimension` | `geodata.core.dimension.Dimension` (metadata only) |
| `DimensionSelector` / `ColumnSelector` | plain column names + `provider.resolve(selector)` |
| `IteratorEngine` / `expand()` | `provider.expand(iterators)` |
| `FigureEngine` | `FigureGenerator` + `render_template` |
| `render_template(...)` old tuple return | `render_template_legacy(...)` → new `render_template(...)` |

New `__all__` splits **public** (`render_template`, `register_template`,
`TEMPLATES`, `DataProvider`, `DataFrameProvider`, `FigureGenerator`,
`FigureSpec`, ...) from **deprecated** (`Dataset`, `Dimension`,
`DimensionSelector`, `ColumnSelector`, `FigureEngine`, ...).

### 2. Dataset, Dimension (deprecated shims)

`Dataset` (dataframe + key_column + dimensions) and `Dimension` (name + labels)
moved to `geodata` (see `geodata/ARCHITECTURE.md`). figEngine keeps
re-exports for backward compatibility; they are **not** used by the engine
internals and will be removed in the next major version.

- `Dataset` → use `GeoData` / `DataProvider`
- `Dimension` → `geodata.core.dimension.Dimension`
- Labels remain purely metadata and must never encode visualization behavior.

### 3. DimensionSelector (shim)

Resolution moved to the provider (`provider.resolve(selector)`); figEngine's
local implementation is retained only as a deprecated shim.

```python
DimensionSelector:
    resolve(provider) -> list[str]   # now delegated to provider.resolve
```

Supports:
- single column: `"chem1"`
- attribute-based: `{"analyte": True}`
- explicit list: `["chem1", "chem2"]`

### 4. Attribute Mapping & Scale

**AttributeMapping** maps data (or constants) to visual channels declaratively.
**Scale** transforms data-domain values into visual-domain values (e.g., position, color, size).

```python
AttributeMapping:
    target: str          # "x", "y", "color", "size", "shape"
    source: SourceType   # DimensionSelector, str, list[str], constant
    scale: Scale         # how to map data → visual

Scale:
    transform(values) -> visual_values    # e.g., linear, log, ordinal
    invert(visual_values) -> values       # inverse transform (for interactivity)
```

Responsibilities:
- **AttributeMapping**: stores *what* maps to *which* channel
- **Scale**: stores *how* the mapping is computed (linear, log, ordinal palette, etc.)
- Resolution order: resolve selectors → extract data → apply scales → produce visual values

Examples:
| Channel | Source | Scale |
|---------|--------|-------|
| `x` | `DimensionSelector(analyte=True)` | `ScaleContinuous()` |
| `y` | `"chem1"` | `ScaleContinuous()` |
| `color` | `"group"` | `ScaleOrdinal(palette="Set1")` |
| `color` | `"blue"` | `ScaleConstant()` |

AttributeMapping must NOT:
- access dataset directly
- perform rendering logic

---

### 5. Geom (Geometric Object)

Defines the type of visual mark to draw.

```python
Geom:
    name: str
    required_channels: list[str]    # e.g., ["x", "y"]
    optional_channels: list[str]    # e.g., ["color", "size", "alpha"]
```

Built-in Geoms:
- `GeomPoint` – scatter plot marks
- `GeomLine` – connected line segments
- `GeomBar` – bar/column marks
- `GeomArea` – filled area under a line
- `GeomRibbon` – confidence band / envelope
- `GeomText` – text labels
- `GeomPath` – arbitrary path (incl. dissolved/variogram-style boundaries from `geochemmapper.py`)
- `GeomErrorbar` – error bars
- `GeomSmooth` – smoothed conditional mean (composition of StatSmooth + GeomRibbon/Line)
- `GeomPolygon` – filled/closed polygons (Stiff diagram frames)

**New channels** (`geometry`, `image`) support the site-map and per-photo-SEM
additions:

- `geometry` channel: geometry data (point coords, polygons, shapefile/geojson
  boundaries, stream lines, contours) attached to layers.
- `image` channel: image-array sources for insertion into a figure data-space
  (e.g., `GeomImage` for particle insets; uses the `matplotlib.offsetbox`
  OffsetImage idiom already used by `geochemmapper.add_figure_callouts`).

A suite of **geo-allied geoms** (nine, ported from `geochemmapper.py` idioms) is
added for Stage-4 spatial/particle output:

| Geom | Purpose |
| --- | --- |
| site/resource point geoms | categorical + gradient point layers (site symbols) |
| label geom | location labels (incl. callout/stagger layout, `add_labels`) |
| boundary geom | shapefile/geojson/kmz polygon + line boundaries |
| streams geom ✅ | USGS `NHDPlus_HR` stream polylines (shipped with `site_map`, Phase 18.3) |
| contour geom ✅ | DEM contour lines (shipped with `site_map`, Phase 18.2) |
| annotation/inset geom | figure callouts + OffsetImage particle insets |
| image geom | raw-image overlays in data space |

Existing rendering must keep working for all prior figure templates (Piper,
Stiff, bivariate, boxplot, timeseries, radar, pie, isotope, NAGP/ANP, NPR/NNP,
histogram).

Geoms must:
- declare required and optional channels
- not resolve DimensionSelectors
- not perform data transformation
- only define *what* to draw

---

### 6. Stat (Statistical Transformation)

Transforms data before visual encoding.

```python
Stat:
    name: str
    compute(data, mapping) -> pd.DataFrame   # transformed data
```

Built-in Stats:
- `StatIdentity` – pass-through (no transformation)
- `StatBin` – bin continuous values into intervals
- `StatCount` – count occurrences (for bar charts)
- `StatSmooth` – smoothing / regression (LOESS, linear, etc.)
- `StatSummary` – summary statistics (mean, median, quartiles)
- `StatDensity` – kernel density estimate
- `StatEcdf` – empirical cumulative distribution

Stats must:
- be pure functions of data
- preserve column names for channel mapping
- not depend on rendering

---

### 7. Layer

A Layer binds a Geom, a Stat, mappings, and scales into a drawing unit.

```python
Layer:
    geom: Geom
    stat: Stat
    mapping: dict[str, SourceType]       # channel → data source
    scales: dict[str, Scale]            # channel → scale (optional; inferred if absent)
    data: pd.DataFrame | None           # override dataset for this layer (optional)
```

A figure may contain **multiple layers**, each independently specifying *what* to draw, *how* to transform it, and *which* scales to use. Layers are drawn in order (later layers are drawn on top).

Layer resolution pipeline:
1. Resolve DimensionSelectors → column names
2. Apply Stat transformation → transformed DataFrame
3. Extract data series per channel
4. Apply Scale → visual-domain values
5. Package into LayerSpec for renderer

---

### 8. Coord (Coordinate System)

Transforms visual-domain values to screen space.

```python
Coord:
    name: str
    transform(visual_values) -> screen_coords
    aspect_ratio: float | None
```

Built-in Coords:
- `CoordCartesian` – standard x/y plane (default)
- `CoordPolar` – polar coordinates (radial + angular)
- `CoordFlipped` – swapped x/y axes
- `CoordFixed` – fixed aspect ratio
- `CoordGeo` – **new** geographic coordinate system: lon/lat → projected CRS,
  bounds/margins, axis formatting (degrees), basemap support (optional `[geo]`
  extra). Used by `site_map` and `cluster_map` templates.

Advanced figures (e.g. Piper, Stiff) are ordinary cartesian/ternary figures: they
compose `CoordCartesian` / `TernaryCoord` with nested `FigureSpec` children or
settings-driven frames. The Stiff diagram is a cartesian template (`CoordCartesian`
with named/absolute tick labels and a `GeomPolygon` layer); there are no dedicated
coord subclasses for it. Dependency rules are unchanged.

Coords must:
- operate on pre-scaled visual values
- not depend on data or rendering backend
- be composable with facets

---

### 9. Facet (Subplot Splitting)

Divides data into subsets, each rendered as a separate subplot.

```python
Facet:
    name: str                    # "wrap", "grid", "null"
    by: DimensionSelector        # dimension(s) to split by
    scales: "fixed" | "free"     # share scales across facets
```

Built-in Facets:
- `FacetNull` – single plot (default)
- `FacetWrap` – split by one dimension, wrap into rows/cols
- `FacetGrid` – split by two dimensions (rows × cols)

Facets replace some uses of the IteratorEngine. The key difference:
- **Facet**: multiple panels within a single figure (shared axes/layout)
- **IteratorEngine**: multiple *independent* figures (separate files, contexts)

---

### 10. FigureSpec

Concrete, fully resolved plotting instruction – the contract between system and renderer.

```python
FigureSpec:
    data: pd.DataFrame
    layers: list[LayerSpec]       # resolved layers with visual-domain values
    coord: Coord
    facet: Facet
    scales: dict[str, Scale]      # global scale registry
    settings: dict                # title, figsize, theme, etc.
    context: dict                 # iterator / facet context values
```

`LayerSpec` is the resolved form of a Layer:

```python
LayerSpec:
    geom: Geom
    stat: Stat                   # already applied; included for renderer metadata
    visual_mapping: dict[str, Any]  # channel → concrete visual values
```

This is the final, renderer-agnostic spec. Backends consume this to produce figures.

---

### 11. IteratorEngine (deprecated shim)

Multi-figure expansion **moved to the producer** (`provider.expand(iterators)`).
`geofig-engine` calls `provider.expand(...)` when iterators are present and never
expands data itself. The old `IteratorEngine` class remains as a deprecated shim
wrapping `provider.expand` on the internal `Dataset`; it is not used by newer
entry points (`render_template`).

```python
provider.expand(iterators) -> list[(subset_df, context)]
```

Where:
- `subset_df` is a filtered view of the dataset
- `context` is a dict of iterator values (e.g., `{"analyte": "chem2"}`)

Use for: generating one figure *per* combination of values (e.g., one plot per analyte).
Use Facet for: multiple panels *within* a single figure.

Expansion must:
- not modify source data
- not depend on templates, layers, or mappings

---

### 12. FigureGenerator (Orchestrator)

Top-level execution/render driver.

```python
FigureGenerator:
    provider: DataProvider        # DataFrame or upstream provider view
    layers: list[Layer]
    coord: Coord
    facet: Facet
    scales: dict[str, Scale]      # optional global defaults
    settings: dict
    iterators: list[DimensionIterator]  # optional (for multi-figure output)

Responsibilities:
- resolve dimension selectors (via provider.resolve)
- expand iterators (via provider.expand) for multi-figure
- apply facets (for multi-panel)
- resolve scales (data → visual domain)
- build FigureSpec(s)
- send to renderer
```

`render_template(data, ..., template=...)` sits **above** FigureGenerator:
it resolves a template key against a small registry of template builders
(bivariate, boxplot_with_points, dendrogram, site_map, particle_overlay, plus the
existing Piper/Stiff/radar/timeseries/isotope/etc. builders), then composes the
`FigureGenerator` from the builder's Layer/Coord/Facet/Scale recipe.

FigureGenerator is the ONLY component allowed to orchestrate multiple subsystems.

---

### 13. Renderer

Backend-specific drawing logic.

```python
Renderer:
    render(spec: FigureSpec) -> Figure
    render_all(specs: list[FigureSpec]) -> list[Figure]
```

Examples:
- `MatplotlibRenderer`
- `PlotlyRenderer` (future)

Belongs to the Matplotlib backend:

- **grouped, titled legends** (`LegendGroup`, `LegendAccumulator` in
  `renderers/matplotlib/legend.py`) — used by `site_map`/`particle_overlay` to
  group legend items (Boundaries / Facilities / Sample Points / QA overlay) and
  by templated map/particle figures generally.
- **geometry/image handlers** (`handlers.py`) for the new spatial geoms and
  OffsetImage insets (particle overlays).

Renderers must:
- consume only FigureSpec (no access to Dataset, Dimensions, etc.)
- not perform data transformations or scale resolution
- handle all Geom types they support (return NotImplemented for unsupported)
- respect Coord and Facet

---

## Implementation Roadmap

### Focus — interoperability (next major development target → v0.2.0)

geofig-engine is the downstream consumer (workflows W1/W2 in
`../PIPELINE_MODULES.md`). The shared contracts are:

1. **Data** — render entries accept a `DataProvider` (geodata views satisfy it;
   `DataFrameProvider` for standalone frames). No geodata/geochemmodel import.
2. **Spec** — `TEMPLATES` registry resolves both template keys and keys emitted by
   `geochemmodel.VisualizationEncoding`; encode extra `[geo]` handling.
3. **Render** — canonical `render_template(data, template=<key>|FigureTemplate, ...)
   -> list[Figure]`, all-optional args, matches `ModelResult.render()` calls.
4. **Audit** — render metadata returned without graph state; legacy path preserved
   via deprecation shims until the next major version.

### Current status (baseline v0.1.0)

- **Implemented + tested:** legacy `Dataset`-based engine (`render_template` tuple
  return), `FigureEngine`/`IteratorEngine`, full template set (piper, stiff,
  timeseries, DWQI, …), `LegendGroup`/`LegendAccumulator`, `geofig_cli`.
- **Shipped in this phase (v0.2.0):** the declarative provider-based API
  documented below.

### M1 — Declarative API + interoperability (next major focus)

- [ ] `provider.py`: `DataProvider` Protocol, `DataFrameProvider`, `DatasetProvider`.
- [ ] `engine/generator.py`: `FigureGenerator` (provider-driven, resolving
      templates/iterators/coords); legacy `FigureEngine` untouched.
- [ ] `engine/api.py`: `render_template(data, template=<key>|FigureTemplate,
      mapping=, settings=, iterators=, facet=, coord=, savedir=)
      -> list[Figure]` with all-optional args; exported `TEMPLATES` registry +
      `register_template`/`get_template`; `render_template_legacy` (old tuple form,
      `DeprecationWarning`).
- [ ] Registry templates: `bivariate`, `boxplot_with_points` (+ native legacy-key
      builders), `dendrogram`, `site_map`, `particle_overlay`.
- [ ] Deprecation shims (`Dataset`, `Dimension`, `DimensionSelector`,
      `ColumnSelector`, `IteratorEngine`, `FigureEngine`) with import-time warnings;
      legacy test suite stays green.
- [ ] Required geo support: `CoordGeo`, geometry/image channels, geoms
      (site point, boundary, label, annotation/inset, image) + `[geo]` extra.
      Basemap tiles delivered with the `site_map` template (wp14); the DEM
      contour geom delivered with `site_map` (Phase 18.2); stream geom
      delivered with `site_map` (Phase 18.3).
- [ ] Interop tests: `geochemmodel.ModelResult.render()` smoke through the new path;
      standalone DataFrame render (basic analysis) works without geodata/geochemmodel.

### M2 — Figure/geo depth (v0.2.x)

- [ ] Deferred geoms (`GeomTable`/`GeomColorbar`);
      `CoordGeo` polish (bounds/aspect/axis format). Streams shipped in 18.3.
- [ ] Template breadth and consistency across renderers; Plotly backend candidate.

### M3 — Hardening (→ v1.0.0)

- [ ] Remove deprecated shims — per Versioning policy, no earlier than `1.0.0`.
- [ ] Public API + registry freeze; golden-image regression suite; performance.

## Versioning

**Scheme — Semantic Versioning (`MAJOR.MINOR.PATCH`).** Version authority is
`geofig-engine/pyproject.toml` → `[project] version` (single source of truth;
current baseline: `0.3.2`). Releases are tagged `geofig-engine-v<version>`
(e.g. `geofig-engine-v0.2.0`).

### Public surface governed by this policy

- Canonical API: `render_template(...)`, `register_template` / `TEMPLATES`
  registry, `DataProvider` / `DataFrameProvider` / `DatasetProvider`,
  `FigureGenerator`, `FigureSpec`/`LayerSpec`, geoms/coords/templates.
- Legacy shims (deprecated, import-time `DeprecationWarning`): `Dataset`,
  `Dimension`, `DimensionSelector`, `ColumnSelector`, `IteratorEngine`,
  `FigureEngine`, `render_template_legacy` — scheduled for removal in the
  **next major version**.

### Bump rules (tied to tasks/commits)

- **MAJOR** — breaking changes to `render_template` (signature/return),
  removal of deprecated shims or registry keys/geoms/coords/templates.
- **MINOR** — backward-compatible additions: new templates (registry keys),
  new geoms/coords/channels, new providers, `[geo]`/new renderer support;
  deprecation warnings may be introduced here, never removal.
- **PATCH** — bug fixes, documentation, internal refactors with no behavior
  change.

**Pre-1.0 note:** while `MAJOR == 0`, breaking changes bump `MINOR`
(`0.1.0 → 0.2.0` may break); the API only stabilizes at `1.0.0` (and the shim
removal lands no earlier than that).

### Deprecation policy

- A public symbol is deprecated in a **MINOR** with a `DeprecationWarning`
  (noting "deprecated since vX.Y"), retained through at least the next
  **MAJOR**, then removed in that MAJOR. A MINOR never removes.
- Registry/template keys are public API: **additions in MINOR, removals only
  in MAJOR.**

### Keeping commits & tasks in sync

- Every task that changes the public API states its **target version**; commit
  messages reference it (e.g. `geofig-engine: add DataProvider → v0.2.0`).
- A version bump is its own explicit task/commit (`release: v0.2.0`) and is
  logged in the package `CHANGELOG.md` (feature — version — date).

## Templates & Registry

`render_template(data: DataFrame | DataProvider | ndarray, template=<key> | FigureTemplate,
mapping=..., settings=..., iterators=..., facet=..., coord=..., savedir=...)` resolves
`template` through a registry mapping **template name → builder**.
`geofig_engine` **exports the default registry map** (`TEMPLATES`, a plain
`dict[name → builder]`) plus `register_template(name, builder)` so downstream
adapters (`geochemmodel.results`) and workflows can register/resolve keys
without importing rendering internals. Support-branch templates
(`bivariate`, `boxplot_with_points`) are usable with **no mapping beside
`data`/`template`** (their defaults resolve from the recipe).

Phase 15 (v0.2.0) seeds the registry at import with the concrete keys
`bivariate`, `boxplot_with_points`, `dendrogram`, `site_map`,
`particle_overlay` plus the legacy factory set listed below. Phase 18.4
(v0.4.0 target) rewired that legacy set to native builders; all ten legacy keys
now share the same canonical `render_template` pathway as the pipeline keys.

Pipeline template keys (referenced by `VisualizationEncoding.template`):

| Template | Purpose |
| --- | --- |
| `bivariate` | cluster/correlation scatter (exports markers for cluster labels) |
| `boxplot_with_points` | per-group boxplot with jittered points |
| `dendrogram` | hierarchical linkage dendrogram from `ModelResult.tables["linkage"]` |
| `site_map` | `CoordGeo` site map: basemap + point layers + grouped legend |
| `particle_overlay` | per-photo QA overlay: segmentation edges on the (downsampled) source image, classified particles, per-photo QA stats — the only figure for ParticleImageModel |

The legacy keys (`histogram`, `pie`, `radar`, `timeseries`, `isotope`,
`npr_nnp`, `anp_agp`, `nagph_nag`, `piper`, `stiff`) are seeded directly to
native `*_builder` callables. The eight layer templates return duck-typed
`TemplateRecipe`s consumed by `FigureGenerator`; `piper` and `stiff` return
first-class `SpecRecipe`s that build linked/composite `FigureSpec`s and then
reuse the normal renderer/legend/savedir path (without `iterators`/`facet`).
`FigureTemplate` factories and scalar/spec-builder functions remain supported
compatibility surfaces; the deprecated `legacy_adapter` shim is retained but
is no longer used for registry seeding and is removed no earlier than 1.0.0.

Optional extras (pyproject):

- `[geo]` extra: geographic deps for `CoordGeo` / `site_map` / geo geoms
  (projection, shapefile/geojson, kmz, altimetry; optional `xyzservices`-based
  basemap-provider lookup — the tile fetcher itself works without `[geo]`).

---

## Example Flow

### Standalone basic analysis (no modeling stage, no geodata)

```python
from geofig_engine import render_template, DataFrameProvider

figs = render_template(
    data=DataFrameProvider(df),          # raw pandas → figEngine works alone
    template="bivariate",                # registry key, defaults from recipe
    mapping={"x": "SO4", "y": "Cl", "color": "group"},
    savedir="out/",                       # optional; returns list[Figure] either way
)
```

Nothing else is required — `mapping`, `settings`, `iterators`, `facet`,
`coord` are all optional, so an even simpler `render_template(df,
template="bivariate")` renders with template defaults.

### Low-level composition (opt-in, GoG path)

```python
layer = Layer(
    geom=GeomPoint(),
    stat=StatIdentity(),
    mapping={"x": "CO3", "y": "SO4", "color": "group"},
    scales={
        "x": ScaleContinuous(),
        "y": ScaleContinuous(),
        "color": ScaleOrdinal(palette="Set1"),
    },
)

gen = FigureGenerator(
    provider=DataFrameProvider(df),      # or GeoData.provider_for("long") | DatasetProvider()
    layers=[layer],
    coord=CoordCartesian(),
    facet=FacetNull(),
    settings={"title": "CO3 vs SO4 by group"},
)
specs = gen.build_specs()
figs = gen.render(...)
```

`FigureGenerator` only speaks `DataProvider` (`provider.resolve/expand/subset`);
the legacy `FigureEngine` is a deprecated shim that adapts `Dataset` into the
same generator.

### Execution

1. Resolve `x` → `["chem2", "chem3"]` (via `provider.resolve`)
2. Iterate over `x` (optional, per-figure expansion via `provider.expand`)
3. For each iteration:
   a. Apply Stat (identity → no change)
   b. Extract data series per channel
   c. Apply Scales (data → visual domain)
   d. Build FigureSpec with resolved layers + coord
4. Render

### Upstream invocation (geochemmodel / workflows)

```python
# geochemmodel ModelResult.render() — lazy import
from geofig_engine import render_template

figs = render_template(
    data=dl.provider_for("long") | result.tables["particles"],
    template=enc.template,          # "site_map" | "bivariate" | "particle_overlay" | ...
    mapping=enc.mapping,
    settings=enc.settings,
    iterators=enc.iterators,
    facet=enc.facet,
    coord=enc.coord,
)
```

### Legacy scripts (transition)

Existing scripts keep the old call shape via the deprecated path:

```python
from geofig_engine import render_template_legacy, Dataset

specs, figures, legend_fig = render_template_legacy(
    dataset=Dataset(df, key_column="Location"),
    template=piper_case(...),       # old factories still available
)
# DeprecationWarning on call → migrate to render_template(DataFrameProvider(df), ...)
```

---

## Layer Ownership

```
provider.py/            (new)
  DataProvider Protocol            (structural; never imports geodata)
  DataFrameProvider                (in-engine dataframe adapter — standalone use)
  DatasetProvider                  (legacy Dataset → provider adapter)

core/
  AttributeMapping
  Scale (and implementations)
  Geom (and implementations)       incl. geometry/image-channel geoms
  Stat (and implementations)
  Coord (and implementations)      incl. CoordGeo ([geo] extra)
  Facet (and implementations)
  Layer / LayerSpec
  FigureSpec
  Dimension*                       (deprecated shim  → geodata)
  Dataset*                         (deprecated shim  → geodata)
  DimensionSelector*               (deprecated shim  → geodata)
  IteratorEngine*                  (deprecated shim  → provider.expand)

engine/
  generator.py  FigureGenerator    (provider-driven orchestration; shared
                                   Layer→LayerSpec resolution helpers)
  api.py        render_template    (canonical entry, list[Figure])
                render_template_legacy  (old tuple form, deprecated)
                template registry  (TEMPLATES, register_template)

deprecated.py/                     (import-time DeprecationWarning shims)

renderers/
  Renderer implementations
  (one module per backend: matplotlib/, ...)
  legend.py  (LegendGroup / LegendAccumulator — grouped, titled legends)

layers/
  Reusable layer configurations (pre-built combinations)

templates/           (optional, backward compat)
  Pre-built figure compositions (common recipes)
```

Rules:
- `core/` must not depend on `renderers/`
- `core/` must not depend on `engine/`
- `renderers/` must only depend on `FigureSpec` + `LayerSpec`
- `engine/` is the only layer allowed to connect everything
- `provider.py`, `core/`, `engine/`, `renderers/` never import `geodata` /
  `geochemmodel` (input is duck-typed through `DataProvider`)
- `engine/api.py` is the *only* module consumers import for new work;
  `engine/generator.py` stays low-level

---

## Extensibility Strategy

### Adding a new Geom
- subclass `Geom`
- declare required and optional channels
- add rendering support in each backend

### Adding a new Stat
- subclass `Stat`
- implement `compute(data, mapping) -> pd.DataFrame`
- no changes to rendering

### Adding a new Coord
- subclass `Coord`
- implement `transform(visual_values) -> screen_coords`
- update renderer to apply coord during drawing

### Adding a new Facet
- subclass `Facet`
- implement split logic
- update FigureGenerator to apply facet during spec building

### Adding a new Scale
- subclass `Scale`
- implement `transform()` and optionally `invert()`

### Adding a new backend
- implement `Renderer` interface
- handle all Geom types (or raise NotImplemented)

### Extending across packages
- new templates: call `register_template(name, builder)` (or add a
  `name → builder` entry to the exported `TEMPLATES` map) — optionally from
  the consuming package's adapter (e.g. `geochemmodel.results`, workflows) —
  no engine core changes needed.
- new inputs: implement the `DataProvider` protocol (or use
  `DataFrameProvider`); `FigureGenerator` and `render_template` pick it up
  unchanged.
- new backends / geoms / coords: engine changes only (see above); `api.py`
  remains stable for consumers.

---

## Non-Goals (for now)

- no GUI
- no automatic layout engine
- no full grammar-of-graphics implementation (we target the subset useful for environmental data)
- no pipeline package (composition lives in workflows, `../PSEUDOCODE_EXAMPLES.md`)
- no import of `geodata` / `geochemmodel`

---

## Key Constraint

The system must always preserve:

```
Data → Spec → Render separation
```

Breaking this will lead to tight coupling and poor extensibility.