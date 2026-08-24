# Roadmap

Completed phases are marked with ✅. Remaining work is organized by theme.

---

## ✅ Phase 1–9 — Core GoG foundation
All 9 phases from the original refactor: Geom, Stat, Scale, Coord, Facet, LayerSpec, FigureSpec, Resolver pipeline, MatplotlibRenderer + 8 geom handlers, facet rendering, legend system, serialization, simplified `render_template` entry.

---

## ✅ Phase 10 — Remaining simple Geom types
Four implemented (one later refactored to GoG pattern).

- `GeomBox` — boxplot with configurable show_points (jitter), show_n, min_box_n, showfliers, showmeans, horizontal orientation; color palette via `_apply_box_colors()`; alpha from visual mapping
- `GeomViolin` — violin plot with show_medians, log_scale; alpha passed to bodies
- `GeomStepLine` — step line with drawstyle (where="pre"|"mid"|"post"), black default color
- **Shared utilities extracted**: `dodge_positions()` in `position.py` used by box and violin; `_sort_and_filter_groups()` with multi-mode sorting including `value_forward`/`value_reverse`
- ✅ **Histogram refactored** — `GeomHistogram` removed; replaced by `StatBin` + `GeomBar` composed via `histogram()` template in `templates/histogram.py`. `StatBin.compute()` bins data via `np.histogram`, returns `x`, `y`, `width` columns. Resolver in `generator.py` resolves stat-produced columns from `stat_data` before falling back to the original dataset.
- ✅ **Black outline defaults** — `render_bar`, `render_step_line`, `render_histogram` (and box/violin) all default to black edgecolor/color with `linewidth=0.5`
- ✅ **xtick preservation fix** — `_apply_settings` now guards `set_xscale`/`set_yscale` against redundant `"linear"` calls that reset tick locators

---

## ✅ Phase 11 — Enhanced bar / area features
Extend existing `GeomBar` and `GeomArea` handlers and the visual-mapping / stat pipeline.

- **Bar stacking** — new `StatStack` or `stack_col` in bar mapping that stacks series
- ✅ **Bar / boxplot sorting** — multi-mode sort via `_sort_and_filter_groups()` in `handlers.py`: `none`, `forward`, `reverse`, `value_forward`, `value_reverse`
- ✅ **Bar / boxplot smush** — smush parameter in `_sort_and_filter_groups()` removes gaps when a series is absent within a group
- ✅ **`StatBin` implemented** — `StatBin.compute()` bins a numeric column into `x`, `y`, `width` using `np.histogram`, supporting `bins`, `density`, `cumulative`, and `range` parameters. Resolver in `generator.py` routes stat-produced columns directly from `stat_data`.
- **Continuous color ramp** — `GeomPoint` / `GeomLine` support for mapping a numeric column to a continuous color scale (e.g., viridis), not just categorical

---

## ✅ Phase 12 — Circular / pie / spider geoms
Implemented via GoG composition:
- `StatSum` + `GeomBar` + `CoordPolar` → pie chart (`templates/pie.py`)
- `StatRadar` + `GeomArea` / `GeomLine` + `CoordPolar` → spider/radar (`templates/radar.py`)
- `GeomBar.position` for stacking/fill; `StatSum` supports `show_percent`/`show_count`/`show_name`
- **Phase A–D**: closing, normalisation, angle mapping moved from `StatRadar` → handlers / `ScaleNormalize` / `CoordPolar.transform_visual_mapping()`

---

## ✅ Phase 13 — Annotation / reference layer system
- `GeomHSpan` / `GeomVSpan` / `GeomRect` — shaded region annotations in data coordinates
- `GeomAbline` — slope-intercept + two-point reference lines via `ax.axline()`
- `GeomText` — `angle` channel for rotation, `bbox` channel for bounding boxes, `_measure_text_px()` helper
- Per-layer `zorder` control — optional field on `Layer`/`LayerSpec`; overrides auto-increment in `_render_axes()`
- ✅ **526 tests pass**

---

## ✅ Phase 14 — Specialized coord systems
Complex multi-element diagrams that don't fit a single Coord + Geom.

