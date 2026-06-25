# FigEngine Architecture

## Overview

FigEngine is a declarative visualization system built around the **Grammar of Graphics** (GoG) – a formal framework where statistical graphics are composed from independent, reusable components.

### Core GoG Concepts

1. **Tidy dataset**
2. **Semantic dimension metadata**
3. **Aesthetic mappings + Scales** (data → visual domain)
4. **Geoms** (visual marks – points, lines, bars, etc.)
5. **Stats** (statistical transformations – identity, bin, smooth, etc.)
6. **Coord** (coordinate system – Cartesian, polar, etc.)
7. **Facet** (subplot splitting)
8. **Layer** (Geom + Stat + mapping bound to data)
9. **Rendering backends**

### Pipeline

```
Dataset
→ DimensionSelector (resolve columns)
→ IteratorEngine / Facet (expand contexts)
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

### 1. Dataset

Represents the raw tidy data.

```python
Dataset:
    dataframe: pandas.DataFrame
    key_column: str
    dimensions: dict[str, Dimension]

Responsibilities:
- store data
- validate schema
- expose selection/filtering
- expose unique values per dimension
```

---

### 2. Dimension

Represents a column with semantic metadata.

```python
Dimension:
    name: str
    labels: dict[str, Any]
```

Example labels:
- `{"analyte": True}`
- `{"unit": "mg/L"}`
- `{"role": "group"}`

Labels are purely metadata and must not encode visualization behavior.

---

### 3. DimensionSelector

Flexible way to select dimensions by name or metadata.

```python
DimensionSelector:
    resolve(dataset) -> list[str]
```

Supports:
- single column: `"chem1"`
- attribute-based: `{"analyte": True}`
- explicit list: `["chem1", "chem2"]`

---

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
- `GeomPath` – arbitrary path
- `GeomErrorbar` – error bars
- `GeomSmooth` – smoothed conditional mean (composition of StatSmooth + GeomRibbon/Line)

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
- `CoordTransformed` – arbitrary scale transforms (log, sqrt, etc.)
- `CoordFlip` – swapped x/y axes
- `CoordFixed` – fixed aspect ratio

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

### 11. IteratorEngine

Generates multiple independent figures based on dimension expansion.

```python
IteratorEngine:
    expand(dataset, selectors) -> list[(subset_df, context)]
```

Where:
- `subset_df` is a filtered view of the dataset
- `context` is a dict of iterator values (e.g., `{"analyte": "chem2"}`)

Use for: generating one figure *per* combination of values (e.g., one plot per analyte).
Use Facet for: multiple panels *within* a single figure.

IteratorEngine must:
- not modify original dataset
- not depend on templates, layers, or mappings
- operate only on dataset + selectors

---

### 12. FigureGenerator (Orchestrator)

Top-level system entry point.

```python
FigureGenerator:
    dataset
    layers: list[Layer]
    coord: Coord
    facet: Facet
    scales: dict[str, Scale]      # optional global defaults
    settings: dict
    iterators: list[DimensionIterator]  # optional (for multi-figure output)

Responsibilities:
- resolve dimension selectors
- expand iterators (for multi-figure)
- apply facets (for multi-panel)
- resolve scales (data → visual domain)
- build FigureSpec(s)
- send to renderer
```

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

Renderers must:
- consume only FigureSpec (no access to Dataset, Dimensions, etc.)
- not perform data transformations or scale resolution
- handle all Geom types they support (return NotImplemented for unsupported)
- respect Coord and Facet

---

## Example Flow

### User Configuration

```python
# Define layers
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

# Compose figure
generator = FigureGenerator(
    layers=[layer],
    coord=CoordCartesian(),
    facet=FacetNull(),
    settings={"title": "Analyte vs chem1 by group"},
)
```

### Execution

1. Resolve `x` → `["chem2", "chem3"]`
2. Iterate over `x` (optional, per-figure expansion)
3. For each iteration:
   a. Apply Stat (identity → no change)
   b. Extract data series per channel
   c. Apply Scales (data → visual domain)
   d. Build FigureSpec with resolved layers + coord
4. Render

---

## Layer Ownership

```
core/
  Dataset
  Dimension
  DimensionSelector
  AttributeMapping
  Scale (and implementations)
  Geom (and implementations)
  Stat (and implementations)
  Coord (and implementations)
  Facet (and implementations)
  Layer / LayerSpec
  FigureSpec
  IteratorEngine

engine/
  FigureGenerator (orchestration)

renderers/
  Renderer implementations
  (one module per backend)

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

---

## Non-Goals (for now)

- no GUI
- no automatic layout engine
- no full grammar-of-graphics implementation (we target the subset useful for environmental data)

---

## Key Constraint

The system must always preserve:

```
Data → Spec → Render separation
```

Breaking this will lead to tight coupling and poor extensibility.
