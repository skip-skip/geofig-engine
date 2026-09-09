# Phase 14.59: Verify majortick implementation

**Status**: open
**Phase**: 14.59
**Dependencies**: `14_59_wp8_majortick_axis_model`, `14_59_wp9_majortick_secondary`, `14_59_wp10_majortick_renderer`, `14_59_wp11_stiff_majorticks`, `14_59_wp12_tests_stiff_majorticks`, `14_59_wp13_tests_offset_edges`, `14_59_wp14_tests_named_secondary`, `14_59_wp15_tests_piper_regression`

## Description

Full verification gate for the majortick work:

- Full test suite (`python -m pytest -q`)
- Ruff on all modified files, net-clean vs the pre-change baseline (no new
  findings)
- Numeric geometry spot-checks: stiff x ruler nubs span `[ylo - 0.06, ylo]`,
  piper has zero stub segments, offset variants land on the right tips
- Regenerate example figures (`$env:MPLBACKEND='Agg'; python
  examples/hydro_demo.py`) — all 7 figures produce output

## Files to modify

- none (verification only)

## Acceptance criteria

- [ ] `python -m pytest -q` green (baseline 1043 + new tests)
- [ ] Ruff no-new-findings on changed files
- [ ] Numeric geometry spot-checks pass
- [ ] `hydro_demo.py` regenerates all 7 figures