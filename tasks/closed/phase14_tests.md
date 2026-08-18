# Phase 14 test suite

**Status**: open
**Phase**: 14
**Dependencies**: `piper_utils`, `piper_template`, `stiff_diagram`, `classification_templates`

## Description

Write pytest tests covering all Phase 14 additions.

### Test areas

**Chemistry utilities** (unit tests)
- `meq_per_l()` for each common ion
- `convert_to_meq()` multi-column conversion
- `fill_bicarbonate_as_hco3()` computation
- `combined_na_k()` computation
- NaN/edge-case handling

**Piper diagram** (integration tests)
- `PiperCoord` construction and serialization
- `build_piper_specs()` returns valid FigureSpec with piper_layout setting
- Renderer dispatches to `_render_piper()` for PiperCoord
- 3-panel figure has correct structure (3 axes, proper projections)
- `piper_overlay_diamond()` returns modified spec

**Stiff diagram** (integration tests)
- `plot_stiff()` returns valid FigureSpec
- Rendered figure has correct number of axes/patches
- Ion values are positioned correctly (left vs right side)

**Classification templates** (integration tests)
- `npr_nnp()` builds template with correct layers
- `anp_agp()` builds template with correct layers
- `nagph_nag()` builds template with correct layers
- All three render without errors via `render_template()`

### Regression
- All 526 existing tests still pass

## Files to create

- `tests/test_chemistry.py` — chemistry utility tests
- `tests/test_piper.py` — PiperCoord + template tests
- `tests/test_stiff.py` — Stiff diagram tests
- `tests/test_classification_templates.py` — NPR/NNP, ANP/AGP, NAGpH tests

## Acceptance criteria

- [ ] At least 40 test cases across all 4 test files
- [ ] All tests pass with `conda run -n figengine pytest -x --tb=short`
- [ ] 526 existing tests have zero regressions
