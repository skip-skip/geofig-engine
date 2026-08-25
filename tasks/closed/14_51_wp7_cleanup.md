# WP7: Cleanup — dead code, debug demo, ROADMAP

**Status**: open
**Phase**: 14.51
**Depends on**: `14_51_wp6_tests`

## Description

Final cleanup pass: remove any remaining dead code, update the debug demo, verify the hydro demo works, and update ROADMAP.md.

## Changes

### `examples/debug_piper_axes.py`

Update to use the new children API:
- Build a FigureSpec with children instead of links
- Verify frames render correctly with implied frame logic
- Check no orange rectangle artifact

### `examples/hydro_demo.py`

Run and verify output — should work unchanged since it uses `build_piper_specs` which is rewritten internally.

### Dead code removal

- Remove any remaining `AxisLink` imports across the codebase
- Remove any `subplot` references in non-test code
- Remove `piper_overlay_diamond` from all imports/exports
- Clean up any unused `_FRAME_PROVIDERS` references

### `ROADMAP.md`

- Mark Phase 14.51 as complete
- Note the architectural change: linked axes → nested FigureSpecs
- Update test count

## Acceptance criteria

- [ ] `debug_piper_axes.py` works with new API, no orange artifact
- [ ] `hydro_demo.py` produces correct output
- [ ] No dead `AxisLink` / `subplot` / `piper_overlay_diamond` references remain
- [ ] ROADMAP updated with Phase 14.51 summary
- [ ] Full test suite passes
- [ ] All demo images visually correct

## Files

- `examples/debug_piper_axes.py`
- `examples/hydro_demo.py` (verify only)
- `ROADMAP.md`
- Various source files (dead import cleanup)
