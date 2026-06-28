# GeomText improvements — rotation, bounding boxes, pixel placement

**Status**: open
**Phase**: 13
**Dependencies**: none

## Description

Enhance the existing `GeomText` and its `render_text` handler with:
1. **Rotation** — add `angle` channel to `GeomText.optional_channels`
2. **Bounding box backgrounds** — add `bbox` channel (dict with facecolor, edgecolor, alpha, etc.)
3. **Auto pixel-based placement** — `_measure_text_px()` helper that computes text pixel extent before rendering, enabling precise placement relative to features

### Changes

**GeomText** — add `angle` and `bbox` to optional_channels:
```python
class GeomText(Geom):
    def __init__(self) -> None:
        super().__init__(
            name="text",
            required_channels=("x", "y", "label"),
            optional_channels=("color", "size", "alpha", "angle", "bbox"),
        )
```

**render_text handler** — enhancements:
- `"angle"` channel → `kw["rotation"]` (float, degrees)
- `"bbox"` channel → `kw["bbox"]` (dict with facecolor, edgecolor, alpha, pad, etc.)
- `_measure_text_px(text, fontsize, rotation)` → `(width_px, height_px)` using matplotlib's text rendering for pre-computation
- Use `_measure_text_px()` to enable alignment options: `auto_halign`, `auto_valign` that adjust `ha`/`va` to keep text within axes bounds

### Serialization
- Update `geom_to_dict`/`geom_from_dict` for `GeomText` if needed (currently no params, no change needed)

## Files to modify

- `src/geofig_engine/core/geom.py` — add `"angle"`, `"bbox"` to `GeomText.optional_channels`
- `src/geofig_engine/renderers/matplotlib/handlers.py` — update `render_text`; add `_measure_text_px()` helper

## Acceptance criteria

- [ ] `GeomText` accepts `angle` channel — labels render with `rotation`
- [ ] `GeomText` accepts `bbox` channel — labels render with bounding box
- [ ] `_measure_text_px()` returns expected pixel dimensions for a given text/fontsize/rotation
- [ ] Auto-alignment prevents text from being clipped by axis boundaries
- [ ] Backward compatible — existing text usage without angle/bbox still works
- [ ] Existing serialization tests pass (no new serialization branches needed)
