# WP-N: Verify reversal series — full suite + regenerate piper outputs

**Status**: complete
**Phase**: 14.55
**Dependencies**: `14_55_wpi_reverse_flag_model.md`, `14_55_wpj_cartesian_normalize_range.md`, `14_55_wpk_cartesian_reverse_arrows.md`, `14_55_wpl_piper_template_reverse.md`, `14_55_wpm_tests.md`

## Description

Run the full test suite and regenerate the example piper outputs, then confirm
the diamond renders correctly (grid, ticks, titles, arrow directions) under the
new normalized + reversed settings. `examples/outputs/` is git-ignored, so these
files are artifacts for visual confirmation only.

## Changes

- Run the full test suite (expect 926+ passing; no regressions).
- Regenerate `examples/outputs/hydro_demo/01_piper.png` and
  `examples/outputs/piper_axes_debug.png`.
- Visually inspect the diamond: grid present, primary/secondary ticks present,
  "Anions (%)"/"Cations (%)" on the upper/right edges, arrows pointing toward
  increasing data and consistent with the reversed labels.

## Acceptance criteria

- [ ] Full test suite passes (existing + new)
- [ ] `01_piper.png` regenerated; diamond grid/ticks/titles/arrows render correctly
- [ ] `piper_axes_debug.png` regenerated
- [ ] Any discrepancy between the rendered diamond and the intended look is
  reported (and, if a settings tuning is needed, captured as a follow-up WP rather
  than silently changed)

## Files

- `examples/hydro_demo.py`, `examples/debug_piper_axes.py` (sources)
- `examples/outputs/` (git-ignored artifacts)
