# Phase 18.4: native recipe builders for legacy factories

**Status**: complete
**Phase**: 18.4
**Version target**: v0.4.0
**Dependencies**: none (the open `18_4_epic` is a review ticket, not a blocking
implementation dependency)

## Description

Make native registry builders the source of truth for the eight legacy
`FigureTemplate` factories. Each template module gains a builder that returns
the canonical `TemplateRecipe`; the existing factory stays as a compatibility
wrapper. The registry seeds those builders directly, and `render_template`
passes `mapping` / `settings` into key builders so template-specific kwargs are
reachable through the canonical API.

## Changes

### `src/geofig_engine/engine/api.py`

- In the string-template branch of `render_template`, call the registry builder
  with `mapping=mapping, settings=settings` instead of calling it with no
  arguments.
- Keep the existing `_apply_mapping_override` and
  `{**recipe.default_settings, **(settings or {})}` merge for direct
  `FigureTemplate` / recipe objects so those paths stay behaviorally
  unchanged.
- Remove `LEGACY_FACTORIES` / `legacy_adapter` from registry seeding. Seed the
  eight native builders explicitly.
- Leave `recipe_from`'s `FigureTemplate` adaptation intact and warning-free.

### Legacy template modules (native builders)

For each module below, add `*_builder(mapping=None, settings=None, **_) ->
TemplateRecipe` with the existing `TemplateRecipe` lazy-import pattern. Move the
current layer/stat/default construction into the builder; the legacy factory
delegates to the builder and converts the recipe to `FigureTemplate`.

- `src/geofig_engine/templates/histogram.py` — `histogram_builder`; settings
  `bins`, `density`, `cumulative`.
- `src/geofig_engine/templates/pie.py` — `pie_builder`; settings
  `show_percent`, `show_count`, `show_name`.
- `src/geofig_engine/templates/radar.py` — `radar_builder`; settings `fill`,
  `fill_alpha`, `shared_axes`.
- `src/geofig_engine/templates/timeseries.py` — `timeseries_builder`; no extra
  knobs.
- `src/geofig_engine/templates/isotope.py` — `isotope_builder`; settings
  `functions`, `auto_filter`.
- `src/geofig_engine/templates/npr_nnp.py` — `npr_nnp_builder`; settings
  `npr_crit`, `nnp_crit`.
- `src/geofig_engine/templates/anp_agp.py` — `anp_agp_builder`; no extra knobs.
- `src/geofig_engine/templates/nagph_nag.py` — `nagph_nag_builder`; no extra
  knobs.

Renderer defaults (`*_DEFAULTS`) must not change. Template-specific settings
merge into the builder's computation and the recipe defaults; renderer settings
continue to merge on top in `render_template`.

### `src/geofig_engine/templates/legacy.py`

- Keep `LEGACY_DEFAULT_MAPPING`, `LEGACY_FACTORIES`, and `legacy_adapter` as
  compatibility surfaces, but stop importing them from `engine/api.py`.
- Emit a call-time `DeprecationWarning` from `legacy_adapter` naming the
  deprecated shim and the native builder/key replacement.
- Update the module docstring: "retained compatibility shim, no longer used by
  the registry; removed no earlier than 1.0.0".

### `src/geofig_engine/templates/__init__.py`

- Export the eight new `*_builder` functions alongside the existing factories.
- Keep all existing exports and `__all__` entries intact.

## Acceptance criteria

- [ ] `get_template(key)` returns the native builder for all eight keys (e.g.
      `get_template("histogram") is histogram_builder`)
- [ ] `render_template(data, template=key, mapping=..., settings=...)` renders
      all eight keys with factory kwargs honored through flat settings
- [ ] `render_template(..., template="histogram", mapping={"x": "other_col"})`
      bins `other_col`, not the legacy stub `x`
- [ ] Existing factory functions still return `FigureTemplate` and produce the
      same layers/defaults as before
- [ ] `legacy_adapter(...)` still works but emits a call-time
      `DeprecationWarning`; tests use `pytest.warns`, not warning skips
- [ ] `recipe_from(FigureTemplate)` remains warning-free and unchanged
- [ ] No public key, factory, or shim removed; no upstream imports added
- [ ] Committed as a single commit
      (`geofig-engine: native recipe builders for legacy templates -> v0.4.0`)

## Files

- `src/geofig_engine/engine/api.py`
- `src/geofig_engine/templates/histogram.py`
- `src/geofig_engine/templates/pie.py`
- `src/geofig_engine/templates/radar.py`
- `src/geofig_engine/templates/timeseries.py`
- `src/geofig_engine/templates/isotope.py`
- `src/geofig_engine/templates/npr_nnp.py`
- `src/geofig_engine/templates/anp_agp.py`
- `src/geofig_engine/templates/nagph_nag.py`
- `src/geofig_engine/templates/legacy.py`
- `src/geofig_engine/templates/__init__.py`
- `tests/test_declarative_api.py`, `tests/test_pipeline_templates.py`,
  `tests/test_templates.py`
