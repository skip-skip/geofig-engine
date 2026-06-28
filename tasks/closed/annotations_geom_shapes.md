# GeomRect, GeomHSpan, GeomVSpan — shaded region annotations

**Status**: open
**Phase**: 13
**Dependencies**: none

## Description

Add three new Geom types for shaded rectangular regions used in geochem classification plots (NPR/NNP, ANP/AGP, NAGpH quadrants and threshold bands).

### Channel additions to `Channel` enum
- `XMIN = "xmin"`
- `XMAX = "xmax"`

### New Geoms

**GeomHSpan** — horizontal band spanning the full x-axis at a y-range.
- `required_channels=("ymin", "ymax")` — data-coordinate bounds
- `optional_channels=("color", "alpha")`
- handler uses `ax.axhspan(ymin, ymax, color=..., alpha=...)`

**GeomVSpan** — vertical band spanning the full y-axis at an x-range.
- `required_channels=("xmin", "xmax")` — data-coordinate bounds
- `optional_channels=("color", "alpha")`
- handler uses `ax.axvspan(xmin, xmax, color=..., alpha=...)`

**GeomRect** — arbitrary rectangle in data coordinates.
- `required_channels=("xmin", "xmax", "ymin", "ymax")`
- `optional_channels=("color", "alpha")`
- handler uses `matplotlib.patches.Rectangle` via `ax.add_patch()`

### Handler pattern

Each handler receives scalar xmin/xmax/ymin/ymax resolved from the visual_mapping (data-driven or constants). They draw the shape and return immediately — no grouping, no dodge.

### Serialization
- Add `"hspan"`, `"vspan"`, `"rect"` branches to `geom_to_dict`/`geom_from_dict` in `converters.py`
- Export new Geom types from `serialize/__init__.py`

### Registration
- Add all three to `_GEOM_HANDLERS` in `renderer.py`

## Files to modify

- `src/geofig_engine/core/geom.py` — add `Channel.XMIN`, `Channel.XMAX`; add `GeomHSpan`, `GeomVSpan`, `GeomRect` dataclasses
- `src/geofig_engine/renderers/matplotlib/handlers.py` — add `render_hspan`, `render_vspan`, `render_rect` functions
- `src/geofig_engine/renderers/matplotlib/renderer.py` — register handlers in `_GEOM_HANDLERS`
- `src/geofig_engine/serialize/converters.py` — add branches in `geom_to_dict`/`geom_from_dict`
- `src/geofig_engine/serialize/__init__.py` — export new Geom types

## Acceptance criteria

- [ ] `GeomHSpan` draws a horizontal band from ymin to ymax across the full axis
- [ ] `GeomVSpan` draws a vertical band from xmin to xmax across the full axis
- [ ] `GeomRect` draws a rectangle at the specified data-coordinate bounds
- [ ] All three support `color` and `alpha` channels
- [ ] Handlers resolve constants from Series via `_resolve_constant()` (allow scalar or single-row DataFrames)
- [ ] Serialization round-trips correctly for all three new types
- [ ] All three are registered in `_GEOM_HANDLERS`
