# WP5: Serialization — recursive children, transform, frame_config

**Status**: open
**Phase**: 14.51
**Depends on**: `14_51_wp1_core_model`

## Description

Update the serialization layer to handle the new FigureSpec structure: recursive `children`, per-spec `transform`, and `frame_config`. Remove `AxisLink` serialization.

## Changes

### `src/geofig_engine/serialize/converters.py`

Replace `link_to_dict` / `link_from_dict` with recursive spec serialization:

```python
def _spec_to_dict(spec: FigureSpec) -> dict:
    return {
        "data": spec.data.to_dict(orient="list"),
        "mappings": _visual_mapping_to_dict(spec.mappings),
        "settings": spec.settings,
        "context": spec.context,
        "template_name": spec.template_name,
        "iterator_key": list(spec.iterator_key),
        "layers": [_layer_to_dict(l) for l in spec.layers],
        "coord": _coord_to_dict(spec.coord),
        "facet": _facet_to_dict(spec.facet),
        "children": [_spec_to_dict(c) for c in spec.children],
        "transform": _link_transform_to_dict(spec.transform),
        "frame_config": spec.frame_config,
    }

def _spec_from_dict(data: dict) -> FigureSpec:
    return FigureSpec(
        data=pd.DataFrame(data["data"]),
        mappings=_visual_mapping_from_dict(data["mappings"]),
        settings=data["settings"],
        context=data["context"],
        template_name=data["template_name"],
        iterator_key=tuple(data.get("iterator_key", [])),
        layers=[_layer_from_dict(l) for l in data.get("layers", [])],
        coord=_coord_from_dict(data.get("coord", {})),
        facet=_facet_from_dict(data.get("facet", {})),
        children=tuple(_spec_from_dict(c) for c in data.get("children", [])),
        transform=_link_transform_from_dict(data.get("transform", {})),
        frame_config=data.get("frame_config"),
    )
```

Update `_layer_to_dict` / `_layer_from_dict`:
- Remove `subplot` field
- Remove `coord` field

Update top-level `spec_to_dict` / `spec_from_dict` to use recursive `_spec_to_dict` / `_spec_from_dict`.

## Acceptance criteria

- [ ] `_spec_to_dict` serializes `children`, `transform`, `frame_config`
- [ ] `_spec_from_dict` deserializes them back
- [ ] `_layer_to_dict` no longer serializes `subplot` or `coord`
- [ ] Recursive round-trip: `spec_from_dict(spec_to_dict(spec)) == spec`
- [ ] `link_to_dict` / `link_from_dict` are deleted
- [ ] Full test suite passes

## Files

- `src/geofig_engine/serialize/converters.py`
