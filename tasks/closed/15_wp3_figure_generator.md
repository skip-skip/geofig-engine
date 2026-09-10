# Phase 15: FigureGenerator (provider-driven orchestrator)

**Status**: complete
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_wp1_provider_contract`

## Description

Add the provider-driven orchestrator (`ARCHITECTURE.md` §12 `FigureGenerator`).
It is the **only** component allowed to orchestrate multiple subsystems and
consumes **only** `DataProvider` (`provider.resolve` / `provider.expand` /
`provider.subset`). Layering → `LayerSpec` resolution helpers are extracted
from the legacy `FigureEngine` so both engines share them; the legacy
`FigureEngine` behavior is **unchanged** (its existing tests must stay green).

The legacy `Dataset` path reaches this generator through `DatasetProvider`
(`15_wp1`), so `FigureEngine` can stay as-is and the deprecation shim (`15_wp5`)
simply re-exports it.

## Changes

### `src/geofig_engine/engine/generator.py`

- Extract shared Layer→LayerSpec resolution / scale-resolution helpers used by
  `FigureEngine` into module-level functions (or a small internal resolver
  object) so both engines reuse the same code path. Legacy `FigureEngine`
  internals delegate to these helpers with **no behavior change**.
- Add `FigureGenerator` with the field surface from §12:

  ```python
  FigureGenerator(provider: DataProvider, layers: list[Layer], coord: Coord,
                  facet: Facet = FacetNull(), scales: dict[str, Scale] | None = None,
                  settings: dict | None = None,
                  iterators: list[DimensionIterator] | None = None)
  ```

  - `build_specs() -> list[FigureSpec]` — resolve selectors via
    `provider.resolve`, expand `provider.iterators` via `provider.expand`,
    apply facet splitting, resolve scales (data → visual domain), build the
    `FigureSpec`(s) with resolved layers + coord + settings.
  - `render(renderer=None, renderer_name="matplotlib") -> list[Figure]` —
    build then hand `FigureSpec`s to the renderer.
  - Missing required channels raise an informative error **at spec-build
    time** (lazy default resolution — no eager validation).
- Keep `FigureEngine` importable and green (existing `tests/test_engine*.py`
  pass untouched).

## Acceptance criteria

- [ ] `FigureGenerator` consumes a `DataProvider`; a `DataFrameProvider`-backed
      generator produces `FigureSpec`s equivalent to the legacy path for the
      same layers/settings (assert layer count/columns/coord)
- [ ] `provider.resolve` / `provider.expand` / `provider.subset` are called by
      the generator (spy on a test provider) — the generator never touches a
      `Dataset` object directly
- [ ] Facet splitting yields one spec per facet group
- [ ] Missing required channels raise the informative spec-build error
- [ ] Legacy `FigureEngine` tests and `hydro_demo.py` output unchanged (run the
      demo; no diffs in rendered figures)
- [ ] No `geodata`/`geochemmodel` import in `engine/generator.py`
- [ ] Tests added in `tests/test_engine_new_api.py` (and/or `test_provider.py`)
- [ ] Committed as a single commit (`geofig-engine: add FigureGenerator → v0.2.0`); full suite green

## Files

- `src/geofig_engine/engine/generator.py`
- `tests/test_engine_new_api.py`