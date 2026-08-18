# Stiff diagram — single-sample polygon

**Status**: open
**Phase**: 14
**Dependencies**: none

## Description

Implement a Stiff diagram function — a per-sample 6-axis polygon showing relative ion concentrations. Unlike standard GoG components, Stiff diagrams plot a **single sample at a time** using a custom matplotlib axis.

### Architecture

**`plot_stiff(ca, mg, na_k, cl, hco3, so4, title="", figsize=(6, 6)) -> FigureSpec`**
Standalone function that accepts scalar ion concentrations (in meq/L or mg/L) for a single sample. Returns a `FigureSpec` suitable for rendering.

Implementation creates a matplotlib figure directly with:
- Horizontal axis split into positive (right) and negative (left) halves
- 3 vertical axes for cation pairs (Na+K / Cl, Mg / HCO3, Ca / SO4)
- Polygon connecting the ion values at each axis
- Axis scaled symmetrically (uses the max value across all 6 ions)

### Rendering
`plot_stiff` builds a FigureSpec with a special setting `"stiff_layout": True` that the renderer detects. A new `_render_stiff()` method in the renderer handles the custom matplotlib layout.

Alternatively, `plot_stiff` can create the matplotlib figure directly and return a lightweight wrapper. Prefer the GoG path: produce a FigureSpec, let the renderer handle it.

### Serialization
The FigureSpec produced by `plot_stiff` should be serializable (stores the 6 ion values as settings/metadata).

## Files to create / modify

- `src/geofig_engine/templates/stiff.py` — `plot_stiff()` function
- `src/geofig_engine/templates/__init__.py` — export `plot_stiff`
- `src/geofig_engine/renderers/matplotlib/renderer.py` — add `_render_stiff()` dispatch path (optional: handle via pipeline or direct figure)

## Acceptance criteria

- [ ] `plot_stiff(ca, mg, na_k, cl, hco3, so4)` returns a FigureSpec
- [ ] Rendered figure shows a 6-axis polygon with correct ion labels
- [ ] Axis scaling is symmetric (automatically sized to max ion value)
- [ ] Left side (negative): Cl, HCO3, SO4
- [ ] Right side (positive): Na+K, Mg, Ca
- [ ] Grid lines at regular intervals for readability
- [ ] Title is settable
- [ ] FigureSpec is serializable
