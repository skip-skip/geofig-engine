# WP-H: Fix pre-existing piper test failures from the layout change

**Status**: open
**Phase**: 14.53 (follow-up; ahead of WP-C piper integration)
**Depends on**: none

## Description

The committed layout change (`c1c69b3` "Adjust piper layout") shifted the right
triangle and diamond positions and dropped the per-panel titles, but the piper
tests still assert the OLD transform values and per-panel `title` settings. This
leaves the test suite red (4 failures). Reconcile the tests with the committed
layout so the suite passes.

## Current failures (`tests/test_piper.py`)

1. `TestBuildPiperSpecs::test_right_child_has_ternary_coord_and_transform`
   - asserts `right.transform.ops` translate `(1.0, 0.0)`; code now `(1.2, 0.1)`
2. `TestBuildPiperSpecs::test_diamond_child_is_cartesian`
   - asserts `m[0, 2] == 0.5`; code's `.translate(0.6, 0.0)` gives `0.6`
3. `TestBuildPiperSpecs::test_children_have_settings`
   - asserts per-panel `title` ("LEFT TRIANGLE" / "RIGHT TRIANGLE" / "DIAMOND");
     titles were removed
4. `TestPiperParity::test_diamond_positions_match_legacy`
   - asserts legacy world corner positions `[[0.5,0],...]`; code now centered at x=0.6

## Changes

- Decide how the layout change is meant to be interpreted (keep the committed
  positions and dropped titles, or revise), then align `tests/test_piper.py`:
  - Update the right-triangle transform expectation to the new translate.
  - Update the diamond translate / world-corner expectations.
  - Update/adjust the `settings` assertions (titles removed; verify what the
    settings now contain — e.g. diamond still carries `xlim`/`ylim`/`grid_step`/
    `tick_step`, which WP-C later extends with secondary axes).
- Confirm the underlying `models/hydro_demo` / piper figure still renders sanely
  with the new layout before locking in assertions.

## Verification

- [ ] `python -m pytest tests/test_piper.py -q` — all pass
- [ ] `python -m pytest tests/ -q` — full suite green
- [ ] `python examples/hydro_demo.py` — piper panel layout looks intentional

## Files

- `tests/test_piper.py`
