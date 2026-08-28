# WP-G: Cleanup + ROADMAP + close task files

**Status**: open
**Phase**: 14.53
**Depends on**: 14_53_wpa..wpf

## Description

Final pass: verify the full suite + demos, document Phase 14.53 in ROADMAP, and
close the WP-A..G task files.

## Changes

- Grep for consistency (no leftover placeholder `y2scale` confusion; secondary-axis
  helpers/rendering consistent).
- `ROADMAP.md`: add a `## Phase 14.53` section (marked in-progress until done)
  documenting the general secondary-axis system for cartesian coordinates.
- Move WP-A..G task files from `tasks/open/` to `tasks/closed/`.

## Verification

- [ ] `python -m pytest tests/ -q` — all pass
- [ ] `python examples/hydro_demo.py` — all 7 figures render
- [ ] `python examples/debug_piper_axes.py` — diamond shows reversed upper-edge ticks
- [ ] Task files WP-A..G moved to `tasks/closed/`

## Files

- `ROADMAP.md`
- `tasks/` (move files to `closed/`)
