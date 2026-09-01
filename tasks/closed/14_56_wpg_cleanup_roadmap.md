# WP-G: Piper template + outputs + ROADMAP + commit

**Status**: complete
**Phase**: 14.56
**Dependencies**: `14_56_wpa_axis_font_model.md` .. `14_56_wpf_font_tests.md`

## Description

Close out the font-size work-package series: confirm the piper template needs no
knob overrides (it should pick up the unified `axis_label` default 7 and all other
built-in defaults), regenerate the affected example outputs, update the ROADMAP
Phase 14.56 entry, and commit the working-tree changes on `mapping-refactor`.

## Changes

### `src/geofig_engine/templates/piper.py`

- Optional: if any font rewiring changes the intended piper look beyond the
  approved Anion/Cation 6 -> 7 unification, decide whether to set explicit knobs.
  Default expectation: no change needed (uses built-in defaults).

### `examples/outputs/`

- Regenerate any outputs affected by the wiring: `hydro_demo/01_piper.png`,
  `piper_axes_debug.png`, and any native/facet example changed by WP-D / WP-E.
  (Note: `examples/outputs/` is git-ignored.)

### `ROADMAP.md`

- Add a `Phase 14.56 - Configurable font sizes for all text elements` section after
  14.55, documenting: the per-element knobs, the generic `fontsize` fallback, the
  `axis_label` unification (Anion/Cation 6 -> 7), and the updated test count.
- Do not claim stiffness labels are covered (stiff is out of scope).

### `tasks/`

- Move `14_56_wpa_axis_font_model.md` .. `14_56_wpg_cleanup_roadmap.md` from
  `tasks/open/` to `tasks/closed/`, setting `**Status**: complete` on each.

### Commit

- On branch `mapping-refactor`, message style `Phase 14.56 <desc>` (e.g.
  `Phase 14.56 WP-A..G: configurable font sizes for all text elements`).
- Include axis.py, renderer.py, legend.py, generator.py (if touched), tests, task
  files, ROADMAP. Do not stage/commit secrets or stray files.

## Acceptance criteria

- [x] Piper renders with unified `axis_label` (Anion/Cation 7) and default sizes elsewhere
- [x] All affected example outputs regenerated (git-ignored)
- [x] ROADMAP Phase 14.56 entry added with accurate test count; stiffness correctly excluded
- [x] All font WPs in `tasks/closed/` with `**Status**: complete`
- [x] `git status` staged set matches intended files
- [x] Commit created on `mapping-refactor` with a `Phase 14.56` message

## Implementation notes

- `piper.py` requires **no** knob override: it relies on built-in defaults, and the
  Anion/Cation secondary titles now pick up `axis_label` (default 7) automatically.
- Regenerated `hydro_demo` Piper outputs and `piper_axes_debug.png` (git-ignored).
- ROADMAP Phase 14.56 entry added (955 tests); stiffness labels explicitly excluded.
- Final commit: `Phase 14.56 WP-A..G: configurable font sizes for all text elements`.

## Files

- `src/geofig_engine/templates/piper.py` (only if a knob override is needed)
- `examples/outputs/` (git-ignored)
- `ROADMAP.md`
- `tasks/open/` -> `tasks/closed/`
- commit on `mapping-refactor`
