# Phase 14.59: Rewrite the Stiff template as a cartesian FigureSpec

**Status**: open
**Phase**: 14.59
**Dependencies**: `14_59_wp1_axis_named_ticks`, `14_59_wp2_frame_named_ticks_render`, `14_59_wp3_geom_polygon`

## Description

Re-express the Stiff diagram (`plot_stiff`) as an ordinary `CoordCartesian`
figure so the diagram is produced entirely by the declarative frame + layer
machinery. The public API is unchanged:

```python
plot_stiff(ca, mg, na_k, cl, hco3, so4, title="", figsize=(6, 6)) -> FigureSpec
```

Design (cartesian-native look — standard framed box + grid + named ticks):

- **Data**: the 7-vertex polygon in **raw signed meq/L** coordinates (no
  normalization): cations on the left are negative (`-na_k, -ca, -mg` at
  y = 2, 1, 0), anions on the right positive (`+cl, +hco3, +so4` at
  y = 0, 1, 2), closing back to the first vertex.
- **X axis**: symmetric `xlim = ±(1.5 * tick_max)` so `x=0` sits exactly in the
  center and the extreme ticks stay interior; `tick_step = tick_max / 2`;
  `abs_ticks: True` shows the meq/L ruler as `20 10 0 10 20`;
  `xlabel: "meq/L"` via the WP2 framed `xlabel` wiring.
- **Y axis** (dual y axes): primary `tick_labels = {0: "Mg²⁺", 1: "Ca²⁺", 2: "Na⁺+K⁺"}`
  on the left edge; `secondary_y = {"range": [0, 2], "tick_labels": {0: "SO₄²⁻", 1: "HCO₃⁻", 2: "Cl⁻"}}`
  on the right edge; `ylim = (-0.55, 2.5)`; `grid_step: 1` for the ion-row grid.
- **Layers**: one `GeomPolygon(color=..., edgecolor="black", edgewidth=1.5)` for
  the filled polygon (WP3). Decorative elements as declarative layers: dashed
  center line at `x=0` (`GeomAbline`, two-point) and the mid horizontal line at
  `y=1` (`GeomLine` two-point segment). Ion axis runway lines (vertex → frame
  edge at each row) are optional `GeomLine` segments if desired for readability.
- **Title**: `settings["title"]` → figure suptitle (computed by `_nice_tick_max`
  for `tick_max`; `max_val` moves out of `StiffCoord` into the template).
- Renders through `_render_single_framed` (aspect equal, axis off) — no coord
  dispatch, no `StiffCoord`.

## Changes

### `src/geofig_engine/templates/stiff.py`

- Rewrite `plot_stiff` to build the cartesian spec described above via
  `build_spec`; identical signature and return type. Keep `figsize` default
  `(6, 6)`. `title` maps to `settings["title"]`.

## Acceptance criteria

- [ ] `plot_stiff(...)` returns a `FigureSpec` with `coord.name == "cartesian"`
- [ ] Polygon data uses raw signed meq/L values (7 vertices)
- [ ] `xlim` symmetric about 0; x tick labels are absolute values
- [ ] Cation labels on the left y edge; anion labels on the right (secondary y)
- [ ] "meq/L" caption renders below the x axis
- [ ] Filled polygon + center/mid decorative lines render
- [ ] Title renders as suptitle; `hydro_demo.py` stiff figures still produce output

## Files

- `src/geofig_engine/templates/stiff.py`
- `tests/test_stiff.py` (rewrite — see WP6)