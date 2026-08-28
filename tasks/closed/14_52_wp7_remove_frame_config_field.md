# WP7: Remove `frame_config` field from FigureSpec

**Status**: open
**Phase**: 14.52
**Depends on**: WP1-WP6 (Phase 14.52 core)

## Description

Fold frame-drawing hints (title, xlim, ylim, grid_step, tick_step, label_policy) out of
the separate `frame_config` field and into each spec's existing `settings` dict. This WP
removes the field from `FigureSpec` and its factory.

## Changes

- `src/geofig_engine/core/spec.py`
  - Remove `frame_config: dict | None = None` field (line ~68)
  - Remove `frame_config` param from `build_spec(...)` signature (line ~142) and its pass-through (~180)
  - Remove `frame_config` validation block (lines ~124-127)
  - Update docstrings (lines ~51-54, ~159)
- `tests/test_links.py`
  - `test_build_spec_accepts_frame_config` -> settings-based equivalent
  - `test_invalid_frame_config_raises` -> remove or repurpose

## Verification

- [ ] `FigureSpec`/`build_spec` no longer accept `frame_config`
- [ ] `tests/test_links.py` validation tests pass

## Files

- `src/geofig_engine/core/spec.py`
- `tests/test_links.py`
