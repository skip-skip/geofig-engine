# WP-A: Secondary axis data model + mapping helpers

**Status**: open
**Phase**: 14.53
**Depends on**: none

## Description

Define the declarative data model for secondary cartesian axes (secondary x and
secondary y) and the pure helpers that map secondary-axis values onto primary
local coordinates. Secondary axes are declared as structured entries in a child
spec's `settings` (consistent with the frame-hints-in-settings refactor of 14.52).

## Changes

- Add a normalized reader that, given a child's `settings`, returns validated
  `secondary_x` / `secondary_y` declarations (present/absent, and their fields):
  - `range`: `[min, max]` of the secondary axis data scale (required to enable)
  - `tick_step`: label spacing on the secondary scale (default = primary `tick_step`)
  - `label_policy`: `"upright"` or `"parallel"` (default = primary `label_policy`)
  - `position`: edge to draw on (`"top"` for x, `"right"` for y; allow override)
  - `label`: optional axis title (e.g. `"Anions (%)"`)
- Add a pure linear mapping helper derived from primary range (from `xlim`/`ylim`)
  onto the secondary `range`: `fwd(primary)->secondary` and `inv(secondary)->primary`.
  Assert the secondary range is invertible (min != max) and both ranges are
  length-2 numeric.
- Provide a small function to enumerate the secondary tick values + their local
  coordinates: step `range` at `tick_step`, map each via `inv` into the primary
  (local-frame) coordinate.

## Design notes

- `range=[100, 0]` on a `[0,100]` primary produces the reversed/complement scale
  the piper diamond needs; arbitrary ranges generalize beyond reversal.
- Keep the helpers pure (no matplotlib imports) so they can be unit-tested and
  reused by the frame renderer and the coord/data path (WP-B/WP-D).

## Verification

- [ ] `inv(fwd(p)) == p` for representative values including reversed ranges
- [ ] Secondary declarations parse from settings; malformed ones raise ValueError

## Files

- `src/geofig_engine/` (new module or `core/` helper)
- `tests/test_secondary_axis.py` (new)
