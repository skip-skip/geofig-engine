# Phase 17: Column utilities (`io/columns.py`)

**Status**: open
**Phase**: 17
**Version target**: v0.3.0
**Dependencies**: `17_00_epic`

## Description

Column-level data utilities for the `geofig_engine.io` subpackage: parse
Ecesis-style column names with embedded units into a wide sample frame, and
bin numeric/datetime columns into categoricals. Contracts are deterministic
and documented (no reference codebase on disk).

## Changes

### `src/geofig_engine/io/columns.py` (new)

- `ecesis_to_sample_df(frame, unit_pattern=None, drop_na=True) -> pd.DataFrame`
  - Parses Ecesis-style **column names with embedded units** and returns a
    wide sample frame with a two-level column index `(analyte, unit)`.
  - Column-name forms recognized (documented regexes):
    - `"NO3_mg/L"` / `"NO3_ug/L"` — underscore-separated unit
    - `"Ca (mg/L)"` — parenthesized unit
    - plain names without a unit (`"Sample_ID"`, `"pH"`) stay as-is (unit
      level `""`, no split)
  - Default `unit_pattern` mirrors the `io/equis.py` `UNIT_RE` set
    (SI prefixed mass/volume forms, `meq/L`, `ppb`, `ppm`, `mg/kg`, `mg_kg`,
    `%`); an explicit `unit_pattern` (compiled regex) overrides it.
  - Returned frame keeps original row order and column order; cells are
    `pd.to_numeric(errors="coerce")`; rows where **every** parsed numeric
    cell is NaN are dropped when `drop_na=True` (documented). Input frame is
    never mutated.
- `create_bins(series, bins, strategy="range", labels=None, include_lowest=True, right=True) -> pd.Series`
  - Categorical bins from a numeric or datetime `series`.
  - `strategy="range"` — `bins` is either an int (that many equal-width bins
    across the observed min–max) or an explicit sorted sequence of edges.
  - `strategy="quantile"` — `bins` is the number of equal-frequency bins
    (uses `qcut` semantics); duplicated edges are collapsed into a single
    edge (no empty bins).
  - `labels` optional; `include_lowest` / `right` map onto `cut`/`qcut`
    semantics. NaN input values → NaN category (documented).
  - Deterministic: identical input → identical category dtype and ordering.

### `src/geofig_engine/io/__init__.py`

- Export `ecesis_to_sample_df`, `create_bins` (append to `__all__`).

### `tests/test_io.py` (extended)

- `TestEcesisToSampleDf` — underscore and parenthesized unit parsing,
  MultiIndex (analyte, unit) columns, plain columns preserved, numeric
  coercion, drop_na, input frame unchanged.
- `TestCreateBins` — range str: int bins and explicit edges; quantile
  str: equal-frequency; NaN → NaN category; datetime input; labels applied;
  deterministic category order.

## Acceptance criteria

- [ ] Ecesis column-name parsing handles underscore and parenthesized units;
      plain columns pass through
- [ ] `create_bins` supports both strategies on numeric and datetime input
      deterministically; NaN handled as documented
- [ ] Input frames/series not mutated; no new required dependencies
- [ ] Both exported from `geofig_engine.io`
- [ ] Full suite green; committed as a single commit
      (`geofig-engine: io column utilities → v0.3.0`)

## Files

- `src/geofig_engine/io/columns.py` (new)
- `src/geofig_engine/io/__init__.py`
- `tests/test_io.py`