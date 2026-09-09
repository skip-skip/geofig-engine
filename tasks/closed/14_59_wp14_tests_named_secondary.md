# Phase 14.59: Named-edge and secondary majortick tests

**Status**: closed
**Phase**: 14.59
**Dependencies**: `14_59_wp10_majortick_renderer`, `14_59_wp13_tests_offset_edges`

## Description

Cover the two non-numeric paths majorticks now serve:

1. **Named edges** — a frame with `y_tick_labels` (left) and a secondary with
   `tick_labels` (right). Majorticks must be drawn at the exact label
   positions, including frame edges (y = ylo and y = yhi get ticks too), not
   skipped like interior numeric ticks.
2. **Secondary inheritance** — a `parse_secondary_settings` unit test that a
   secondary dict omitting `majortick_length`/`majortick_offset`/
   `majortick_width`/`majortick_color` inherits the frame-level values, and a
   render test that the top (secondary x) edge draws nubs when the frame sets
   the length.

## Files to modify

- `tests/test_stiff.py` (named edges via the stiff spec's left/right rows)
- `tests/test_secondary_axis.py` (inheritance unit test)

## Acceptance criteria

- [ ] Named left/right edges produce ticks at all named positions incl. edges
- [ ] Frame-level majortick values inherited when secondary omits them
- [ ] Per-secondary override beats the frame-level fallback
- [ ] Top-edge (secondary x) nubs render when the frame sets `majortick_length`