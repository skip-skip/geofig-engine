# Roadmap

Completed phases are marked with ✅. Remaining work is organized by theme.

---

## ✅ Phase 1–9 — Core GoG foundation
All 9 phases from the original refactor: Geom, Stat, Scale, Coord, Facet, LayerSpec, FigureSpec, Resolver pipeline, MatplotlibRenderer + 8 geom handlers, facet rendering, legend system, serialization, simplified `render_template` entry.

---

## 🔜 Phase 10 — Remaining simple Geom types
Implement as new Geom subclasses + matplotlib handlers.

- `GeomBox` — boxplot with configurable show_points (jitter), show_n, min_box_n, showfliers, showmeans, horizontal orientation
- `GeomViolin` — violin plot with show_medians, log_scale
- `GeomStepLine` — line plot with step drawstyle (where="pre"|"mid"|"post")
- `GeomHistogram` — histogram with bins config, density, cumulative

---

## 📋 Phase 11 — Enhanced bar / area features
Extend existing `GeomBar` and `GeomArea` handlers and the visual-mapping / stat pipeline.

- **Bar stacking** — new `StatStack` or `stack_col` in bar mapping that stacks series
- **Bar / boxplot sorting** — multi-mode sort: `none`, `forward`, `reverse`, `value_forward`, `value_reverse`
- **Bar / boxplot smush** — remove gaps when a series is absent within a group
- **Continuous color ramp** — `GeomPoint` / `GeomLine` support for mapping a numeric column to a continuous color scale (e.g., viridis), not just categorical

---

## 📋 Phase 12 — Circular / pie / spider geoms

- `GeomPie` — aggregated pie chart. Supports subseries color families (HSL lightness ramps). Smart label alignment for 360°.
- `GeomSpider` — radar / spider chart. Per-axis normalization and max_value. Smart label alignment. Aggregation via stat.

---

## 📋 Phase 13 — Annotation / reference layer system
Needed for geochem classification plots (NPR/NNP, ANP/AGP, NAGpH).

- `GeomRect` / `GeomHSpan` / `GeomVSpan` — shaded rectangular regions (axvspan/axhspan)
- `GeomAbline` — reference line defined by slope + intercept (or two-point), with optional dashed style
- `GeomText` improvements — auto pixel-based placement (`_measure_text_px`), bounding-box backgrounds, angle rotation
- Layer `zorder` control via spec settings (already have basic zorder, make it user-configurable per layer)

---

## 📋 Phase 14 — Specialized coord systems
Complex multi-element diagrams that don't fit a single Coord + Geom.

- **PiperCoord** — ternary cation/anion triangles + diamond projection. Front-end handles mg/L→meq/L conversion, temperature-dependent pKa for alkalinity speciation, combined Na+K / HCO3+CO3.
  - `build_piper_specs()` → factory function creating a FigureTemplate with one Geom layer per subplot region
  - Optional overlay API via `piper_overlay_diamond()`
- **StiffCoord** — 6-axis polygon per sample. Single-sample function, not a general-purpose geom.
  - Standalone function `plot_stiff(ca, mg, na, k, hco3, so4, cl, ...)` returning a FigureSpec
- **Classification plot templates** (composition over inheritance — reuse GeomPoint + annotation layers):
  - `npr_nnp(mapping={"x": npr_col, "y": nnp_col})` template adding shaded bands + quadrant labels
  - `anp_agp(mapping={"x": agp_col, "y": anp_col})` template adding reference slope lines + region labels
  - `nagph_nag(mapping={"x": nagph_col, "y": nag_col})` template adding threshold lines + auto-placed labels

---

## 📋 Phase 15 — Enhanced legend features

- **Multi-level grouped legends** — `subseries_col` pattern with section headers and aligned columns (from geochemplot's grouped-legend pattern)
- **Dimension legend builder** — `build_dimension_legend()` standalone function from color_col + shape_col + linetype_col
- **Marker/color combinatorial generator** — `gen_markers()`, `gen_markers_series()` using `itertools.product` over marker list + color palette
- **Legend ordering / filtering** — allow reordering legend entries, filtering by series

---

## 📋 Phase 16 — IO / Data subpackage (`geofig_engine.io`)
Port and generalize geochemplot's data-handling utilities.

- **EQuIS format conversion**:
  - `equisflat_to_sample_df()` — pivot EQuIS flat to wide
  - `sample_df_to_equisflat()` — melt wide to EQuIS flat
  - `equis_crosstab_to_flat()` — parse EQuIS cross-tab Excel
- **Unit utilities**:
  - `equisflat_normalize_units()` — normalize SI prefixes (nano→milli→kilo) within analyte groups
  - `fill_bicarbonate_as_hco3()` — compute HCO3+CO3 from alkalinity + pH + temperature
  - Ion weight / charge tables for mg/L → meq/L conversion
- **Column utilities**:
  - `ecesis_to_sample_df()` — parse Ecesis-style column names with embedded units
  - `create_bins()` — create categorical bins from numeric/datetime columns (range or quantile)
- **Geospatial utilities**:
  - `haversine()` — great-circle distance
  - `path_distance()` — cumulative path distance along ordered points
- **General generators**: `gen_markers()`, `gen_markers_series()`, `gen_markers_cross_grouping()`

---

## 📋 Phase 17 — Infrastructure

- **Multithread / parallel iteration processing** — parse iterators in parallel thread pool
- **Data preprocessing pipeline** — assign new columns / groups / aggregates before spec building
- **Multi-page figure output** — render multiple specs onto pages (e.g., PDF with one plot per page)
- **Axis limit overrides per layer** — expose xlim/ylim per layer, not just globally
