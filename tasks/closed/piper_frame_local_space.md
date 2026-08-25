# Frame providers: draw in local space, stamp like data

**Status**: closed
**Phase**: 14.5
**Depends on**: `piper_world_limits_fix`

## Description

Frame providers (`_piper_ternary_frame`, `_piper_diamond_frame`) currently pre-map geometry through `_apply_matrix_pts(link_matrix, ...)`. This breaks the "one transform chain" principle — frame geometry lives in a different pipeline than data.

The goal: frame providers draw in local coordinate space (`[0,1]²` for ternary, `[0,100]²` for diamond). The renderer stamps frame line artists with the link affine, same as data. Labels stay world-side (placed at `transform_point()` anchors, not stamped).

## Renderer changes (`renderer.py:_render_linked`)

Add frame-stamping loop before the existing frame provider call:

```python
for link in spec.links:
    frame = link.frame or {}
    provider = _FRAME_PROVIDERS.get(frame.get("provider"))
    if provider is not None:
        snapshot = self._snapshot_artists(ax)
        provider(ax, link.transform.matrix(), label_policy)
        affine = _affine_from_matrix(link.transform.matrix())
        for artist in self._new_artists(ax, snapshot):
            if not isinstance(artist, matplotlib.text.Text):
                artist.set_transform(affine + ax.transData)
```

Set `ax.set_facecolor("none")` for transparent background.

## Frame provider changes

**`_piper_ternary_frame`**: Remove all `_apply_matrix_pts` calls for line geometry. Draw triangle at local `[(0,0), (1,0), (0.5, sqrt3/2)]`. Grid at local 20/40/60/80%. Labels placed at world coords via `_apply_matrix_pts` (not stamped).

**`_piper_diamond_frame`**: Remove all `_apply_matrix_pts` calls for line geometry. Draw square at local `[(0,0), (100,0), (100,100), (0,100)]`. Grid at local 20/40/60/80%. Labels placed at world coords.

## Acceptance criteria

- [ ] Frame line artists are drawn in local space
- [ ] Frame line artists receive link affine transform via stamping
- [ ] Frame text labels remain upright (placed world-side)
- [ ] `ax.set_facecolor("none")` set in `_render_linked`
- [ ] Visual output matches current output (for existing identity/ternary transforms)
- [ ] Full test suite passes

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py` — `_render_linked()`, `_piper_ternary_frame()`, `_piper_diamond_frame()`
