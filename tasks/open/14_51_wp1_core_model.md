# WP1: Core model — nested FigureSpec, simplified LayerSpec, delete AxisLink

**Status**: open
**Phase**: 14.51
**Depends on**: none (first WP)

## Description

Refactor the core data model so linked axes are represented as child FigureSpecs instead of AxisLink objects. This is the foundation all subsequent WPs build on.

## Changes

### `src/geofig_engine/core/spec.py` — FigureSpec

Add three fields:
```python
children: tuple[FigureSpec, ...] = ()
transform: LinkTransform = field(default_factory=LinkTransform)
frame_config: dict | None = None
```

Remove two fields:
```python
# REMOVED: links: tuple[AxisLink, ...] = ()
# REMOVED: root_transform: LinkTransform | None = None
```

Update `validate_figure_spec()`:
- Validate `children` are `FigureSpec` instances
- Validate depth-1 only (children must not have their own children)
- Remove link name uniqueness check
- Remove subplot routing validation

### `src/geofig_engine/core/layer.py` — LayerSpec

Remove two fields:
```python
# REMOVED: subplot: str | None = None
# REMOVED: coord: Any = None
```

### `src/geofig_engine/core/link.py`

Delete `AxisLink` class entirely. Keep `LinkTransform` and `label_rotation`.

### `src/geofig_engine/core/spec.py` — `build_spec()`

Update signature:
- Remove `links` parameter
- Remove `root_transform` parameter
- Add `children` parameter
- Add `transform` parameter
- Add `frame_config` parameter

## Acceptance criteria

- [ ] `FigureSpec` has `children`, `transform`, `frame_config` fields
- [ ] `FigureSpec` no longer has `links` or `root_transform` fields
- [ ] `LayerSpec` no longer has `subplot` or `coord` fields
- [ ] `AxisLink` class is deleted from `link.py`
- [ ] `LinkTransform` and `label_rotation` remain in `link.py`
- [ ] `validate_figure_spec()` validates children are FigureSpec instances at depth-1
- [ ] `build_spec()` accepts and forwards new fields
- [ ] Full test suite passes (tests will need updating — see WP6)

## Files

- `src/geofig_engine/core/spec.py`
- `src/geofig_engine/core/layer.py`
- `src/geofig_engine/core/link.py`
