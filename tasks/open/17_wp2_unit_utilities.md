# Phase 17: Unit utilities (`io/units.py`)

**Status**: open
**Phase**: 17
**Version target**: v0.3.0
**Dependencies**: `17_00_epic`

## Description

Unit-normalization and carbonate-species utilities for the `geofig_engine.io`
subpackage: normalize SI prefixes within analyte groups, and compute
combined HCO3+CO3 from alkalinity + pH + temperature. Contracts are
deterministic and documented (no reference codebase on disk).

## Changes

### `src/geofig_engine/io/units.py` (new)

- `equisflat_normalize_units(flat, parameter_col="Parameter", value_col="Result", unit_col="Result_Unit", inplace=False) -> pd.DataFrame`
  - Normalize SI prefixes (nano → kilo) **within each analyte group** so all
    results for one parameter share one unit string.
  - Works per `parameter_col` group: the canonical unit for a group is the
    most frequent unit string (ties → lexicographically smallest); every
    row's value is rescaled
    `value * 10 ** (prefix_exponent(canonical) - prefix_exponent(row_unit))`
    and the unit string replaced by the canonical one.
  - Prefix table (module `SI_PREFIXES`, documented): `n` 1e-9, `u`/`µ` 1e-6,
    `m` 1e-3, `c` 1e-2, `d` 1e-1, (base) 1e0, `k` 1e3, `M` 1e6, `G` 1e9.
    Units are parsed as `prefix? + base` where base matches
    `(g|L|mol|mg_kg ... )`; unrecognized unit strings are left untouched
    (value and unit unchanged, documented).
  - Returns a new frame by default; `inplace=True` mutates and returns the
    input frame.
- `fill_bicarbonate_as_hco3(df, alkalinity_col, ph_col, temperature_col=None, out_col="HCO3_CO3", inplace=False) -> pd.DataFrame`
  - Adds `out_col` = combined bicarbonate + carbonate alkalinity equivalent
    using carbonate speciation at (pH, temperature): the HCO3⁻+CO3²⁻ fraction
    of total alkalinity,
    `f = (K1·[H] + 2·K1·K2) / ([H]² + K1·[H] + K1·K2)`,
    with `[H] = 10**(-pH)` and temperature-corrected dissociation constants
    (documented Arrhenius-style corrections of pKa1 = 6.35, pKa2 = 10.33 at
    25 °C; `temperature_col` optional, defaults to 25 °C).
  - Rows with NaN pH → NaN result; missing columns raise `KeyError` with an
    informative message. Units are those of the input alkalinity column
    (mg/L ↔ meq/L conversion intentionally not performed — deferred to an
    external data system).

### `src/geofig_engine/io/__init__.py`

- Export `equisflat_normalize_units`, `fill_bicarbonate_as_hco3` (append to
  `__all__`).

### `tests/test_io.py` (extended)

- `TestEquisflatNormalizeUnits` — single group rescaling (e.g. ng/L, ug/L,
  mg/L, g/L → one canonical unit with correct scaled values), inter-group
  independence (two parameters keep different canonical units), ties →
  lexicographically smallest, unrecognized units untouched, `inplace`
  semantics, input never mutated when `inplace=False`.
- `TestFillBicarbonateAsHco3` — known pH 25 °C speciation fractions (pH 8.3:
  f ≈ 0.97–0.98; pH 10.3: f ≈ 1.0 dominated by carbonate), NaN pH → NaN,
  missing column raises, temperature column path, `inplace` semantics.

## Acceptance criteria

- [ ] Prefix normalization is deterministic and group-scoped; unrecognized
      units pass through untouched
- [ ] `fill_bicarbonate_as_hco3` returns the documented speciation formula
      (validated against hand-computed fractions at 25 °C)
- [ ] Input frames not mutated unless `inplace=True`; no new required
      dependencies
- [ ] Both exported from `geofig_engine.io`
- [ ] Full suite green; committed as a single commit
      (`geofig-engine: io unit utilities → v0.3.0`)

## Files

- `src/geofig_engine/io/units.py` (new)
- `src/geofig_engine/io/__init__.py`
- `tests/test_io.py`