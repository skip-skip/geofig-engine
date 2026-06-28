# GeomAbline — reference line annotations

**Status**: open
**Phase**: 13
**Dependencies**: `annotations_geom_shapes` (if adding xmin/xmax channels, otherwise independent)

## Description

Add `GeomAbline` for reference lines (diagonal, horizontal, or vertical) used in geochem classification plots. Supports two definition modes:

1. **Slope-intercept**: `slope` + `intercept` fields (e.g., `y = 2x + 1`)
2. **Two-point**: `x1`, `y1`, `x2`, `y2` fields (line through two data-coordinate points)

The handler draws the line across the full axis extent (or clipped to data limits) using `ax.axline()` (mpl 3.3+) or by computing endpoints from current axis limits.

No new channels needed — all parameters are Geom fields (not visual_mapping channels), following the `GeomFunctionLine` pattern.

```python
@dataclass(frozen=True)
class GeomAbline(Geom):
    slope: float | None = None
    intercept: float = 0.0
    x1: float | None = None
    y1: float | None = None
    x2: float | None = None
    y2: float | None = None
```

- `required_channels=()` — no data channels needed
- `optional_channels=("color", "style", "width", "alpha")` — visual styling

Validation: exactly one of `(slope, intercept)` or `(x1, y1, x2, y2)` must be provided (all or none per group).

Handler `render_abline`:
- Resolves slope/intercept or x1/y1/x2/y2 from the geom fields
- Uses `ax.axline()` if available (matplotlib >= 3.3), else computes endpoints from axis limits
- Applies color, linestyle, linewidth, alpha from visual_mapping

## Files to modify

- `src/geofig_engine/core/geom.py` — add `GeomAbline` dataclass with validation
- `src/geofig_engine/renderers/matplotlib/handlers.py` — add `render_abline` function
- `src/geofig_engine/renderers/matplotlib/renderer.py` — register in `_GEOM_HANDLERS`
- `src/geofig_engine/serialize/converters.py` — add `"abline"` branches in `geom_to_dict`/`geom_from_dict`

## Acceptance criteria

- [ ] Slope-intercept mode draws correct line across full axis
- [ ] Two-point mode draws correct line through specified points
- [ ] Validation rejects mixed/insufficient parameters at construction
- [ ] Supports `color`, `style`, `width`, `alpha` channels
- [ ] Handles axis limits correctly (line extends to edges)
- [ ] Serialization round-trips correctly (stores slope/intercept or x1/y1/x2/y2)
- [ ] Registered in `_GEOM_HANDLERS`
- [ ] `ax.axline()` fallback for older matplotlib
