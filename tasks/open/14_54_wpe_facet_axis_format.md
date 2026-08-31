# WP-E: Facet path consumes AxisFormat per panel

**Status**: open
**Phase**: 14.54
**Depends on**: 14_54_wpa_axis_format_model.md

## Description

The faceted render path (`_render_faceted`) currently calls `_apply_settings`
per panel on a shared subplot grid (native matplotlib panels). Align it with the
unified model so each panel is formatted from the **same** `AxisFormat` spec as
single/child frames, giving a single source of truth for axis formatting across
all rendering paths.

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- In `_render_faceted`, replace the per-panel `_apply_settings(ax, fig, spec)`
  with a call through the unified formatting entry that parses `AxisFormat`
  from `spec.settings` and applies title/labels/limits/scales/grid/time_format
  per panel.
- Because faceted panels are native (non-stamped) subplot axes, apply the
  `AxisFormat` through a thin native adapter (reads the same fields, emits
  matplotlib mutators) rather than the custom stamped frame drawer — panels are
  not affine-stamped.
- Preserve the existing facet grid layout, axis-sharing (`sharex`/`sharey`),
  `_compute_facet_limits`, and `_apply_facet_panel` behavior exactly.
- Where a facet's coord is ternary/polar, route panel formatting through
  `_draw_frame` (WP-B/WP-C) as appropriate for those coords.

## Acceptance criteria

- [ ] Faceted panels render identical to before (limits, sharing, titles, grid)
- [ ] Panel formatting is driven by `AxisFormat`, not ad-hoc settings reads
- [ ] Facet layout / limits / sharing logic is unchanged
- [ ] Existing facet tests pass (light updates only if assertions on settings shape change)

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `tests/test_axis_format.py` (panel formatting parity)
- Affected facet tests (light updates)
