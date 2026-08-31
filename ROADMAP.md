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

## ✅ Phase 14.5 — Linked axes (818 tests)

Generalize multi-panel diagrams (Piper, later Stiff/Durov) from renderer-hardcoded GridSpec layouts into a declarative **linked axes** system. A figure has one **main axis** plus zero or more **links** — named secondary axes that share the same dataset and together form a *single full axis space*. Links are positioned by an ordered `LinkTransform` chain (translate → rotate → scale) declared in world units; one flat `Affine2D` per artist group stacked on the same `ax.transData`. `FigureSpec.root_transform` optionally composes a global transform on the main axis.

### Shipped

- ✅ **`LinkTransform` / `AxisLink` / `FigureSpec.links`** — `core/link.py` with ordered affine composition, `matrix()`, `transform_point()`, serialization
- ✅ **`TernaryCoord`** — projects three fractions summing to 1 into a right-triangle local space; generic, reusable for Durov/Ternary plots beyond Piper
- ✅ **`StatIonFractions`** — performs the chemistry before visualization (concentration addition, percent normalization, diamond coordinates); follows `Stat.compute(data) -> DataFrame` contract
- ✅ **Generic linked-axes render path** — single shared matplotlib Axes, `_render_linked`, `_stamp_new_artists`, `_linked_world_limits`, box frame provider, 18 unit tests
- ✅ **Piper re-expressed as linked-axes spec** — `build_piper_specs()` returns `FigureSpec` with 3 `AxisLink`s (left/right triangles + diamond), no template-side math. `piper_overlay_diamond()` is plain layer routing
- ✅ **PiperCoord deprecated** — still importable/serializable with `DeprecationWarning`; old `_render_piper` renderer path deleted
- ✅ **Legacy piper parity verified** — ternary/diamond positions match legacy math to 1e-12

### Verification

- Unit tests: `LinkTransform.matrix()` composition, `transform_point` anchors, `TernaryCoord` round-trips, layer routing, serialization round-trip
- 29 Piper tests (structure, rendering, geom compat, legacy parity)
- Stiff/Durov identified as follow-up beneficiaries (not in scope)

---

## ✅ Phase 14.51 — Linked axes refactor: nested FigureSpecs (794 tests)

Replace `AxisLink` + `LayerSpec.subplot` string-routing with nested `FigureSpec` children where frames are implied by coord type and transform. Depth-1 only — children must not nest.

### Shipped

- ✅ **Core model** — `FigureSpec` gains `children`, `transform`, `frame_config`; removes `links`, `root_transform`; `AxisLink` deleted; `LayerSpec` loses `subplot` and `coord`
- ✅ **Frame implication** — `_draw_implied_frame` auto-selects ternary/diamond based on coord type; `TernaryCoord` → triangle frame with auto-derived `ions`, `reversals`, `title`; `CoordCartesian` + `rotate` → diamond frame
- ✅ **Renderer refactor** — `_render_children` renders child FigureSpecs on one shared Axes; child coord transforms, frame stamping (snapshot→draw→stamp with affine), `_children_world_limits`
- ✅ **Piper template rewrite** — `build_piper_specs()` creates 3 child FigureSpecs (left, right, diamond) with own coord/transform/layers/frame_config; `piper_overlay_diamond` removed
- ✅ **Serialization** — recursive `_spec_to_dict`/`_spec_from_dict` for children; `link_to_dict`/`link_from_dict` deleted
- ✅ **Tests rewritten** — `test_links.py`, `test_piper.py`, `test_linked_render.py` updated for children API; 794 tests pass
- ✅ **Debug demo updated** — `debug_piper_axes.py` uses children API, no orange artifact

### Verification

- 794 tests pass (previously 676 non-linked + 142 linked tests)
- `hydro_demo.py` produces all 7 figures correctly
- `debug_piper_axes.py` renders 35 lines, 46 texts — frames with tick labels, grid, titles, ion arrows
- Piper serialization round-trip preserves children, transforms, frame_config

---

## ✅ Phase 14.52 — Fluent orderable transforms + generalized cartesian axis

Made `LinkTransform` a fluent, orderable builder (`LinkTransform().rotate(45).scale(...).translate(...)`) with call-order = point-operation order, and replaced the diamond special-case with a general cartesian-axis handler dispatched by coord type + frame hints in `settings` (removing the `rotate != 0` proxy).

