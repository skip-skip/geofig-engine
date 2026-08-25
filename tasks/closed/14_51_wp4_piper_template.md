# WP4: Piper template rewrite — children instead of links

**Status**: open
**Phase**: 14.51
**Depends on**: `14_51_wp3_renderer_refactor`

## Description

Rewrite `build_piper_specs` to construct child FigureSpecs instead of AxisLink objects. Remove `piper_overlay_diamond`. The template becomes simpler: each link axis is a self-contained FigureSpec with its own coord, transform, layers, and optional frame_config.

## Changes

### `src/geofig_engine/templates/piper.py`

Rewrite `build_piper_specs`:

```python
def build_piper_specs(data, left_tri, right_tri, mapping=None, title=""):
    # ... validate, compute percentages, augment data ...

    visuals = _resolve_visuals(data, mapping)

    left_vm = {ch: aug[ch] for ch in left_channels}
    left_vm.update(visuals)

    right_vm = {ch: aug[ch] for ch in right_channels}
    right_vm.update(visuals)

    dia_vm = {"x": aug["_dia_anion_pct"], "y": aug["_dia_cation_pct"]}
    dia_vm.update(visuals)

    left = FigureSpec(
        data=aug, mappings=mappings,
        coord=TernaryCoord(channels=left_channels, handedness="left"),
        transform=LinkTransform(scale=(0.5, 0.5)),
        frame_config={"title": "LEFT TRIANGLE"},
        layers=[LayerSpec(geom=GeomPoint(), stat=StatIdentity(),
                          visual_mapping=left_vm, zorder=10)],
    )
    right = FigureSpec(
        data=aug, mappings=mappings,
        coord=TernaryCoord(channels=right_channels, handedness="right"),
        transform=LinkTransform(scale=(-0.5, 0.5), translate=(1.0, 0.0)),
        frame_config={"title": "RIGHT TRIANGLE"},
        layers=[LayerSpec(geom=GeomPoint(), stat=StatIdentity(),
                          visual_mapping=right_vm, zorder=10)],
    )
    diamond = FigureSpec(
        data=aug, mappings=mappings,
        coord=CoordCartesian(),
        transform=LinkTransform(translate=(0.5, 0.0), rotate=45.0,
                                scale=(sqrt(2)/400, dia_pct*sqrt(2)/2)),
        layers=[LayerSpec(geom=GeomPoint(), stat=StatIdentity(),
                          visual_mapping=dia_vm, zorder=10)],
    )

    parent = FigureSpec(
        data=aug, mappings=mappings,
        settings={"figsize": (10, 8), "title": title},
        template_name="piper",
        children=(left, right, diamond),
    )
    return [parent]
```

Delete `piper_overlay_diamond` function entirely.

### `src/geofig_engine/templates/__init__.py`

Remove `piper_overlay_diamond` from exports.

## Acceptance criteria

- [ ] `build_piper_specs` returns a FigureSpec with 3 children
- [ ] Each child has its own `coord`, `transform`, `layers`
- [ ] No `AxisLink` objects created
- [ ] No `frame` dicts (only `frame_config` with optional title)
- [ ] `piper_overlay_diamond` is deleted
- [ ] `__init__.py` exports updated
- [ ] Visual output matches Phase 14.5 piper (same geometry, same labels)
- [ ] Full test suite passes (tests updated in WP6)

## Files

- `src/geofig_engine/templates/piper.py`
- `src/geofig_engine/templates/__init__.py`
