# WP3: Renderer refactor — `_render_children` replaces `_render_linked`

**Status**: open
**Phase**: 14.51
**Depends on**: `14_51_wp2_frame_implication`

## Description

Replace the `_render_linked` method with `_render_children`. The new method iterates `spec.children` instead of `spec.links`, applies each child's own coord and transform, and renders each child's layers directly (no string-based routing).

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py`

Rename/refactor `_render_linked` → `_render_children`:

```python
def _render_children(self, spec: FigureSpec):
    fig, ax = plt.subplots(figsize=spec.settings.get("figsize", (10, 6)))
    ax.set_facecolor("none")
    if not spec.children:
        raise ValueError("FigureSpec must define at least one child")

    for child in spec.children:
        # 1. Apply child's coord to its layers' visual mappings
        child = self._apply_child_coord_transforms(child)
        # 2. Draw frame (implied by coord type)
        snapshot = self._snapshot_artists(ax)
        self._draw_implied_frame(ax, child)
        affine = _affine_from_matrix(child.transform.matrix())
        for artist in self._new_artists(ax, snapshot):
            if not isinstance(artist, matplotlib.text.Text):
                artist.set_transform(affine + ax.transData)
        # 3. Render child's layers
        self._render_child_layers(ax, child, affine)

    # 4. Compute world limits from all children
    xlim, ylim = self._children_world_limits(spec.children)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    # 5. Finalize
    title = spec.settings.get("title")
    if title:
        fig.suptitle(title, fontsize=14, y=0.98)
    ax.axis("off")
    plt.close(fig)
    return fig
```

New helper `_apply_child_coord_transforms(child)`:
- Iterates `child.layers`, applies `child.coord.transform_visual_mapping()` to each layer's visual_mapping
- Returns a new FigureSpec with updated layers

New helper `_render_child_layers(ax, child, affine)`:
- Renders each layer in `child.layers` using `_render_layer`
- Stamps each layer's artists with the child's affine

Rename `_linked_world_limits` → `_children_world_limits`:
- Iterates children instead of links
- Each child contributes its `transform.transform_points([(0,0),(1,0),(0,1),(1,1)])` corners
- Each child's layers contribute their x/y data through the child's transform

Remove:
- `_apply_linked_coord_transforms` (replaced by `_apply_child_coord_transforms`)
- The `affine_for` closure (each child has its own affine directly)

Update dispatch in `render()`:
```python
if spec.children:
    return self._render_children(spec)
```

## Acceptance criteria

- [ ] `_render_children(spec)` iterates `spec.children`
- [ ] Each child's coord transforms its own layers' visual mappings
- [ ] Each child's layers are stamped with the child's own affine
- [ ] Frame is drawn for each child via `_draw_implied_frame`
- [ ] World limits computed from all children's transforms + data
- [ ] No string-based routing (no `subplot` lookups)
- [ ] `_render_linked` method is deleted
- [ ] Full test suite passes

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
