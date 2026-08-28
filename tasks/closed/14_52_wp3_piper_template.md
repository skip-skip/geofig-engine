# WP3: Piper template + debug demo fluent rewrites

**Status**: open
**Phase**: 14.52
**Depends on**: 14_52_wp1_fluent_link_transform.md, 14_52_wp2_cartesian_axis_handler.md

## Description

Update `build_piper_specs()` and the debug demo to use the fluent `LinkTransform` API and to declare the diamond's `[0,100]²` bounds + grid/tick steps in `frame_config` (feeding the new cartesian-axis handler).

## Changes

### `src/geofig_engine/templates/piper.py`

- **Left triangle** (line 100): `LinkTransform().scale(0.5, 0.5)`
- **Right triangle** (line 116): `LinkTransform().scale(-0.5, 0.5).translate(1.0, 0.0)` (scale-then-translate to points — matches current `M = T·S`)
- **Diamond** (lines 126-145):
  ```python
  transform=LinkTransform().rotate(45.0).scale(_SQRT2/400.0, _SQRT6/400.0).translate(0.5, 0.0),
  frame_config={
      "title": "DIAMOND",
      "xlim": (0, 100), "ylim": (0, 100),
      "grid_step": 20, "tick_step": 20,
  },
  ```

### `examples/debug_piper_axes.py`

Mirror the same fluent rewrites; diamond `frame_config` gains `xlim=(0,100), ylim=(0,100), grid_step=20, tick_step=20`. Verify frames-only output geometry is unchanged (xlim/ylim/lines/texts).

## Acceptance criteria

- [ ] `build_piper_specs()` uses only fluent `LinkTransform` construction
- [ ] Diamond child declares `[0,100]²` bounds + grid/tick steps in `frame_config`
- [ ] Debug demo uses fluent API and declares diamond bounds
- [ ] Piper output geometry unchanged vs Phase 14.51 (same left/right/diamond layout, labels, colors)

## Files

- `src/geofig_engine/templates/piper.py`
- `examples/debug_piper_axes.py`
