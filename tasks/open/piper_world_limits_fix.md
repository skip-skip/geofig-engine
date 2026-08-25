# Fix `_linked_world_limits` to include routed layer data

**Status**: open
**Phase**: 14.5
**Depends on**: (none — first step)

## Description

`_linked_world_limits` in `renderer.py:514-555` skips all routed layers because of the guard at line 522:

```python
if layer.subplot is not None:
    continue
```

This means only link corner transforms contribute to axes bounds. For the diamond link (identity transform), corners are `[0,1]²`, but the actual data from `_compute_diamond_xy` spans `[-0.38, 0.35] × [-0.01, 0.18]`. Result: 50% of diamond data is clipped.

## Fix

Remove the `subplot is not None` skip. For routed layers, transform their x/y through the link matrix and include in the bounds computation. Keep the existing link-corner computation as a fallback for empty-data cases.

## Acceptance criteria

- [ ] All routed layer data contributes to world limits
- [ ] Diamond data points at negative x are no longer clipped
- [ ] Ternary data still renders within limits
- [ ] Full test suite passes

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py` — `_linked_world_limits()`
