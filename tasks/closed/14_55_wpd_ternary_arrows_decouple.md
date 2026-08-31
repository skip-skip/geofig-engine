# WP-D: Decouple ternary ion labels from arrows; add setting-driven ternary arrows

**Status**: complete
**Phase**: 14.55
**Dependencies**: `14_55_wpb_axis_arrow_helper.md`

## Description

Overhaul `_draw_ternary_frame` (`renderer.py:160`) to stop hardcoding the
fused arrow+ion-label block (`renderer.py:233-261`). Today the ternary arrows
and the ion edge labels (e.g. `Mg`, `Ca`, `Na+K`) are one annotation, with
direction baked in via `rev_bottom`/`rev_left`/`rev_right` derived from
`coord.handedness`.

After this WP:
- **Ion edge labels stay** as standalone edge labels, always drawn (preserving
  current look and semantics) and no longer carrying arrow styles.
- **Arrows become independent**, driven by `axis.show_arrows()` via the WP-B
  helper, drawn on each of the 3 edges parallel to the edge and pointing toward
  increasing values (the sorted-values rule), not by the `reverse` handedness
  flag.

Note: existing ternary tests assert on the presence of grid lines / tick labels
and describe "ion arrows" loosely (e.g. `test_axis_format.py:483`,
`test_linked_render.py:150`); they check counts/general presence, not arrow
direction. Keep ion labels rendered so those still pass, and add explicit arrow
on/off coverage in WP-G.

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py` — `_draw_ternary_frame`

1. **Extract ion edge labels** from the current fused block into standalone
   text placements (the existing `mid_left`/`mid_base`/`mid_right` anchors and
   `label_rotation((1,0), matrix, label_policy)` rotation are reused). Each ion
   label renders as plain text with the white bbox, independent of any arrow.
2. **Remove the ternary-only `_arrow(...)` closure and its `reverse`/arrowstyle
   logic** — replaced by `_draw_axis_arrow`.
3. **Draw ternary arrows when `axis.show_arrows()`**:
   - Bottom edge: from `(0,0)` → `(1,0)` (or sorted per the value increase
     along the edge), offset below the base; local_vec `(1, 0)`.
   - Left edge: from `(0,0)` → apex along the left edge; local_vec
     `(0.5, SQRT3_2)`.
   - Right edge: from `(1,0)` → apex along the right edge; local_vec
     `(-0.5, SQRT3_2)`.
   - Each arrow points toward ascending value along that edge (per the sorted
     rule), parallel via `label_rotation`.
4. Preserve the tick-label inversion logic (`inv = 100 - tick`) and the
   triangle/grid drawing untouched.

### Considerations

- The current ternary behavior makes some edge tick labels show inverted values
  and arrows point per handedness. Under the new rule, the *arrow* direction
  always follows ascending value; tick labels and handedness remain unchanged.
  Eyeball the piper triangles (which set `handedness="right"` on the cation
  triangle) to confirm arrow direction reads sensibly alongside inverted labels
  after enabling arrows (see WP-F).

## Acceptance criteria

- [x] Ion edge labels (Mg/Ca/Na+K etc.) render as standalone labels, always present, no arrow fused in
- [x] Ternary with `axis_arrows: true` draws 3 arrows (one per edge); with it off/absent draws no arrows
- [x] Arrow direction follows ascending values (sorted rule), not `rev_*`/handedness
- [x] The old `_arrow` closure and `reverse` arrowstyle fusion in `_draw_ternary_frame` are removed entirely
- [x] Triangle outline, grid, tick labels, and title rendering are unchanged
- [x] Existing ternary tests still pass (with any light updates noted in WP-G)

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
