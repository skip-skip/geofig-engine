# Phase 17: EQuIS format conversion (`io/equis.py`)

**Status**: complete
**Phase**: 17
**Version target**: v0.3.0
**Dependencies**: `17_00_epic`

## Description

EQuIS format conversion utilities in the `geofig_engine.io` subpackage:
pivot the EQuIS "flat" long format (one row per parameter result per sample)
to a wide per-sample frame, melt it back, and parse the EQuIS cross-tab
Excel layout. Contracts are defined deterministically (no reference
codebase is available on disk).

## Changes

### `src/geofig_engine/io/equis.py` (new)

- `equisflat_to_sample_df(flat, sample_keys=("Location",), parameter_col="Parameter", value_col="Result", extra_cols=(), drop_na=True) -> pd.DataFrame`
  - Pivot a long flat frame to wide: one row per sample (the `sample_keys`
    columns are kept first), one column per parameter (first-appearance
    order), cells = results.
  - Inputs: `parameter_col` names the analyte; `value_col` is the numeric
    result; `extra_cols` are additional sample-level columns that must be
    constant per sample (raises `ValueError` otherwise). Columns outside
    `sample_keys` / `parameter_col` / `value_col` / `extra_cols` are
    dropped (documented).
  - A duplicated `(sample, parameter)` pair raises `ValueError` with an
    informative message. Rows with a NaN result are dropped when
    `drop_na=True`.
  - Never mutates the input frame.
- `sample_df_to_equisflat(sample_df, sample_keys=("Location",), parameter_col="Parameter", value_col="Result", extra_cols=(), drop_na=True) -> pd.DataFrame`
  - Inverse melt: rows = `(sample_keys..., parameter_col, value_col)`, wide
    parameter columns become `parameter_col` values; `extra_cols` propagate
    per sample. Rows with NaN values dropped when `drop_na=True`.
  - Round-trips `equisflat_to_sample_df` (column names, values, and
    first-appearance column order preserved).
- `equis_crosstab_to_flat(path_or_df, sample_keys=("Location",), parameter_col="Parameter", value_col="Result", unit_col="Result_Unit") -> pd.DataFrame`
  - Accepts a `pd.DataFrame` already read from a cross-tab, or an Excel
    file path / `Path` / file-like (read via `pd.read_excel`; engine
    auto-selected — `openpyxl` needed only when a test exercises Excel).
  - Cross-tab layout: rows = samples + metadata; columns = `Analyte` or
    `Analyte<unit-suffix>`; cells = numeric results.
  - Column-name parsing (documented regex): embedded units via
    `"NO3_mg/L"` (underscore) or `"Ca (mg/L)"` (parenthesized) split into
    `parameter_col` + `unit_col`; columns with no unit suffix and not in
    `sample_keys` are treated as plain metadata and kept on every row.
    Units matched: SI prefixed mass/volume forms (`ng/L`, `ug/L`, `µg/L`,
    `mg/L`, `g/L`, `mg/kg`, `mg_kg`), `meq/L`, `ppb`, `ppm`, plus plain
    `mg`, `g`, `kg`, `%` — see the module `UNIT_RE` constant.
  - Cells coerced with `pd.to_numeric(errors="coerce")` (non-numeric cells
    become NaN, documented).

### `src/geofig_engine/io/__init__.py`

- Export `equisflat_to_sample_df`, `sample_df_to_equisflat`,
  `equis_crosstab_to_flat` (append to `__all__`).

### `tests/test_io.py` (extended)

- `TestEquisFlatToSample` — pivot shape/columns, sample-key order, duplicate
  `(sample, parameter)` raises, `extra_cols` constant-per-sample, invalid
  varying extra_cols raises, drop_na behavior, input frame unchanged.
- `TestSampleDfToEquisFlat` — inverse melt values, round-trip equality with
  `equisflat_to_sample_df`.
- `TestEquisCrosstabToFlat` — DataFrame input: underscore units, parenthesized
  units, plain metadata columns, non-numeric cell → NaN; Excel input via
  `pytest.importorskip("openpyxl")` writing a workbook to a `BytesIO` buffer.

## Acceptance criteria

- [ ] `equisflat_to_sample_df` / `sample_df_to_equisflat` round-trip (values
      and parameter column order preserved)
- [ ] Duplicate (sample, parameter) and non-constant extra columns raise
      `ValueError` with informative messages
- [ ] `equis_crosstab_to_flat` parses underscore and parenthesized units into
      `Parameter` + `Result_Unit` and coerces cells; Excel input works when
      `openpyxl` is present and skips cleanly otherwise
- [ ] No input frame is mutated; no new required dependencies
- [ ] All three exported from `geofig_engine.io`
- [ ] Full suite green (1039 baseline + all new); committed as a single commit
      (`geofig-engine: io equis conversion → v0.3.0`)

## Files

- `src/geofig_engine/io/equis.py` (new)
- `src/geofig_engine/io/__init__.py`
- `tests/test_io.py`