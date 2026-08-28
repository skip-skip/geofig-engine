# WP12: Cleanup + ROADMAP + close task files

**Status**: open
**Phase**: 14.52
**Depends on**: 14_52_wp7..wp11

## Description

Final pass: remove all remaining `frame_config` references, verify full suite + demos,
document in ROADMAP, close the WP7-12 task files.

## Changes

- Grep `frame_config` across `src/`, `examples/`, `tests/`, `docs/` — expect zero
- Confirm `settings` is the single carrier of frame hints for children
- `ROADMAP.md`: update Phase 14.52 WP2/WP3 notes that reference frame_config to settings
- Move WP7-WP12 task files to `tasks/closed/`

## Verification

- [ ] `python -m pytest tests/ -q` — all pass
- [ ] `python examples/hydro_demo.py` — 7 figures render; diamond frame/grid/labels/title correct
- [ ] `python examples/debug_piper_axes.py` — geometry unchanged
- [ ] Task files WP7-WP12 moved to `tasks/closed/`

## Files

- `ROADMAP.md`
- `tasks/` (move files to `closed/`)