- **WP1 Fluent LinkTransform** — `LinkTransform` is now an immutable, ordered-op builder: `rotate(deg)` / `scale(sx, sy)` / `translate(tx, ty)` each append an op to `.ops` and return a new instance; call-order = point-op order so `matrix()` = `T·S·R` reproduces the old diamond convention. Supports `transform_point(s)`, `transform_direction`, `matrix()`, and op-list (de)serialization via `to_dict()`/`from_dict()`.
- **WP2 Generalized cartesian-axis handler** — new `_draw_cartesian_axis(ax, matrix, settings)` subsumes the deleted `_draw_diamond_frame`; `_draw_implied_frame` dispatches by coord type + frame hints in settings (ternary → triangle, cartesian + `xlim`/`ylim` in settings → axes, cartesian without → no frame). `_child_local_bbox` reads bounds from settings. Tick/title text stays upright world-side; only geometry gets the affine.
- **WP3 Piper template + demo** — fluent transform construction for left/right triangles + diamond; diamond declares `[0,100]²` bounds + `grid_step`/`tick_step` in `settings`; renderer skips tick labels at bounding edges (interior 20–80 only).
- **WP4 Serialization** — ordered-op `to_dict`/`from_dict` round-trip through `figure_spec_to_dict`/`spec_from_json`; restore tuple-valued `xlim`/`ylim` after JSON (which coerces them to lists).
- **WP5 Tests** — rewrote `test_piper.py` / `test_linked_render.py` to the fluent API, asserting against `matrix()` / `.ops` directly; diamond render test passes explicit bounds. Full suite: **800 passed**.
- **WP6 Cleanup + ROADMAP** — no constructor-form (`LinkTransform(rotate=, translate=, scale=)`) or field reads remain; no `_draw_diamond_frame` / `rotate != 0` dispatch; `hydro_demo.py` renders all 7 figures with consistent per-sample colors and no orange regression; `debug_piper_axes.py` geometry unchanged (35 lines / 47 texts including DIAMOND title).
- **WP7-12 settings-based frames** — removed the `frame_config` field from `FigureSpec` entirely; frame hints (`title`, `xlim`/`ylim` bounds, `grid_step`, `tick_step`, `label_policy`) now live in each spec's `settings`. For children, `xlim`/`ylim` in settings are local-space frame bounds (e.g. diamond `[0,100]²`), not matplotlib axis limits; child settings feed only the frame-drawing logic, not the generic `_apply_settings` handler. Serializer round-trips `settings` (restoring tuple bounds); piper template + debug demo and all tests updated. Full suite: **800 passed**.

## ✅ Phase 14.53 — General secondary axis system for cartesian coordinates

Add a general secondary-axis system to the cartesian frame: secondary **x** and
secondary **y** axes that (a) draw tick labels on the frame's top/right edges and
(b) support plotting a second data series against them (twin-axis). Secondary
axes are transformed exactly like primary axes (local-space anchors stamped by
the child's `LinkTransform`, rotated per `label_policy`). Declared as structured
`settings` entries; used to add complement scales to the piper diamond.

- **Data model + mapping** — `core/secondary_axis.py`: `SecondaryAxis` (frozen
  dataclass: `range`, `tick_step`, `label_policy`, `position`, `label`,
  `primary_range`), `linear_mapping()` pure `fwd`/`inv` helpers,
  `tick_values()`/`tick_coordinates()`, and `parse_secondary_settings()`
  (validated declarative reader with default inheritance). matplotlib-free.
- **Frame tick-label rendering** — `_draw_cartesian_axis` draws secondary-x
  ticks on the top edge and secondary-y ticks on the right edge, plus optional
  world-side axis titles; both loops opt-in via the settings declarations, same
  `_apply_matrix_pts`/`label_rotation` path as primary ticks.
- **Piper diamond integration** — diamond child carries `secondary_x`/`secondary_y`
  with `[0,100]` ranges so its upper edges show the complement anion/cation scales
  (un-reversed — the reverse-scale idea was dropped in the layout change).
- **Data twin-axis** — `_remap_secondary_channels`: a layer whose visual mapping
  carries `x2`/`y2` (secondary units) is mapped through the matching
  `SecondaryAxis.inv` into local `x`/`y` before rendering, then deforms with the
  child transform; missing matching declaration raises a clear error.
- **Serialization + validation** — `_settings_from_dict` restores tuple-valued
  `secondary_x`/`secondary_y` `range` entries after JSON; `_validate_secondary_settings`
  enforces the declaration shape on `FigureSpec` construction.
- **Type-system hardening** — `x2` added to `ALLOWED_TARGETS`, `Channel`, and
  `Mapping` (mirroring `y2`) so both twin-axis channels are first-class.
- **World limits** — `_children_world_limits` now includes `x2`/`y2` series
  (mapped to local coords) in the world-bounding-box computation.
- **849 tests pass**

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
  - Note: mg/L → meq/L conversion is intentionally excluded — deferred to an external data system
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
