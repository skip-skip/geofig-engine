# WP-C: Piper diamond integration (upper-edge reversed secondary axes)

**Status**: open
**Phase**: 14.53
**Depends on**: 14_53_wpa_secondary_axis_model.md, 14_53_wpb_secondary_axis_render.md

## Description

Wire the general secondary-axis system into the piper template so the diamond
carries reversed "secondary axis" tick labels on its two upper edges, like
secondary axes whose numbers are the reverse of the main axes.

## Changes

- `src/geofig_engine/templates/piper.py`
  - Add `secondary_x` and `secondary_y` to the diamond child's `settings`:
    - `secondary_x`: `{"range": [100, 0], "tick_step": 20, "label": "..."}` (drawn top)
    - `secondary_y`: `{"range": [100, 0], "tick_step": 20, "label": "..."}` (drawn right)
  - Choose sensible labels for the anion/cation complement axes.
- `examples/debug_piper_axes.py`
  - Mirror the diamond settings additions.
  - Update the printed/asserted `texts:` count (secondary ticks add labels).

## Design notes

- Because ranges are `[100,0]` on a `[0,100]` primary, the top edge reads
  80/60/40/20 (descending) and the right edge likewise — the reversed scales.
- Verify the diamond's rotated geometry places these labels on the true upper
  slanted edges (local top/right after the 45° transform).

## Verification

- [ ] `python examples/debug_piper_axes.py` renders; diamond shows reversed upper-edge ticks
- [ ] `python examples/hydro_demo.py` renders all 7 figures
- [ ] `tests/test_piper.py` asserts the diamond carries the secondary settings

## Files

- `src/geofig_engine/templates/piper.py`
- `examples/debug_piper_axes.py`
- `tests/test_piper.py`
