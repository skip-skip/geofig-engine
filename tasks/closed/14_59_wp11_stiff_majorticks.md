# Phase 14.59: Stiff template majortick opts-in

**Status**: complete
**Phase**: 14.59
**Dependencies**: `14_59_wp8_majortick_axis_model`, `14_59_wp10_majortick_renderer`

## Description

Opt the Stiff template into the new majortick feature with the same outside
production nub the renderer previously hard-coded (0.4 * label_offset =
0.06). Settings apply uniformly, so this ticks the bottom x ruler, the left
cation edge, and the right anion edge (no secondary_x on stiff, so no top
ticks). `majortick_offset: 0` keeps the ticks entirely outside the frame,
clear of the label strips.

## Files to modify

- `src/geofig_engine/templates/stiff.py` — add
  `"majortick_length": 0.06, "majortick_offset": 0` to the settings dict.

## Acceptance criteria

- [ ] Stiff settings contain `majortick_length: 0.06` and `majortick_offset: 0`
- [ ] Bottom x ruler ticks span `[ylo - 0.06, ylo]`
- [ ] Left/right named-label rows get ticks at y = 0, 1, 2
- [ ] No top-edge ticks (no secondary_x)
- [ ] Serialization round-trip preserves the new settings keys