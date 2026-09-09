# Phase 14.59: Piper zero-stub regression

**Status**: complete
**Phase**: 14.59
**Dependencies**: `14_59_wp10_majortick_renderer`

## Description

Guarantee the piper diamond stays clean after the majortick generalization.
Before the renderer change, `f21ca8c` introduced inward nubs on piper's
numeric diamond edge; the gate (`majortick_length is None` => no nubs) must
keep piper exactly as it was. Add a render regression: `build_piper_specs`
produces zero short stub segments on the diamond child's axes (scan by 2-pt
segment length, since the 45-degree transform makes nubs diagonal).

## Files to modify

- `tests/test_piper.py`

## Acceptance criteria

- [ ] Piper diamond render asserts zero majortick stub segments
- [ ] Existing piper tests unchanged and passing