# WP-M: Tests for reversal flags + cartesian normalization (tests/)

**Status**: complete
**Phase**: 14.55
**Dependencies**: `14_55_wpi_reverse_flag_model.md`, `14_55_wpj_cartesian_normalize_range.md`, `14_55_wpk_cartesian_reverse_arrows.md`, `14_55_wpl_piper_template_reverse.md`

## Description

Add test coverage for the reversal model, the range-normalisation fix, and the
arrow/label reversal behavior, and keep the existing suite green. Follow the
existing `tests/test_axis_format.py` helpers/patterns (`_render_child`,
`TICK_TEXT_SETTINGS`, arrow count + geometry assertions via
`matplotlib.text.Annotation`).

## Changes

### `tests/test_axis_format.py`

- **Model/parse**: `x_reversed`/`y_reversed` default `False`, round-trip `True`,
  reject non-bool (`"nope"`, `1`).
- **Range normalization**: a frame declared `xlim=(100,0), ylim=(100,0)` renders
  a **non-empty grid** and **non-empty primary ticks**; secondary titles land
  above/right (not lower/corner).
- **Arrow reversal**: with `x_reversed=True`, the primary x arrowhead lands on the
  **decreasing-data** end (flips vs `False`); `y_reversed=True` mirrors. Arrows
  always point toward increasing data.
- **Reversed tick labels**: primary bottom/left tick labels read high→low.

### `tests/test_piper.py`

- Update `test_children_have_settings` for the diamond's new
  `xlim`/`ylim (0,100)` + `x_reversed`/`y_reversed True` settings.

## Acceptance criteria

- [ ] New model/parse/validation tests pass
- [ ] New normalization tests pass (grid + ticks non-empty under descending limits)
- [ ] New reversal arrow-direction tests pass
- [ ] Reversed-tick-label test passes
- [ ] Updated `test_piper.py` passes
- [ ] Full suite green (no existing-test regressions)

## Files

- `tests/test_axis_format.py`
- `tests/test_piper.py`
