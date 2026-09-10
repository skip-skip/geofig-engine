# geofig-engine

A declarative grammar-of-graphics plotting engine for hydrogeochemical and
engineering data. Geofig-engine provides a small core API for describing what
a figure *is* — data, mappings, layers, scales, coords, facets, and settings —
and a matplotlib renderer that turns those descriptions into figures.

## Installation

Requires Python 3.11+. Runtime dependencies are `pandas` and `matplotlib`.

```bash
pip install -e .
```

## Quickstart

```python
import pandas as pd
from geofig_engine.templates import bivariate
from geofig_engine.engine import render_template

df = pd.DataFrame({
    "x": [1, 2, 3, 4, 5],
    "y": [2, 3, 5, 7, 11],
    "well": ["A", "A", "B", "B", "B"],
})

specs, figures, legend = render_template(
    dataset=df,
    template=bivariate(mapping={"x": "x", "y": "y", "color": "well"}),
    settings={"figsize": (8, 6)},
)
figures[0].show()
```

Templates, data, and `mapping` values are described by the API reference;
`render_template` accepts either a `Dataset` object or a `pd.DataFrame`.

## Documentation

The API reference is organized into these pages under `docs/`:

| Page | Scope |
| --- | --- |
| [API: Core](docs/api/core.md) | Data model, dimensions, iterators, layers, specs, geoms, stats, scales, coords, facets, links, axis/plot settings |
| [API: Engine](docs/api/engine.md) | `EngineConfig`, `FigureEngine`, and the `render_template` entry point |
| [API: Templates](docs/api/templates.md) | `FigureTemplate` and the shipped hydrogeochemical templates |
| [API: Renderers](docs/api/renderers.md) | `BaseRenderer`, `MatplotlibRenderer`, and the legend API |
| [API: Serialization](docs/api/serialize.md) | `FigureSpec` <-> dict / JSON converters |
| [API: Data](docs/api/data.md) | Geom preset registry and the legacy functions API |
| [API: IO](docs/api/io.md) | Distance helpers, marker generation, and preprocessing pipelines |