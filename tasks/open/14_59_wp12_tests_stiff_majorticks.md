# Phase 14.59: Update stiff majortick tests

**Status**: open
**Phase**: 14.59
**Dependencies**: `14_59_wp10_majortick_renderer`, `14_59_wp11_stiff_majorticks`

## Description

Update the existing stiff majortick regression test in `tests/test_stiff.py`
(to the new parameter names/geometry) and extend it with styling asserts.

Current `test_x_axis_tick_marks_at_interval_numbers` is renamed to
`test_x_axis_majorticks_at_interval_numbers` and asserts:

- nubs at x = -20, -10, 0, 10, 20 spanning exactly `[ylo - 0.06, ylo]`
- `linewidth == 1.0` and `color == "black"` on the tick artists

## Files to modify

- `tests/test_stiff.py`

## Acceptance criteria

- [ ] Test renamed to majortick vocabulary
- [ ] Span assert `[ylo - 0.06, ylo]` (exterior, per `majortick_offset: 0`)
- [ ] `linewidth`/`color` asserted from the new `majortick_width`/`_color`
- [ ] Existing render smoke tests (labels, caption, no dotted grid) still pass