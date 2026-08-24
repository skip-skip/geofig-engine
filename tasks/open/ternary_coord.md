# TernaryCoord projection

**Status**: open
**Phase**: 14.5
**Dependencies**: (none)

## Description

New ternary projection for linked axes (ROADMAP Phase 14.5), reusable for Piper, Durov, and standalone ternary plots. Maps three fractions summing to 1 into a right-triangle local space (`[0,1]²`, height `√3/2`) with configurable vertex assignment and handedness (left/right facing).

Follows the `CoordPolar` pattern: the coord rewrites projection-specific channels into `x`/`y` via `transform_visual_mapping()`, so geoms and handlers stay projection-agnostic.

## Files to modify

- `src/geofig_engine/core/coord.py` — add `TernaryCoord` dataclass with params (vertex order `a/b/c`, handedness) and `transform_visual_mapping(visual_mapping, geom)` consuming fraction channels → local triangle coords
- `src/geofig_engine/serialize/converters.py` — TernaryCoord serialization in `coord_to_dict`/`coord_from_dict`
- `tests/test_ternary_coord.py` (new)

## Acceptance criteria

- [ ] Pure-fraction inputs land on correct triangle corners for both handedness values
- [ ] Fraction channels (`a/b/c` keys by default, configurable) are rewritten to local `x/y`; original channel keys removed from mapping
- [ ] Non-fraction channels (color, style, …) pass through untouched
- [ ] Behavior documented/pinned for rows where fractions do not sum to 1 (normalize or raise — pick one, test it)
- [ ] Geoms require no knowledge of ternary math
- [ ] Serialization round-trips TernaryCoord losslessly
