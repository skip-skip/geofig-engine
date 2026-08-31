# WP-J: Cleanup + ROADMAP + close task files

**Status**: complete
**Phase**: 14.54
**Depends on**: 14_54_wpa..14_54_wpi

## Description

Final pass: verify the full suite + demos, document Phase 14.54 in ROADMAP.md,
and close the WP-A..J task files.

## Changes

- Grep for consistency: no leftover `settings` reads of flat axis keys in the
  renderer that should have migrated to `AxisFormat`; the single and child paths
  call the same `_draw_frame`; no reference to a `settings["axis"]` field that
  doesn't exist in `AxisFormat`.
- `ROADMAP.md`: add a `## ✅ Phase 14.54 — Unified axis/frame rendering pipeline`
  section documenting:
  - `AxisFormat` model (`core/axis.py` + `settings["axis"]`) with common +
    per-coord `options` + appearance knobs.
  - Unified `_draw_frame` entry used by BOTH top-level and child specs
    (cartesian/ternary/polar).
  - Custom polar frame.
  - Unification of the single path with the children pipeline (identity
    transform); top-level ternary now draws a frame (parity fix).
  - Facet path consuming `AxisFormat` per panel.
  - `tick_format` capability, validation, serialization tuple restoration
    (incl. `figsize`).
  - Template migration to `settings["axis"]`.
  - Note `y2scale` intentionally left untouched.
- Move WP-A..J task files from `tasks/open/` to `tasks/closed/`.

## Verification

- [ ] `python -m pytest tests/ -q` — all pass
- [ ] `python examples/hydro_demo.py` — all 7 figures render, appearance preserved
- [ ] `python examples/debug_piper_axes.py` — diamond unchanged (children path)
- [ ] Task files WP-A..J moved to `tasks/closed/`

## Files

- `ROADMAP.md`
- `tasks/` (move WP-A..J to `closed/`)
