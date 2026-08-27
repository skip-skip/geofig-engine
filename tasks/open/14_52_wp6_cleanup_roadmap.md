# WP6: Cleanup + ROADMAP

**Status**: open
**Phase**: 14.52
**Depends on**: 14_52_wp1_fluent_link_transform.md, 14_52_wp2_cartesian_axis_handler.md, 14_52_wp3_piper_template.md, 14_52_wp4_serialization.md, 14_52_wp5_tests.md

## Description

Final pass: remove leftover references to the old `LinkTransform(translate=, rotate=, scale=)` form and `rotate != 0` diamond dispatch anywhere they remain, verify full suite + demo output, then document Phase 14.52 in ROADMAP.

## Changes

### Cleanup

- Grep for `LinkTransform(` constructor-form usages across `src/` and `examples/` — must be zero
- Grep for `.transform.rotate` / `.transform.translate` / `.transform.scale` attribute reads — must be zero (use `matrix()` / `.ops`)
- Grep for `_draw_diamond_frame` / `rotate != 0` dispatch — must be zero
- Confirm `_child_local_bbox` no longer checks `rotate`

### `ROADMAP.md`

Add a `## Phase 14.52` section (marked in-progress) documenting:
- Fluent orderable `LinkTransform` (call-order = point-op order)
- Generalized `_draw_cartesian_axis` handler replacing `_draw_diamond_frame`; dispatch by coord type + frame_config, removing the `rotate != 0` proxy
- Piper/debug demos declare diamond `[0,100]²` bounds in frame_config

### Verification

- [ ] `python -m pytest tests/ -q` — all pass
- [ ] `python examples/hydro_demo.py` — all 7 figures render; piper has consistent per-sample colors across panels, no solid-orange regression, correct diamond frame/grid/labels/title
- [ ] `python examples/debug_piper_axes.py` — frames-only output geometry matches prior (xlim/ylim/lines/texts)
- [ ] Move all 14.52 task files to `tasks/closed/`

## Acceptance criteria

- [ ] No `LinkTransform(...)` constructor-form or field reads remain
- [ ] No `_draw_diamond_frame` or `rotate != 0` dispatch remains
- [ ] Full test suite passes
- [ ] Demo figures render correctly
- [ ] ROADMAP Phase 14.52 documented
- [ ] Task files moved to `tasks/closed/`

## Files

- `ROADMAP.md`
- `tasks/` (move files to `closed/`)
