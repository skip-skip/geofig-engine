# StatPieLabels: compute label positions and text for pie wedges

**Status**: open
**Phase**: 12
**Dependencies**: none

## Description

Implement `StatPieLabels` in `core/stat.py`. Aggregates data the same way as
`StatSum` (groups by category, sums values), then computes display text and
screen positions for auto-placed pie wedge labels.

- `label_x` — angle centre of each wedge (midpoint of angular extent)
- `label_y` — radial distance from centre (e.g. 1.3)
- `label_text` — formatted string, e.g. `"30%"` or `"50 (25.0%)"`

Supports `show_percent=True` and `show_count=False` flags.

## Files to modify

- `src/geofig_engine/core/stat.py` — add `StatPieLabels` dataclass with `compute()`
- `src/geofig_engine/serialize/converters.py` — add deserialization branch

## Acceptance criteria

- [ ] `StatPieLabels(column="value", group="category", show_percent=True).compute(df)` produces labels like `"30.0%"`
- [ ] `StatPieLabels(..., show_count=True, show_percent=True)` produces labels like `"50 (25.0%)"`
- [ ] `label_x` is the angular midpoint of each wedge
- [ ] `label_y` equals the configured `label_distance`
- [ ] Serialization round-trips correctly
