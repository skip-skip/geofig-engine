# geofig-engine

A declarative grammar-of-graphics plotting engine for hydrogeochemical and
engineering data. Geofig-engine provides a small core API for describing what
a figure *is* — data, mappings, layers, scales, coords, facets, and settings —
and a matplotlib renderer that turns those descriptions into figures.

## Installation

Requires Python 3.11+. Core runtime dependencies are `pandas`, `matplotlib`,
`numpy`, and `openpyxl`.

```bash
python -m pip install -e .
```

Optional extras:

| Extra | Adds |
| --- | --- |
| `dev` | `pytest`, `pytest-cov`, `build` |
| `geo` | `pyproj`, `pyshp` for projected CRSs and shapefile boundaries |
| `network` | `requests`, `pillow`, `xyzservices` for basemap tiles, DEM contours, and streams |
| `full` | all of the above |

```bash
python -m pip install -e ".[dev]"
python -m pip install -e ".[full]"
```

See [INSTALL.md](INSTALL.md) for wheel, offline, headless, and verification
instructions.

## Quickstart (standalone)

No `Dataset` wrapper or upstream package needed — a raw `pandas.DataFrame` is
accepted and wrapped automatically:

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
figures[0].show()  # render_template returns list[Figure]
```

`template` is a key into the exported `TEMPLATES` registry (or a
`FigureTemplate`/recipe object); `mapping` and `settings` override the
template defaults per call. `render_template` accepts any `DataProvider`-shaped
object (e.g. a `DataFrameProvider` or a third-party duck-typed provider);
`Dataset`-based pipelines are served by the deprecated `render_template_legacy`
entry, which warns at call time.

## Documentation

The API reference is organized into these pages under `docs/`:

| Page | Scope |
| --- | --- |
| [API: Core](docs/api/core.md) | Data model, dimensions, iterators, layers, specs, geoms, stats, scales, coords (incl. `CoordGeo`), facets, links, axis/plot settings |
| [API: Engine](docs/api/engine.md) | The `render_template` entry point, `TEMPLATES` registry, `FigureGenerator`, and the deprecated legacy surface |
| [API: Providers](docs/api/provider.md) | The `DataProvider` protocol and the `DataFrameProvider` / `DatasetProvider` implementations |
| [API: Templates](docs/api/templates.md) | `FigureTemplate`, the shipped hydrogeochemical templates, and their `TEMPLATES` registry keys |
| [API: Renderers](docs/api/renderers.md) | `BaseRenderer`, `MatplotlibRenderer`, and the legend API |
| [API: Serialization](docs/api/serialize.md) | `FigureSpec` <-> dict / JSON converters |
| [API: Data](docs/api/data.md) | Geom preset registry and the legacy functions API |
| [API: IO](docs/api/io.md) | Distance helpers, marker generation, EQuIS conversion, unit normalization, column utilities, and preprocessing pipelines |