- **PiperCoord** — ternary cation/anion triangles + diamond projection. Front-end handles mg/L→meq/L conversion, temperature-dependent pKa for alkalinity speciation, combined Na+K / HCO3+CO3.
  - `build_piper_specs()` → factory function creating a FigureSpec with PiperCoord (renderer creates 3-panel GridSpec)
  - Optional overlay API via `piper_overlay_diamond()`
- **StiffCoord** — 6-axis polygon per sample. Single-sample function, not a general-purpose geom.
  - Standalone function `plot_stiff(ca, mg, na_k, cl, hco3, so4, ...)` returning a FigureSpec
- **Classification plot templates** (composition over inheritance — reuse GeomPoint + annotation layers):
  - `npr_nnp(mapping)` template adding shaded bands + quadrant labels (GeomRect + GeomAbline + GeomText)
  - `anp_agp(mapping)` template adding reference slope lines + region labels (GeomAbline + GeomText)
  - `nagph_nag(mapping)` template adding threshold lines + auto-placed labels (GeomVSpan + GeomAbline + GeomText)
- **585 tests pass** (526 existing + 59 new)

---

## 📋 Phase 14.5 — Linked axes (planned)

Generalize multi-panel diagrams (Piper, later Stiff/Durov) from renderer-hardcoded GridSpec layouts into a declarative **linked axes** system. Today `_render_piper()` (renderers/matplotlib/renderer.py) manually builds a 3-panel layout that the spec cannot express — a violation of the Data→Spec→Render separation. Linked axes move composition into the spec.

### Concept

