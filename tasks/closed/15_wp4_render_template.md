# Phase 15: New render_template (canonical; list[Figure])

**Status**: complete
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_wp2_template_registry`, `15_wp3_figure_generator`

## Description

Add the **one canonical entry point** (`ARCHITECTURE.md` §1a + `## Templates &
Registry`):

```python
def render_template(
    data: DataFrame | DataProvider,
    template: str | FigureTemplate,
    mapping: dict | None = None,
    settings: dict | None = None,
    iterators: list | None = None,
    facet: Facet | None = None,
    coord: Coord | None = None,
    savedir: str | Path | None = None,
    renderer_name: str = "matplotlib",
) -> list[Figure]:
```

All inputs after `data`/`template` are **optional**; defaults resolve lazily
from the template recipe. A raw `pandas.DataFrame` is wrapped in
`DataFrameProvider`, keeping figEngine usable standalone. `template` may be a
registry key or a `FigureTemplate` (adapted to a recipe). `mapping` overrides/
merges recipe layer mappings; `coord` overrides the recipe coord. `savedir`
persists each figure (and legend) as PNG. Returns **`list[Figure]`** — the old
`(specs, figures, legend_fig)` tuple moves to `render_template_legacy`
(`15_wp5`).

## Changes

### `src/geofig_engine/engine/api.py`

- `render_template(...)`:
  - `data` → `DataProvider` (pass through) | `pd.DataFrame` (wrap with
    `DataFrameProvider`) | ndarray (wrap in a frame with positional columns,
    for `dendrogram` linkage input)
  - resolve `template` via `get_template` (key) or `recipe_from` (`FigureTemplate`)
  - merge `mapping`/`coord`/`settings` with recipe defaults (settings:
    recipe defaults ← merge user settings; mapping: per-layer override)
  - compose a `FigureGenerator` from the recipe layers/coord, call
    `build_specs()` + `render()`; report missing required channels with a
    clear message
  - `savedir`: replicate the legacy save naming convention (index + iterator
    key parts) + a `legend.png`; renderer gating on `renderer_name`
- Do **not** return `specs`/`legend_fig` here — those live in the legacy path.

## Acceptance criteria

- [ ] `render_template(df, template="bivariate")` renders with recipe defaults (no mapping)
- [ ] `render_template(DataFrameProvider(df), template=<FigureTemplate>)` renders
- [ ] `mapping={"x": ..., "y": ..., "color": "group"}` overrides per-layer mappings
- [ ] `coord=` overrides the recipe coord; unknown template key raises `KeyError` listing keys
- [ ] Missing required channels raise the informative error (not a traceback into generator internals)
- [ ] Return type is `list[Figure]` (matplotlib figures) in every path; `savedir=` writes PNGs + `legend.png`
- [ ] No `geodata`/`geochemmodel` import in `engine/api.py`
- [ ] Tests extended in `tests/test_entry.py` + a focused `tests/test_declarative_api.py`
- [ ] Committed as a single commit (`geofig-engine: add declarative render_template → v0.2.0`); full suite green

## Files

- `src/geofig_engine/engine/api.py`
- `tests/test_entry.py`
- `tests/test_declarative_api.py` (new)