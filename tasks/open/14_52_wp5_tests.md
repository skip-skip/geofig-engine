# WP5: Tests

**Status**: open
**Phase**: 14.52
**Depends on**: 14_52_wp1_fluent_link_transform.md, 14_52_wp2_cartesian_axis_handler.md, 14_52_wp3_piper_template.md, 14_52_wp4_serialization.md

## Description

Update all tests to the fluent `LinkTransform` API and the generalized cartesian-axis handler. Assert against `matrix()` / `.ops` directly (no convenience accessors on `LinkTransform`).

## Changes

### `tests/test_links.py`

- `TestLinkTransformMath`: rewrite constructors fluently. Numeric expectations unchanged (semantics preserved). Assert against `matrix()` where field values were previously read.
- `TestLinkTransformValidation`:
  - Constructor-arg validation (e.g. `translate=(1,2,3)`) → fluent-method-arg validation (`.translate((1,2,3))` raises)
  - Frozen test → immutability test: calling a fluent method leaves the receiver unchanged
  - Assert against `.ops` for ordering
- `TestLinkTransformSerialization`: op-list round-trip
- `TestFigureSpecChildren`: rewrite `LinkTransform(...)` constructions fluently
- Update module docstring (lines 1-9) to describe fluent call-order semantics

### `tests/test_linked_render.py`

Rewrite all `LinkTransform(...)` constructions fluently (lines 38, 46, 68, 99, 116, 144, 159, 257, 273).
- `test_diamond_frame_renders` (line 155): add `"xlim": (0, 100), "ylim": (0, 100)` to `frame_config` so the generalized cartesian handler draws the correct box
- Verify `test_no_frame_when_no_frame_config_and_identity_transform` still holds (cartesian child, no frame_config → no frame)

### `tests/test_piper.py`

- Line 92: `left.transform == LinkTransform().scale(0.5, 0.5)`
- Line 100: `right.transform == LinkTransform().scale(-0.5, 0.5).translate(1.0, 0.0)`
- Lines 107-108 (`dia.transform.rotate`, `.translate`) → assert against `dia.transform.matrix()` / `.ops` directly
- Confirm diamond `frame_config` declares `[0,100]²` bounds

## Acceptance criteria

- [ ] All LinkTransform constructions use fluent API
- [ ] Validation/immutability tests assert against fluent methods and `.ops`
- [ ] Piper transform assertions use `matrix()` / `.ops` (no `.rotate`/`.translate` accessors)
- [ ] Diamond render test passes bounds in frame_config
- [ ] Full test suite passes

## Files

- `tests/test_links.py`
- `tests/test_linked_render.py`
- `tests/test_piper.py`
