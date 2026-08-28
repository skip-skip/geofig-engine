# WP11: Tests use settings-based assertions

**Status**: open
**Phase**: 14.52
**Depends on**: 14_52_wp7_remove_frame_config_field.md, 14_52_wp10_serializer_settings.md

## Description

Update tests that referenced `frame_config` to assert against `settings`, and adjust
frame-render tests to pass settings instead of frame_config.

## Changes

- `tests/test_piper.py`
  - `test_children_have_frame_config` -> `test_children_have_settings`
  - assert `left.settings["title"] == "LEFT TRIANGLE"`, and diamond
    `settings["xlim"] == (0,100)`, `settings["ylim"] == (0,100)`, `settings["grid_step"] == 20`
- `tests/test_linked_render.py`
  - `_child_spec(...)` helper (line ~59): replace `frame_config=` kwarg with settings
  - frame tests (line ~145 triangle, ~163 diamond): pass settings
  - `test_no_frame_when_no_frame_config_and_identity_transform` (~177): no frame when no
    xlim/ylim bounds in settings

## Verification

- [ ] All updated tests pass

## Files

- `tests/test_piper.py`
- `tests/test_linked_render.py`
