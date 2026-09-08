# Phase 14.59: Frame renderer support for named & absolute ticks

**Status**: complete
**Phase**: 14.59
**Dependencies**: `14_59_wp1_axis_named_ticks` (axis model)

## Description

Consume the new `abs_ticks` / `tick_labels` capabilities in the unified
cartesian frame drawer (`_draw_cartesian_axis`), wire the previously-unused
`xlabel`/`ylabel` fields into the framed path (needed for the "meq/L" caption),
and resolve the top-level double-title behavior so a framed spec's
`settings["title"]` renders as the figure suptitle only.

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- **Named ticks** — in `_draw_cartesian_axis`, when a primary (x or y) axis
  declares `tick_labels`, draw labels from the (position → label) map at those
  exact local positions **including frame edges**, using the same world-side
  text placement / rotation path as numeric ticks. Named entries bypass
  `_tick_label`.
- **Secondary named ticks** — same handling for `secondary_x` / `secondary_y`
  when their declaration carries `tick_labels`.
- **Absolute ticks** — apply `abs_ticks` in the numeric tick path:
  `_tick_label(abs(value), fmt)`; secondary ticks inherit from the declaration.
- **`xlabel` / `ylabel`** — draw them in `_draw_cartesian_axis` (below the
  bottom edge for x, left of the left edge for y), so framed cartesian specs get
  their axis captions. Sized via `resolve_fontsize("xlabel"/"ylabel")`.
- **Top-level title resolution** — a top-level framed spec currently draws the
  frame box-top title (`axis.title`) *and* `fig.suptitle` from the same
  `settings["title"]`. Make the top-level path render the title once (suptitle).
  Nested children keep their edge titles. Verify no existing test relies on a
  top-level box-top title.

### `tests/test_axis_format.py`

- Render-level tests modeled on `_render_single_top` / `_render_child`:
  named ticks present at edge positions, abs-formatted numeric ticks, secondary
  named y ticks on the right edge, xlabel/ylabel text drawn, top-level title
  renders exactly once.

## Acceptance criteria

- [ ] Named primary ticks render at exact positions, including frame edges
- [ ] Named secondary ticks render on the opposing edge (right for y)
- [ ] `abs_ticks` renders `-v` as `v` for numeric ticks on x, y, and secondary
- [ ] `xlabel`/`ylabel` render on framed cartesian specs (meq/L caption case)
- [ ] Top-level framed spec with `title` renders a single title (suptitle)
- [ ] Full suite passes; default framed output unchanged

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `tests/test_axis_format.py`
- `tests/test_linked_render.py` (if secondary named ticks touch the child path)