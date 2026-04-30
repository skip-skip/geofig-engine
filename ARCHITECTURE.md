# FigEngine Architecture

## Overview

FigEngine is a declarative visualization system built around:

1. **Tidy dataset**
2. **Semantic dimension metadata**
3. **Figure attribute mappings**
4. **Figure templates**
5. **Rendering backends**

The system transforms:

Dataset
→ DimensionSelector (resolve columns)
→ IteratorEngine (expand contexts)
→ FigureTemplate (build spec)
→ FigureSpec
→ Renderer
→ Figures
---

## Core Design Principles

### 1. Separation of Concerns

- Data is never mutated by visualization logic
- Dimension metadata is independent of rendering
- Templates define structure, not execution
- Renderers only draw (no business logic)

---

### 2. Declarative Configuration

Figures are defined by *what they represent*, not *how to draw them*.

Example:

- x = analytes
- y = chem1
- color = 'blue'
- marker = group

---

### 3. Extensibility

The system must support:

- new figure types (templates)
- new rendering backends
- new dimension roles
- new attribute mappings

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

---

### 2. Dimension

Represents a column with semantic metadata.

Dimension:
    name: str
    attributes: dict[str, Any]

Example attributes:
- analyte=True
- unit="mg/L"
- role="group"

Attributes are purely metadata and must not encode visualization behavior.

---

### 3. DimensionSelector

Flexible way to select dimensions.

Supports:
- single column: "chem1"
- attribute-based: {"analyte": True}
- explicit list: ["chem1", "chem2"]

DimensionSelector:
    resolve(dataset) -> list[str]

---

### 4. Attribute Mapping

Maps data (or constants) to visual encodings.

AttributeMapping:
    target: str   # "x", "y", "color", "marker"
    source: Union[
        DimensionSelector,
        str,           # single column
        list[str],     # multiple columns
        constant value
    ]

Responsibilities:
- store declarative mapping only
- resolve sources into concrete values before rendering
- support constants and selectors uniformly
AttributeMapping must NOT:
- access dataset directly
- perform rendering logic

Examples:
- x = DimensionSelector(analyte=True)
- y = "chem1"
- color = "blue"
- marker = "group"

---

### 5. FigureTemplate

Defines a figure type with defaults.

FigureTemplate:
    name: str
    required_mappings: list[str]
    default_settings: dict
    build_spec(
        data: pd.DataFrame,
        mappings: dict,
        settings: dict,
        context: dict
    ) -> FigureSpec

Templates must:
- not resolve DimensionSelectors
- not perform iteration
- only apply structure + defaults

Example:
BivariateTemplate:
- requires x, y
- optional color, marker
- default alpha=0.8

---

### 6. FigureSpec

Concrete, fully resolved plotting instruction.

FigureSpec:
    data: pandas.DataFrame
    mappings: dict[str, Any]
    settings: dict
    context: dict   # iterator values

This is the contract between system and renderer.

---

### 6.5  Mapping Resolution

Before FigureSpec creation, all mappings must be resolved.

Resolution includes:
- DimensionSelector → list of column names
- column names → actual data series
- constants → preserved as-is

This produces fully concrete mappings used in FigureSpec.

This step must occur BEFORE rendering and AFTER iterator expansion.

---

### 7. Iterator Engine

Generates multiple figures based on dimension expansion.

Supports:
- iterating over dimension values
- iterating over dimension groups (e.g., analytes)

IteratorEngine:
    expand(dataset, selectors) -> list[(subset_df, context)]

Where:
- subset_df is a filtered view of the dataset
- context is a dict of iterator values (e.g., {"analyte": "chem2"})

IteratorEngine must:
- not modify original dataset
- not depend on templates or mappings
- operate only on dataset + selectors

---

### 8. FigureGenerator (Orchestrator)

Top-level system entry point.

FigureGenerator:
    dataset
    template
    mappings
    iterator

Responsibilities:
- resolve dimension selectors
- expand iterators
- build FigureSpec(s)
- send to renderer

FigureGenerator is the ONLY component allowed to orchestrate multiple subsystems.

---

### 9. Renderer

Backend-specific drawing logic.

Renderer:
    render(spec: FigureSpec) -> Figure

Examples:
- MatplotlibRenderer
- PlotlyRenderer (future)

---

## Example Flow
### Input
- Dataset with columns:
    - chem1, chem2, chem3
    - group
    - metadata
- Metadata:
    - chem2, chem3 → analyte=True

---

## Layer Ownership

core/
- Dataset
- Dimension
- DimensionSelector
- AttributeMapping
- IteratorEngine
- FigureSpec

templates/
- FigureTemplate implementations

renderers/
- Renderer implementations

engine/
- FigureGenerator (orchestration)

utils/
- shared helpers only

Rules:
- core must not depend on templates or renderers
- templates must not depend on renderers
- renderers must only depend on FigureSpec
- engine is the only layer allowed to connect everything

---

### User Configuration
template = "bivariate"

mappings = {
    "x": DimensionSelector(analyte=True),
    "y": "chem1",
    "marker": "group",
    "color": "blue"
}

---

### Execution
1. resolve x → ["chem2", "chem3"]
2. iterate over x (optional)
3. build FigureSpec(s)
4. render each

---

## Extensibility Strategy
### Adding a new figure type
- subclass FigureTemplate
- define required mappings
- define defaults

### Adding new attribute
- extend AttributeMapping targets
- update renderer interpretation

### Adding new backend
- implement Renderer interface
- no changes to core system

## Non-Goals (for now)
- no GUI
- no automatic layout engine
- no full grammar-of-graphics implementation

## Key Constraint

The system must always preserve:
Data → Spec → Render separation

Breaking this will lead to tight coupling and poor extensibility.