A figure has one **main axis** plus zero or more **links**: named secondary axes that share the same dataset and together form a *single full axis space*. The main axis owns an optional **root transform** (`M_main`, e.g. the diamond's rotate-then-squish); **world space is defined as the main axis's post-transform data space**. Each link is positioned by an ordered transform chain — **translate → rotate → scale** — with translate declared in world units, so template declarations read visually ("lower-left of the visible diamond"). Matrices stay flat: one `Affine2D` per artist group stacked on the same `ax.transData` (no scene-graph nesting). Links are grouped axes, not facets: all layers render into one shared canvas.

### Core model (`core/link.py`, new)

- **`LinkTransform`** (frozen dataclass) — ordered affine parameters:
  - `translate: tuple[float, float]` — offset in world units (post-transform main-axis space)
  - `rotate: float` — degrees about the link's local origin
  - `scale: tuple[float, float]` — squash/stretch applied along world x/y axes, after rotation
  - `matrix() -> np.ndarray` — pure-numpy 3×3 homogeneous composition `M = T·S·R` built in core (matplotlib-free): points experience **rotate → scale → translate** (scale after rotation is what makes the diamond's "rotate 45°, then squash y" expressible); convention pinned by known-corner unit tests, since fluent Affine2D call-order ≠ point-application order
  - `transform_point(xy)` — maps local anchors into world space (used for label placement)
- **`AxisLink`** (frozen dataclass) — `name: str`, `coord: Coord` (e.g., new `TernaryCoord`), `transform: LinkTransform`, optional `frame` styling
- **Layer routing** — reuse the existing `LayerSpec.subplot: str | None` field: a layer with `subplot="cation"` renders through that link's transform+coord; unrouted layers stay on the main axis
- **FigureSpec** gains `links: tuple[AxisLink, ...] = ()`; validation: unique names, every layer `subplot` must resolve to a defined link or None
- Serialization: `link_to_dict()` / `link_from_dict()` in `serialize/converters.py`

### New projection: `TernaryCoord` (`core/coord.py`)

- Maps three fractions summing to 1 into a right-triangle local space ([0,1]²), configurable vertex order and handedness (left/right facing)
- Implements `transform_visual_mapping()` so geoms stay projection-agnostic (same pattern as CoordPolar)
- Generic — reusable for Durov/Ternary plots beyond Piper

### Renderer changes (matplotlib backend)

- Replace per-diagram special cases with one generic path: a single matplotlib Axes spans the whole figure (world = post-transform main-axis data space); the main axis draws through `M_main + transData`, each link through its own `Affine2D.from_values(M_link) + transData`
- **Frame providers** — pluggable callables with signature `(link_matrix, parent_axes, label_policy)` that draw frames/grids/tick-marks in local space through the transform stack (generalizes today's `_draw_ternary_frame` / `_draw_diamond_frame`)
- **Label policy** — text never inherits transforms: tick numerals/vertex names/edge labels are drawn world-side at `transform_point()` anchors; policies `upright` (default, rotation=0) and `parallel` (rotation from transformed edge tangent, squash-aware). Data, frames, grids, tick marks deform with the axis; annotations do not
- Delete `_render_piper()`, `"piper_layout"` / `"piper_overlay"` setting branches, and the PiperCoord isinstance dispatch at renderer.py:103
- Legends/facets operate on the single shared axes unchanged

### Stats layer

- **`StatIonFractions`** (new, `core/stat.py`) — performs the chemistry before visualization, on meq/L inputs only:
  - Concentration addition: Na+K, HCO3+CO3 grouping
  - Percent normalization per sample → fixed-slot fraction columns (`cation_f0/f1/f2`, `anion_f0/f1/f2`) plus derived diamond coordinates (`diamond_x/y`)
  - Follows the `Stat.compute(data) -> DataFrame` contract; one configured instance shared by all piper layers, mapping strings resolved via existing stat_data routing
  - Replaces the coordinate math currently embedded in the piper template front-end
- **mg/L → meq/L conversion lives upstream**, not in the stat: a Phase 17 `PipelineStep` in `io/preprocess.py` applies the existing ion weight/charge tables — keeps `core.stat` free of chemistry tables and preserves Data→Spec layering

### Piper re-expression (proof of concept)

- **Main axis**: cartesian square with a **root transform** — rotate 45° then squash y (~0.5) declared as `M_main`; no dedicated DiamondCoord class needed
- **Two links**: cation triangle (`TernaryCoord`, left-handed, world-anchored translate lower-left) and anion triangle (`TernaryCoord`, right-handed, translate lower-right)
- `build_piper_specs()` rewritten as pure spec construction (no renderer knowledge); `piper_overlay_diamond()` becomes ordinary layer routing
- Old `PiperCoord` deprecated after visual parity is confirmed

### Verification

- Visual parity harness comparing linked-axis piper output against current implementation output
- Unit tests: `LinkTransform.matrix()` composition conventions (incl. rotate-then-squish corner pinning), `transform_point` anchor mapping, TernaryCoord mapping round-trips, layer routing validation, serialization round-trip
- Stiff/Durov identified as follow-up beneficiaries (not in scope)

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

---

## ✅ Phase 18 — Categorized geom preset database
Replaced the function-registry JSON catalog (`data/functions.json`) with a data-only, categorized preset database in `src/geofig_engine/data/geom_presets/`. Adding a preset now requires only a JSON entry — no code changes.

- **`GeomPreset` / `GeomPresetItem` models** — frozen dataclasses: id, category, tags, items, reference/description/valid_domain/geospatial metadata; items carry validated geom params + constant visual mapping + optional zorder
- **Six annotation geom kinds** — `function_line`, `abline` (slope-intercept or two-point), `hspan`, `vspan`, `rect`, `text`; per-kind validation table (required/allowed mapping keys, bound ordering, scalar-only values)
- **Expression safety preserved** — function_line expressions route through the existing `FunctionValidator` (AST-based) at load time
- **Per-category JSON storage** — bundled `water_isotope.json` (15 migrated entries); loader globs the package directory so adding a file adds a category; errors annotated with file/index/id
- **`GeomPresetRegistry`** — queries by id/category/tags/state, metadata stats, `layers_for(ids)` + `auto_layers(category, geom_kinds)` hydration to standard Layers, lazy global singleton with reset hook
- **User extensibility** — `merge_path(path, overwrite=False)` merges external preset files into a registry at runtime (duplicate-id conflict raises unless overwrite)
- **Legacy shim** — `FunctionLoader.load()` / `get_function_registry()` rebuilt as MathFunction views over function_line presets (func_type retained per-item for lossless round-trip); existing tests pass unmodified
- **Isotope template switched** — `_load_functions()` now sources from `get_geom_preset_registry()`; public API unchanged
- **691 tests pass**
