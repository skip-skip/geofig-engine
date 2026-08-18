# Piper diagram template factory

**Status**: open
**Phase**: 14
**Dependencies**: `piper_utils`

## Description

Build the Piper diagram system — a 3-panel figure (ternary cation triangle, ternary anion triangle, diamond projection) for hydrogeochemistry facies analysis.

Piper diagrams do not fit the single-Coord + Facet pattern because each panel has a different coordinate system (ternary, ternary, rotated diamond). The implementation builds a **custom multi-axes FigureSpec** using `pyplot.subplot2grid()` or `GridSpec`.

### Architecture

**`PiperCoord`** — a `Coord` subclass that stores configuration only (no transform):
```python
class PiperCoord(Coord):
    cation_cols: tuple[str, str, str] = ("Ca", "Mg", "Na+K")   # meq/L columns
    anion_cols: tuple[str, str, str] = ("HCO3", "SO4", "Cl")   # meq/L columns
    category_col: str | None = None                             # optional color grouping
```

**`build_piper_specs()`** — factory that returns a complete `FigureSpec` with:
- Spec.settings contains a `"piper_layout"` key that signals the renderer to use a custom 3-panel layout
- The FigureSpec has no standard layers (rendering is handled by the Piper render path)

**Renderer changes** (`renderer.py`):
- In `render()`, detect `isinstance(spec.coord, PiperCoord)` and dispatch to `_render_piper(spec)` 
- `_render_piper()` creates a 3-panel figure using GridSpec:
  - Cation triangle (lower-left)
  - Anion triangle (lower-right)
  - Diamond (upper-center)
- Each panel uses matplotlib's ternary transform or `ax.plot()` with manual axis projection
- Plots points from `spec.data` using the cation/anion column sets

**`piper_overlay_diamond(spec: FigureSpec, data: pd.DataFrame, label_col: str | None = None) -> FigureSpec`**
— returns a new FigureSpec with additional diamond markers overlaid.

### Ternary axis math
For a ternary point (a, b, c) where a+b+c = 1:
- x = b + 0.5 * a
- y = (sqrt(3) / 2) * a

For the diamond projection:
- X = anion_SO4_frac - anion_HCO3_frac
- Y = cation_NaK_frac - cation_Ca_frac

## Files to create / modify

- `src/geofig_engine/core/coord.py` — add `PiperCoord` dataclass
- `src/geofig_engine/renderers/matplotlib/renderer.py` — add `_render_piper()` dispatch path
- `src/geofig_engine/templates/piper.py` — `build_piper_specs()`, `piper_overlay_diamond()`
- `src/geofig_engine/templates/__init__.py` — export piper functions
- `src/geofig_engine/serialize/converters.py` — add PiperCoord serialization

## Acceptance criteria

- [ ] `PiperCoord` stores cation/anion column config and optional category column
- [ ] `build_piper_specs()` returns a FigureSpec with `piper_layout` setting
- [ ] Renderer detects `PiperCoord` and creates 3-panel GridSpec figure
- [ ] Cation triangle plots correct ternary projections
- [ ] Anion triangle plots correct ternary projections
- [ ] Diamond plots correct cation-anion cross-plot
- [ ] Points are colored by `category_col` when provided
- [ ] Axis labels, grid lines, and tick labels follow Piper diagram conventions
- [ ] `piper_overlay_diamond()` adds markers to an existing Piper spec
- [ ] Serialization round-trips PiperCoord
