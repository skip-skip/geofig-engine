# StatSum: aggregate data by group for pie charts

**Status**: open
**Phase**: 12
**Dependencies**: none

## Description

Implement `StatSum` in `core/stat.py`. Groups a DataFrame by a category column,
sums a numeric column, and produces columns needed for pie chart rendering:

- `x` — cumulative proportion × 2π (angular start position)
- `y` — constant 1.0 (radius)
- `width` — proportion × 2π (angular width)
- `label` — group name

## Files to modify

- `src/geofig_engine/core/stat.py` — add `StatSum` dataclass with `compute()`
- `src/geofig_engine/serialize/converters.py` — add deserialization branch

## Acceptance criteria

- [ ] `StatSum(column="value", group="category").compute(df)` returns DataFrame with `x`, `y`, `width`, `label` columns
- [ ] Proportions sum to 1.0
- [ ] Rows are sorted by group (or by value descending if `sort=True`)
- [ ] Serialization round-trips correctly
