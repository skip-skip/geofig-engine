# Phase 19: spec-only template build API

**Status**: complete
**Phase**: 19
**Version target**: v0.5.0
**Dependencies**: none (the open `19_00_epic` is a review ticket, not a blocking
implementation dependency)

## Description

Extract the template → `FigureSpec` portion of `render_template` into a public
`build_template_specs(...)` function. `render_template` becomes a consumer of
that function and retains its current renderer/legend/`savedir` behavior. This
gives the dashboard serializer a Matplotlib-free spec source and removes the
need for callers to duplicate recipe/provider/generator wiring.

## Changes

### `src/geofig_engine/engine/api.py`

- Add:

  ```python
  def build_template_specs(
      data: pd.DataFrame | DataProvider | np.ndarray,
      template: str | FigureTemplate,
      mapping: dict[str, Any] | None = None,
      settings: dict[str, Any] | None = None,
      iterators: list[DimensionIterator] | None = None,
      facet: Facet | None = None,
      coord: Coord | None = None,
  ) -> list[FigureSpec]: ...
  ```

- Move the current steps 1–4 of `render_template` into it: data coercion,
  template/recipe resolution, settings/coord merge, `SpecRecipe` branch,
  `TemplateRecipe` override/generator branch, and `generator.build_specs()`.
- Keep the existing `SpecRecipe` restrictions (`iterators` / `facet` unsupported)
  and the informative `ValueError` messages unchanged.
- Keep lazy required-channel validation at spec-build time.
- Change `render_template` to call `build_template_specs(...)` with the same
  arguments, then perform renderer gating, `render_all`, legend accumulation,
  and optional saving exactly as today.

### `src/geofig_engine/__init__.py`

- Export `build_template_specs` alongside `render_template`.
- Add it to `__all__` under the public API section.

### Tests

- `tests/test_engine_new_api.py`
  - Add `TestBuildTemplateSpecs` covering DataFrame / provider / ndarray inputs,
    registry-key and direct-recipe templates, `mapping` / `settings` / `coord`
    overrides, iterators, and facets.
  - Assert spec count/order/context matches `FigureGenerator` output.
- `tests/test_declarative_api.py`
  - Assert `render_template` delegates to `build_template_specs` (spy or
    monkeypatch) and still returns figures only.
- `tests/test_pipeline_templates.py`
  - Assert all ten seeded keys build specs without rendering, including the two
    `SpecRecipe` keys.

## Acceptance criteria

- [ ] `build_template_specs(...)` returns `list[FigureSpec]` for all ten seeded
      keys and does not instantiate a renderer
- [ ] `SpecRecipe` keys keep their current restrictions and error messages
- [ ] `render_template(...)` return type, figure order, and saved PNG naming are
      unchanged
- [ ] `render_template` no longer contains the recipe/provider/generator wiring
      duplicated from `build_template_specs`
- [ ] New API is importable from `geofig_engine` and documented in the ticket's
      follow-up docs WP
- [ ] No upstream imports, no new dependency, no warning-policy skips
- [ ] Committed as a single commit
      (`geofig-engine: spec-only template build API → v0.5.0`)

## Files

- `src/geofig_engine/engine/api.py`
- `src/geofig_engine/__init__.py`
- `tests/test_engine_new_api.py`, `tests/test_declarative_api.py`,
  `tests/test_pipeline_templates.py`, `tests/test_deprecations.py`
