# Phase 15: Legacy path + deprecation shims

**Status**: complete
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_wp4_render_template`

## Description

Preserve the legacy surface under the new package layout, marked deprecated
per the versioning policy (deprecate in MINOR/v0.2.0; remove no earlier than
1.0.0):

1. `render_template_legacy(dataset=Dataset, template=FigureTemplate, ...) ->
   (specs, figures, legend_fig)` — the former tuple-form entry, retained
   verbatim, **warns on call** (`DeprecationWarning`).
2. `deprecated.py` — re-export `Dataset`, `Dimension`, `DimensionSelector`,
   `ColumnSelector`, `IteratorEngine`, `FigureEngine` with **import-time**
   `DeprecationWarning`, each pointing at its replacement (per the shim table
   in `ARCHITECTURE.md` §1a).
3. `__init__.py` — split `__all__` into **public** (`render_template`,
   `register_template`, `get_template`, `TEMPLATES`, `DataProvider`,
   `DataFrameProvider`, `DatasetProvider`, `FigureGenerator`, `FigureSpec`,
   ...) and **deprecated** (`Dataset`, `Dimension`, `DimensionSelector`,
   `ColumnSelector`, `FigureEngine`, `IteratorEngine`, `render_template_legacy`).

The existing legacy test suite keeps passing: import-time warnings must not
break it (adjust `tests/conftest.py` filters only if it currently escalates
warnings to errors).

## Changes

### `src/geofig_engine/engine/entry.py`

- Keep the existing implementation but expose it as `render_template_legacy`
  (call-time `warnings.warn(..., DeprecationWarning)`). `engine/api.py`
  imports it; the old module no longer exports `render_template`.

### `src/geofig_engine/deprecated.py` (new)

- Import-time-warning re-exports of `Dataset`, `Dimension`,
  `DimensionSelector`, `ColumnSelector`, `IteratorEngine`, `FigureEngine`,
  each with a `DeprecationWarning` message naming the replacement
  (see shim table). No duplicate warnings on repeated import of the same
  symbol in one process.

### `src/geofig_engine/__init__.py`

- Public + deprecated `__all__` split; public names resolve without warnings;
  deprecated names resolve only with the import-time warning. `geofig_cli`
  untouched.

## Acceptance criteria

- [ ] `render_template_legacy(...)` returns the tuple and emits a call-time `DeprecationWarning`
- [ ] `from geofig_engine import Dataset` warns; `from geofig_engine import render_template` does not
- [ ] `geofig_engine.__all__` clearly separates public from deprecated
- [ ] The full legacy suite passes (1039 baseline + existing) with no
      warning-escalation skips/failures; conftest adjusted only if necessary
- [ ] `geofig_cli` still functions (smoke test)
- [ ] New `tests/test_deprecations.py` asserts warning presence/absence + one per symbol per process
- [ ] Committed as a single commit (`geofig-engine: legacy path + deprecation shims → v0.2.0`); full suite green

## Files

- `src/geofig_engine/engine/entry.py`
- `src/geofig_engine/engine/api.py`
- `src/geofig_engine/deprecated.py` (new)
- `src/geofig_engine/__init__.py`
- `tests/conftest.py` (only if needed)
- `tests/test_deprecations.py` (new)