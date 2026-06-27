# StatRadar: normalise and close polygon for spider/radar charts

**Status**: open
**Phase**: 12
**Dependencies**: none

## Description

Implement `StatRadar` in `core/stat.py`. Prepares data for spider/radar charts:

1. Sorts data by x (category) to determine even angular spacing
2. Normalises y values to [0, 1]
3. Closes the polygon by appending the first point at the end

Normalisation behaviour (controlled by `shared_axes`):
- `shared_axes=True` — global min/max across all colour groups (common scale)
- `shared_axes=False` — per-group min/max (each series fills independently)

Produces columns `x` (evenly-spaced angles in radians, closed) and `y` (normalised values, closed).

## Files to modify

- `src/geofig_engine/core/stat.py` — add `StatRadar` dataclass with `compute()`
- `src/geofig_engine/serialize/converters.py` — add deserialization branch

## Acceptance criteria

- [ ] Output `x` values are evenly spaced angles from 0 to 2π
- [ ] First point is appended at the end (polygon closure)
- [ ] `shared_axes=True` uses the same min/max across all groups
- [ ] `shared_axes=False` normalises each colour group independently
- [ ] Serialization round-trips correctly
