# Per-layer zorder control

**Status**: open
**Phase**: 13
**Dependencies**: none

## Description

Make layer z-order configurable per layer. Currently the renderer auto-assigns zorder: data layers start at 10 and increment, function lines start at 1. Users need explicit control to place annotation layers (rects, ablines) behind or in front of data.

### Approach

1. **Add `zorder` field to `LayerSpec`** — optional int, defaults to `None` (auto)
   ```python
   @dataclass(frozen=True)
   class LayerSpec:
       geom: Geom
       stat: Stat
       visual_mapping: dict[str, Any]
       data_override: str | None = None
       coord: Any = None
       zorder: int | None = None
   ```

2. **Modify `_render_axes`** in `renderer.py` — for each layer, if `layer.zorder is not None`, use that value instead of the auto-increment:
   ```python
   order = layer.zorder if layer.zorder is not None else (10 + data_idx)
   ```

3. **Pass `zorder` through `_apply_coord_transform`** — preserve `zorder` when rebuilding LayerSpec during coord transform.

4. **Thread `zorder` from `Layer` → `LayerSpec`** — add `zorder` field to `Layer` (the user-facing Layer, not just the resolved LayerSpec) and propagate it in `_resolve_layers`.

### Usage
```python
Layer(
    geom=GeomRect(...),
    stat=StatIdentity(),
    mapping={"xmin": 0, "xmax": 5, "ymin": 0, "ymax": 10},
    zorder=0,  # behind data layers
)
```

## Files to modify

- `src/geofig_engine/core/layer.py` — add `zorder: int | None = None` to both `Layer` and `LayerSpec`
- `src/geofig_engine/engine/generator.py` — propagate `layer.zorder` into `LayerSpec` in `_resolve_layers()`
- `src/geofig_engine/renderers/matplotlib/renderer.py` — use `layer.zorder` in `_render_axes()` when set; preserve in `_apply_coord_transform()`
- `src/geofig_engine/serialize/converters.py` — include `zorder` in `layer_spec_to_dict`/`layer_spec_from_dict`

## Acceptance criteria

- [ ] `Layer` and `LayerSpec` have optional `zorder: int | None` field
- [ ] When `zorder` is set on a Layer, it propagates through the generator into LayerSpec
- [ ] `_render_axes()` uses `layer.zorder` when not None, falls back to auto-increment when None
- [ ] `_apply_coord_transform()` preserves zorder through the spec rebuild
- [ ] Serialization round-trips include `zorder` field
- [ ] Explicit zorder=0 renders behind data layers (which default to 10+)
- [ ] Backward compatible — all existing layers without zorder use auto-increment
- [ ] All 486 existing tests still pass
