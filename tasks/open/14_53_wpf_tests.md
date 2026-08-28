# WP-F: Tests for secondary axis system

**Status**: open
**Phase**: 14.53
**Depends on**: 14_53_wpa..wpe

## Description

Add and update tests covering the secondary-axis data model, linear mapping, frame
tick-label rendering, data twin-axis, serialization, and the piper integration.

## Changes

- New `tests/test_secondary_axis.py`
  - Linear mapping: `fwd`/`inv` round-trips; reversed ranges (`[100,0]`) produce
    descending local coordinates; non-invertible range raises.
  - Frame rendering: secondary x ticks appear on the top edge and secondary y on
    the right edge at correct world positions (reversed, e.g. 80/60/40/20).
  - Data twin-axis: a `y2` layer lands where the secondary→primary mapping predicts.
  - Errors: `x2`/`y2` without a matching secondary declaration raises.
- `tests/test_linked_render.py`
  - `test_diamond_frame_renders`: add secondary settings and assert the reversed
    upper-edge labels are present; update any text-count assumptions.
- `tests/test_piper.py`
  - Assert the diamond child carries `secondary_x`/`secondary_y` with reversed ranges.
- `tests/test_links.py`
  - Serialization round-trip preserves `secondary_x`/`secondary_y` (tuple range).
  - Validation rejects malformed secondary-axis settings.

## Verification

- [ ] `python -m pytest tests/ -q` — all pass

## Files

- `tests/test_secondary_axis.py` (new)
- `tests/test_linked_render.py`
- `tests/test_piper.py`
- `tests/test_links.py`
