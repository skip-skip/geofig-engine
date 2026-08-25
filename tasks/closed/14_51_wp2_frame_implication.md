# WP2: Frame implication — auto-select frame from coord type

**Status**: open
**Phase**: 14.51
**Depends on**: `14_51_wp1_core_model`

## Description

The frame (border, grid, tick labels, ion arrows) should be implied by the child FigureSpec's coordinate space and transform, not by an explicit `frame` dict with a string provider key. The renderer auto-selects the frame drawing function based on `isinstance(child.coord, ...)`.

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py`

Add new dispatcher method:
```python
def _draw_implied_frame(self, ax, child: FigureSpec):
    matrix = child.transform.matrix()
    cfg = child.frame_config or {}
    if isinstance(child.coord, TernaryCoord):
        self._draw_ternary_frame(ax, matrix, child.coord, cfg)
    elif child.transform.rotate != 0:
        self._draw_diamond_frame(ax, matrix, cfg)
    else:
        self._draw_box_frame(ax, matrix, cfg)
```

Refactor `_piper_ternary_frame(ax, matrix, coord, frame_config)`:
- Read `ions` from `coord.channels` (the ternary channels ARE the ions)
- Read reversals from `coord.handedness`:
  - `handedness="left"` → `rev_bottom=True, rev_right=True`
  - `handedness="right"` → `rev_left=True`
- Read `title` from `frame_config.get("title", "")`
- Read `label_policy` from `frame_config.get("label_policy", "upright")`

Refactor `_piper_diamond_frame(ax, matrix, frame_config)`:
- Read `title` from `frame_config.get("title", "")`
- Read `label_policy` from `frame_config.get("label_policy", "upright")`

Remove `@frame_provider` decorator and `_FRAME_PROVIDERS` registry dict. The dispatch is now via `isinstance` checks in `_draw_implied_frame`.

### `src/geofig_engine/renderers/matplotlib/renderer.py` — label_rotation

Keep `label_rotation()` as-is (it's a pure function used by the frame drawing code).

## Acceptance criteria

- [ ] `_draw_implied_frame(ax, child)` selects the correct frame based on coord type
- [ ] Ternary frame reads ions from `coord.channels`, reversals from `coord.handedness`
- [ ] Diamond frame reads title from `frame_config`
- [ ] `_FRAME_PROVIDERS` registry dict is deleted
- [ ] `@frame_provider` decorator is deleted
- [ ] Frame drawing functions accept `(ax, matrix, coord, frame_config)` signature
- [ ] Full test suite passes

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
