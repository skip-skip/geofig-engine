# GeomBar: add `position` field and stacking logic

**Status**: open
**Phase**: 11/12
**Dependencies**: none

## Description

Add a `position` field to `GeomBar` (values: `"identity"`, `"stack"`, `"fill"`)
and implement the corresponding stacking logic in `render_bar`. This unblocks
both the Phase 11 stacked-bar item and the Phase 12 pie chart.

- `"identity"` — current behavior (bars drawn as-is)
- `"stack"` — bars at the same x are stacked via cumulative `bottom` in `ax.bar()`
- `"fill"` — normalized to [0,1] per x group, then stacked

## Files to modify

- `src/geofig_engine/core/geom.py` — add `position: str = "identity"` field to `GeomBar`
- `src/geofig_engine/renderers/matplotlib/handlers.py` — implement stacking in `render_bar`
- `src/geofig_engine/serialize/converters.py` — serialize `GeomBar.position`

## Acceptance criteria

- [ ] `GeomBar(position="stack")` stacks bars at the same x value
- [ ] `GeomBar(position="fill")` normalises to [0,1] then stacks
- [ ] `GeomBar(position="identity")` behaves as before (no change)
- [ ] `ax.bar()` is called with the correct `bottom` parameter for stacked bars
- [ ] Serialization round-trips the `position` field
