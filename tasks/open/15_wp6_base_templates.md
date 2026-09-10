# Phase 15: Registry templates (bivariate, boxplot_with_points, legacy adapters)

**Status**: open
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_wp2_template_registry`, `15_wp4_render_template`

## Description

Register the pipeline templates that support **no mapping beside
`data`/`template`** (`ARCHITECTURE.md` `## Templates & Registry`: "usable with
no mapping beside `data`/`template` — their defaults resolve from the recipe"),
plus thin adapters that re-register the entire legacy factory set so it stays
usable through the same registry and `render_template`.

## Changes

### `src/geofig_engine/templates/bivariate.py` (pipeline builder)

- `bivariate_builder(mapping=None, settings=None, **_) -> TemplateRecipe` —
  `GeomPoint` + `CoordCartesian` scatter; `color` mapping used for grouping/
  cluster labels; sensible defaults (e.g. first two numeric columns as x/y when
  no mapping given); returns recipe with default settings.

### `src/geofig_engine/templates/boxplot_with_points.py` (pipeline builder)

- `boxplot_with_points_builder(...) -> TemplateRecipe` — `GeomBox` (with
  `show_points` jitter) + overlaid `GeomPoint`; defaults usable mapping-free.

### `src/geofig_engine/templates/legacy.py` (adapters)

- `legacy_adapter(builder)` — wraps an existing factory
  (`histogram`, `pie`, `radar`, `timeseries`, `isotope`, `npr_nnp`, `anp_agp`,
  `nagph_nag`, `piper`, `stiff`) and adapts its `FigureTemplate`/spec result to
  the recipe shape via `recipe_from`.

### `src/geofig_engine/engine/api.py`

- Seed `TEMPLATES` with the two pipeline builders + the ten legacy adapters.

## Acceptance criteria

- [ ] `render_template(df, template="bivariate")` renders with recipe defaults (no mapping)
- [ ] `render_template(df, template="boxplot_with_points", mapping={"x": ..., "y": ...})` renders boxes + jittered points
- [ ] All ten legacy keys resolve through `get_template` and render via the new `render_template`
- [ ] Legacy template output for the same inputs is **visually unchanged** vs the old path (compare rendered figures for piper/stiff/histogram)
- [ ] Missing required channels raise the informative spec-build error
- [ ] Tests extended in `tests/test_templates.py` (+ new `tests/test_pipeline_templates.py` for the two builders)
- [ ] Committed as a single commit (`geofig-engine: registry templates + legacy adapters → v0.2.0`); full suite green

## Files

- `src/geofig_engine/templates/bivariate.py` (new)
- `src/geofig_engine/templates/boxplot_with_points.py` (new)
- `src/geofig_engine/templates/legacy.py` (new)
- `src/geofig_engine/engine/api.py`
- `tests/test_templates.py`
- `tests/test_pipeline_templates.py` (new)