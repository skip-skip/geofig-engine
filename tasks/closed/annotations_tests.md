# Phase 13 test suite — annotations

**Status**: open
**Phase**: 13
**Dependencies**: `annotations_geom_shapes`, `annotations_geom_abline`, `annotations_geom_text`, `annotations_zorder`

## Description

Write pytest tests covering all Phase 13 additions. Tests use `render_template()` to produce `FigureSpec` objects, validate the spec structure, and optionally render to verify visual output via returned `Figure` objects.

### Test areas

**GeomHSpan / GeomVSpan / GeomRect** (new file or section)
- Geom construction validates correctly
- Visual_mapping resolves scalar constants for xmin/xmax/ymin/ymax
- Handler produces correct matplotlib calls (ax.axhspan, ax.axvspan, ax.Rectangle)
- Color and alpha channels are respected
- Works with data-driven channels (Series input)

**GeomAbline**
- Slope-intercept construction
- Two-point construction
- Validation rejects mixed params
- Line extends across full axis
- Color, style, width, alpha respected

**GeomText improvements**
- angle channel applies rotation
- bbox channel adds bounding box
- _measure_text_px() returns pixel dimensions
- Backward compatibility with existing text usage

**Zorder**
- Layer with explicit zorder produces LayerSpec with matching zorder
- Rendering uses explicit zorder when set
- Auto-increment still works when zorder is None
- Serialization round-trip preserves zorder
- Coord transform preserves zorder

**Integration**
- Annotations + data layers in a single figure render in correct z-order
- Full spec round-trip through serialization

### Regression
- All 486 existing tests still pass

## Files to create / modify

- `tests/test_annotations.py` — all Phase 13 tests

## Acceptance criteria

- [ ] At least 20 test cases covering all acceptance criteria above
- [ ] All tests pass with `conda run -n figengine pytest -x --tb=short`
- [ ] Existing tests have zero regressions
