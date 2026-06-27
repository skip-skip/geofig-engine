# render_text: polar-aware label alignment

**Status**: open
**Phase**: 12
**Dependencies**: none

## Description

Enhance `render_text` to automatically set horizontal alignment based on
angular position when the axes uses a polar projection. This enables clean
auto-placed labels for pie chart wedges.

Logic:
- If `ax.name == "polar"`, compute the angle from the x value (in radians)
- Right half (`-π/2 ≤ angle ≤ π/2`): `ha="left"`
- Left half: `ha="right"`
- Always: `va="center"`

## Files to modify

- `src/geofig_engine/renderers/matplotlib/handlers.py` — modify `render_text`

## Acceptance criteria

- [ ] Text in a polar axes on the right half has `ha="left"`
- [ ] Text in a polar axes on the left half has `ha="right"`
- [ ] Cartesian axes behaviour is unchanged
