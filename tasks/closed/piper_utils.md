# Piper — chemistry utility functions

**Status**: open
**Phase**: 14
**Dependencies**: none

## Description

Implement the hydrogeochemistry calculation utilities needed by the Piper diagram template. These go in a new `geofig_engine.chemistry` subpackage.

### Functions

**`meq_per_l(mg_per_l: float, charge: int, molar_mass: float) -> float`**
Convert mg/L to meq/L: `meq/L = mg/L * charge / molar_mass`

**`ion_charge_mass_table() -> dict[str, tuple[int, float]]`**
Ion → (charge, molar mass) mapping for common ions:
- Ca: (+2, 40.08), Mg: (+2, 24.305), Na: (+1, 22.990), K: (+1, 39.098)
- HCO3: (-1, 61.017), CO3: (-2, 60.009), SO4: (-2, 96.06), Cl: (-1, 35.453)

**`convert_to_meq(df: pd.DataFrame, ion_map: dict[str, str]) -> pd.DataFrame`**
Convert multiple mg/L columns to meq/L using the ion table. `ion_map` maps column names to ion names (e.g., `{"Ca": "Ca", "Mg": "Mg"}`).

**`fill_bicarbonate_as_hco3(alkalinity_col: str, ph_col: str, temperature_c: float = 25.0) -> Callable`**
Returns a function that computes HCO3+CO3 from alkalinity + pH + temperature using temperature-dependent pKa1/pKa2.

**`combined_na_k(na_col: str, k_col: str) -> Callable`**
Returns a function that sums Na and K columns.

### Data-flow note
These are pure utility functions, not GoG components. They transform DataFrames *before* the spec-building pipeline. Users call them to prepare data, then pass the result to a template.

## Files to create

- `src/geofig_engine/chemistry/__init__.py` — export all functions
- `src/geofig_engine/chemistry/ion_utils.py` — meq conversion, ion table
- `src/geofig_engine/chemistry/alkalinity.py` — HCO3/CO3 from alkalinity + pH + temp

## Acceptance criteria

- [ ] `meq_per_l()` returns correct values for Ca, Mg, Na, K, HCO3, CO3, SO4, Cl
- [ ] `convert_to_meq()` converts multiple columns in one call
- [ ] `fill_bicarbonate_as_hco3()` returns a callable that adds an `hco3_meq` column
- [ ] `combined_na_k()` returns a callable that adds a `na_k_meq` column
- [ ] All functions handle missing values (NaN) gracefully
- [ ] No dependencies on `geofig_engine` core types (pure data transformations)
