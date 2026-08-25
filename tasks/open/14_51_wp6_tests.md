# WP6: Tests — update linked-axes tests for nested FigureSpec

**Status**: open
**Phase**: 14.51
**Depends on**: `14_51_wp4_piper_template`, `14_51_wp5_serialization`

## Description

Update all tests that reference `AxisLink`, `spec.links`, `layer.subplot`, or `piper_overlay_diamond`. Rewrite `test_links.py` to test FigureSpec children validation and LinkTransform math. Update `test_piper.py` and `test_linked_render.py` for the new spec structure.

## Changes

### `tests/test_links.py`

Rewrite entirely:
- Test `FigureSpec.children` validation (depth-1, type checking)
- Test `LinkTransform.matrix()` (rotate→scale→translate order)
- Test `LinkTransform.transform_point` / `transform_points`
- Test `label_rotation` (upright and parallel policies)
- Remove all `AxisLink` tests

### `tests/test_piper.py`

Update spec construction assertions:
- `spec.children` has 3 entries instead of `spec.links`
- Each child has `coord`, `transform`, `layers` fields
- Layers have no `subplot` field
- Layer visual_mappings are the same (ion columns + visual passthrough)
- Remove `piper_overlay_diamond` tests
- Parity tests: verify LinkTransform maps percentage data to correct diamond vertices

### `tests/test_linked_render.py`

Update:
- Engine `build_specs_from_template` returns specs with children
- Serialization round-trip uses recursive children
- Remove `subplot` from layer assertions

### `tests/test_stat_ion_fractions.py`

Unchanged (doesn't touch links/layers routing).

## Acceptance criteria

- [ ] `test_links.py` rewritten for FigureSpec children + LinkTransform
- [ ] `test_piper.py` updated: spec has children, layers have no subplot
- [ ] `test_linked_render.py` updated: serialization round-trip with children
- [ ] `piper_overlay_diamond` tests removed
- [ ] All 818+ tests pass (some removed, some added, net count may change)
- [ ] No test uses `AxisLink`, `spec.links`, `layer.subplot`, or `piper_overlay_diamond`

## Files

- `tests/test_links.py`
- `tests/test_piper.py`
- `tests/test_linked_render.py`
