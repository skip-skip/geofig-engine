# Phase 15: DataProvider contract (provider.py)

**Status**: open
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_00_epic`

## Description

Add the single input abstraction the engine will consume: a structural
`DataProvider` Protocol plus two concrete implementations. This is the contract
geodata provider views (and geochemmodel result tables) will satisfy in the
interop milestone. **No import of `geodata`/`geochemmodel`** — the Protocol is
duck-typed.

The Protocol surface (from `ARCHITECTURE.md` "Structural provider contract" and
§1 DataProvider):

```python
class DataProvider(Protocol):
    @property
    def columns(self) -> list[str]: ...
    def resolve(self, selector) -> list[str]: ...      # DimensionSelector resolution
    def expand(self, iterators: list | None = None) -> list[tuple[pd.DataFrame, dict]]: ...
    def subset(self, *, columns=None, **filters) -> DataProvider: ...
    def unique_values(self, column: str) -> list: ...
    def dimensions(self, column: str) -> dict: ...     # column metadata labels
```

## Changes

### `src/geofig_engine/provider.py` (new)

- `DataProvider(Protocol)` — `@runtime_checkable`; document member semantics
  (resolve maps a `DimensionSelector`/column name to concrete column strings;
  expand yields `(frame, context)` per iterator combination with `None` =
  single `(frame, {})`; subset returns a **new** provider, never mutates).
- `DataFrameProvider(pd.DataFrame)` — wraps a raw frame for standalone use:
  - `columns` = list(df.columns)
  - `resolve(selector)` — column name → `[name]`; `DimensionSelector`-like
    `(kind, column)` tuples → matching columns (TBD: reuse
    `core/dimension_selector.py` resolution if trivially reusable, else a
    minimal duck check); unknown → `KeyError` with message
  - `expand(iterators=None)` — `None` → `[(df, {})]`; else iterate unique
    values per iterator column (delegating to a shared helper)
  - `subset(*, columns=None, **filters)` — boolean-mask filtering by column
    values (exact match; `in` list), returns a fresh `DataFrameProvider`
  - `unique_values(column)` — sorted unique values
  - `dimensions(column)` — `{}` (no metadata plane at this layer)
- `DatasetProvider(Dataset)` — adapts the legacy `Dataset` (its dataframe +
  `dimensions` dict): `dimensions(column)` maps from the Dataset's dimension
  labels; other members mirror `DataFrameProvider`. Used by the legacy
  engine-adaptation path and deprecated code only.

### `src/geofig_engine/__init__.py`

- Export `DataProvider`, `DataFrameProvider`, `DatasetProvider` (public `__all__`
  split finalized in `15_wp5`).

## Acceptance criteria

- [ ] `isinstance(frame_provider, DataProvider)` holds (runtime-checkable)
- [ ] `DataFrameProvider(df).resolve("col") == ["col"]`; unknown column raises `KeyError`
- [ ] `subset(columns=[...], waste_type="FB")` filters; returns a new provider; input frame unchanged
- [ ] `expand()` with iterators yields one `(frame, context)` per combination
- [ ] `unique_values` / `dimensions` behave as documented
- [ ] `DatasetProvider` exposes the Dataset's dimension labels via `dimensions()`
- [ ] `from geofig_engine.provider import DataProvider` succeeds; no
      `geodata`/`geochemmodel` import anywhere in the module
- [ ] New `tests/test_provider.py` covers the above (including a minimal
      duck-typed third-party provider passing through the Protocol)
- [ ] Committed as a single commit (`geofig-engine: add DataProvider contract → v0.2.0`); full suite green

## Files

- `src/geofig_engine/provider.py` (new)
- `src/geofig_engine/__init__.py`
- `tests/test_provider.py` (new)