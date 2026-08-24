# Generic linked-axes render path (matplotlib)

**Status**: open
**Phase**: 14.5
**Dependencies**: `link_model`, `ternary_coord`

## Description

Renderer engine for linked axes (ROADMAP Phase 14.5). Replaces per-diagram special cases with one generic path: a **single matplotlib Axes spans the whole figure**, where world space is the main axis's post-transform data space.

- Main axis artists draw through `M_main + ax.transData`
- Each link's artists draw through `Affine2D.from_values(M_link) + ax.transData` — flat stacks, no nesting
- Layer routing by existing `LayerSpec.subplot` through the owning link's transform + coord

Text never inherits transforms: tick numerals, vertex names, and edge labels are drawn world-side at `transform_point()` anchors. Label policies: `upright` (default, rotation=0) and `parallel` (rotation from transformed edge tangent, squash-aware).

## Files to modify

- `src/geofig_engine/renderers/matplotlib/renderer.py` — add `_render_linked(spec)` dispatch in `render()` when `spec.links` non-empty; `_render_axes` learns subplot→link routing; frame-provider protocol `(link_matrix, parent_axes, label_policy)` generalizing today's `_draw_ternary_frame`/`_draw_diamond_frame`
- `src/geofig_engine/core/link.py` — frame-provider protocol / LabelPolicy definitions if core-resident
- `tests/test_linked_render.py` (new)

## Acceptance criteria

- [ ] Synthetic two-link spec renders on one Axes; each link's geometry lands at affine-predicted positions
- [ ] Main-axis root transform (`M_main`) applies only to main-axis artists; links stay world-anchored
- [ ] Frames/grids/tick marks deform with their link; text labels remain upright by default
- [ ] `parallel` policy rotation computed from transformed edge tangent (correct under non-uniform scale)
- [ ] Layers route to the correct link via `subplot`; unrouted layers draw in main space
- [ ] zorder semantics preserved across links (data ≥ 10, function lines below)
- [ ] Legends/facets operate unchanged on the single shared axes
