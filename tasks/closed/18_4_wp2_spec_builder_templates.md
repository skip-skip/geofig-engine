# Phase 18.4: `piper` / `stiff` first-class registry builders

**Status**: complete
**Phase**: 18.4
**Version target**: v0.4.0
**Dependencies**: `18_4_wp1_native_recipe_builders`

## Description

Bring the two spec builders into the canonical template pathway without
flattening their inherently composite specs into the layer recipe. Add a small
`SpecRecipe` variant that returns `FigureSpec` object(s) from the provider
frame, and seed `piper` / `stiff` with native builders that use it. Existing
`build_piper_specs` and `plot_stiff` calls remain supported as compatibility
entry points.

## Changes

### `src/geofig_engine/engine/api.py`

- Add `SpecRecipe` (frozen dataclass) carrying `name`, `default_settings`, and a
  `build_specs(frame, mapping, settings, coord)` callable returning
  `list[FigureSpec]`.
- Extend `recipe_from` to pass `SpecRecipe` through unchanged and include it in
  the informative `TypeError` message for unsupported template objects.
- In `render_template`, dispatch recipes:
  - `TemplateRecipe` / duck-typed layer recipes continue through
    `FigureGenerator`;
  - `SpecRecipe` calls its builder with the coerced provider frame and the
    resolved `mapping` / `settings` / `coord`, then reuses the existing
    renderer, `LegendAccumulator`, and `savedir` persistence path.
- For `SpecRecipe`, reject `iterators` and `facet` with a clear `ValueError`
  (v0.4.0 limitation; documented in wp3).

### `src/geofig_engine/templates/piper.py`

- Add `piper_builder(mapping=None, settings=None, **_) -> SpecRecipe`.
- Settings keys: `left_tri`, `right_tri`, `title`, `labels`,
  `axis_label_policy`, `fontsize`, `point_size` (matching
  `build_piper_specs`).
- `SpecRecipe.build_specs` calls the existing `build_piper_specs(frame, ...)`
  so all linked-axes/ternary math stays in the data-to-spec stage.
- Keep `build_piper_specs` unchanged in signature and output.

### `src/geofig_engine/templates/stiff.py`

- Add `stiff_builder(mapping=None, settings=None, **_) -> SpecRecipe`.
- Canonical frame contract: one row with columns `ca`, `mg`, `na_k`, `cl`,
  `hco3`, `so4`; settings keys `title`, `figsize`, `fontsize`.
- Validate the one-row ion frame with an informative `ValueError`.
- Keep `plot_stiff(ca, mg, na_k, cl, hco3, so4, ...)` unchanged as a wrapper
  that builds the one-row frame and calls the same spec builder.

### `src/geofig_engine/engine/api.py` (registry)

- Seed `TEMPLATES["piper"] = piper_builder` and
  `TEMPLATES["stiff"] = stiff_builder`.
- Confirm no legacy adapter remains in the seed loop after wp1 + wp2.

## Acceptance criteria

- [ ] `render_template(data=piper_df, template="piper")` renders a single
      figure with the parent + three linked children
- [ ] `render_template(data=one_row_ion_df, template="stiff")` renders the same
      figure as `plot_stiff(...)` on equivalent inputs
- [ ] `piper` / `stiff` settings overrides are honored through the canonical
      `settings` dict
- [ ] `iterators` / `facet` with either spec recipe raise a clear
      `ValueError` mentioning the unsupported combination
- [ ] Existing `build_piper_specs` / `plot_stiff` tests remain green and
      deterministic (PNG-hash parity)
- [ ] Renderer code is unchanged; no data math moves into the renderer
- [ ] No public key or compatibility function removed; no upstream imports
- [ ] Committed as a single commit
      (`geofig-engine: piper and stiff registry builders -> v0.4.0`)

## Files

- `src/geofig_engine/engine/api.py`
- `src/geofig_engine/templates/piper.py`
- `src/geofig_engine/templates/stiff.py`
- `src/geofig_engine/templates/__init__.py` (builder exports)
- `tests/test_piper.py`, `tests/test_stiff.py`,
  `tests/test_pipeline_templates.py`
