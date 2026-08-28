# WP9: Piper template + demo fold frame_config into settings

**Status**: open
**Phase**: 14.52
**Depends on**: 14_52_wp7_remove_frame_config_field.md, 14_52_wp8_renderer_settings_frames.md

## Description

Update `build_piper_specs` and the debug demo so child specs carry frame hints in
`settings` instead of `frame_config`.

## Changes

- `src/geofig_engine/templates/piper.py`
  - Left/right triangle children: `frame_config={"title": ...}` -> merge `title` into `settings`
  - Diamond child: fold `frame_config` keys into `settings`:
    `{"title": "DIAMOND", "xlim": (0,100), "ylim": (0,100), "grid_step": 20, "tick_step": 20}`
  - Update module docstring if it references frame_config
- `examples/debug_piper_axes.py`
  - Any `frame_config=` -> `settings=`

## Verification

- [ ] `build_piper_specs` children have correct settings (title/bounds/steps)
- [ ] `python examples/debug_piper_axes.py` renders; geometry unchanged

## Files

- `src/geofig_engine/templates/piper.py`
- `examples/debug_piper_axes.py`
