# Phase 18.4: Legacy template pathway unification

**Status**: complete
**Phase**: 18.4
**Version target**: v0.4.0 (MINOR — additive; no removals before 1.0.0)
**Dependencies**: none (phase overview / review ticket)

## Description

Resolve the remaining legacy template implementations into the canonical
`render_template` / `TEMPLATES` pathway so every seeded template key has one
architecture and one access route. Today eight `FigureTemplate` factories are
re-registered through `legacy_adapter`, and `piper` / `stiff` are registered as
spec builders that raise an informative `TypeError` when invoked through
`render_template`
(`src/geofig_engine/templates/legacy.py`, `src/geofig_engine/engine/api.py`).
`render_template` also calls registry builders with no arguments, so
template-specific factory kwargs cannot be reached through the key-based API.

This phase makes native builders the source of truth for all ten legacy keys,
passes `mapping` / `settings` into key builders, and adds a first-class
spec-recipe variant for the two inherently composite spec builders. No public
key, factory, or deprecated shim is removed; old entry points remain
compatible through at least the next MAJOR (>= 1.0.0).

## Decisions locked (with the requester)

- **All ten legacy keys are in scope**: `histogram`, `pie`, `radar`,
  `timeseries`, `isotope`, `npr_nnp`, `anp_agp`, `nagph_nag`, `piper`, `stiff`.
- **Target v0.4.0** (MINOR). The public gain is canonical rendering for every
  seeded key; nothing is removed. `pyproject.toml` stays at `0.3.2` until the
  separate release commit/tag.
- **Native builders own structure/defaults.** Each template module gains a
  `*_builder(...) -> TemplateRecipe` (or `SpecRecipe`) that is seeded in
  `TEMPLATES`. Existing `FigureTemplate` factories and scalar/spec-builder
  functions become thin compatibility wrappers over the same logic.
- **`render_template` passes overrides into key builders.**
  String-key resolution calls `builder(mapping=mapping, settings=settings)`;
  direct `FigureTemplate` / recipe objects keep the existing post-merge
  override behavior.
- **Flat template-specific settings keys** mirror the existing factory kwargs
  (`bins`, `density`, `cumulative`, `show_percent`, `fill`, `functions`,
  `npr_crit`, etc.). Generic renderer settings (`figsize`, `title`,
  `point_size`, feature dicts such as `contours` / `streams`) stay unchanged.
- **`legacy_adapter` is retained but unwired.** It gains a call-time
  `DeprecationWarning` and remains available until >= 1.0.0. `FigureTemplate`
  itself remains supported and warning-free in this phase.
- **`piper` / `stiff` use a first-class `SpecRecipe`.** They cannot be flattened
  into the current layer recipe without moving linked-axes/data-derived spec
  math into the renderer. `SpecRecipe` keeps `Data -> Spec -> Render` intact.
- **Stiff canonical input** is a one-row DataFrame with lowercase ion columns
  (`ca`, `mg`, `na_k`, `cl`, `hco3`, `so4`). `plot_stiff(ca, mg, ...)` remains
  as a compatibility wrapper.
- **Spec-recipe limits for v0.4.0**: `mapping`, `settings`, `coord`, and
  `savedir` are supported; `iterators` / `facet` with a spec recipe raise a
  clear `ValueError` rather than silently producing wrong figures.
- **No new dependencies, no upstream imports, no network**, and no
  warning-policy skips.

## Phase-level acceptance criteria

- [x] All ten legacy keys render successfully through
      `render_template(data, template=<key>)`, with no "not registry-adaptable"
      errors
- [x] The eight `FigureTemplate` factories are native `TemplateRecipe`
      builders seeded directly in `TEMPLATES`; `legacy_adapter` is no longer
      used for registry seeding
- [x] Factory kwargs are reachable through canonical `settings` and preserve
      current visual output (PNG-hash parity where deterministic)
- [x] `piper` and `stiff` render through `render_template` via `SpecRecipe`,
      with deterministic parity against their existing direct spec builders
- [x] `legacy_adapter` remains importable with a call-time
      `DeprecationWarning`; no key, factory, or shim is removed
- [x] `FigureTemplate` objects still pass through `recipe_from` unchanged and
      warning-free
- [x] No upstream (`geodata` / `geochemmodel`) imports, no new required
      dependency, no renderer-side data transformation introduced
- [x] Full suite green (**1576 passed / 8 skipped**) with no skips caused by
      the warning policy
- [x] Commits labeled `geofig-engine: <scope> -> v0.4.0` (target locked here)

## Ticket map

| Ticket file | Scope | Depends |
| --- | --- | --- |
| `18_4_wp1_native_recipe_builders.md` | Builder contract change + native builders for the eight `FigureTemplate` factories; legacy adapter unwired/deprecated | — (epic is a review ticket) |
| `18_4_wp2_spec_builder_templates.md` | `SpecRecipe` + `piper` / `stiff` registry builders; compatibility wrappers | `18_4_wp1_native_recipe_builders` |
| `18_4_wp3_tests_docs_roadmap.md` | Parity/contract tests, docs, ARCHITECTURE/ROADMAP/CHANGELOG updates, suite verification | `18_4_wp1_native_recipe_builders`, `18_4_wp2_spec_builder_templates` |

## Release step (after epic review)

A separate release commit/tag is required by `ARCHITECTURE.md` `## Versioning`:

1. bump `pyproject.toml` to `0.4.0`;
2. finalize `CHANGELOG.md` with the v0.4.0 date;
3. commit as `release: geofig-engine v0.4.0`;
4. tag `geofig-engine-v0.4.0`.

## Files

- `src/geofig_engine/engine/api.py`
- `src/geofig_engine/templates/*.py` (legacy factories, `legacy.py`, `__init__.py`)
- `tests/test_pipeline_templates.py`, `tests/test_templates.py`,
  `tests/test_declarative_api.py`, `tests/test_piper.py`, `tests/test_stiff.py`
- `docs/api/engine.md`, `docs/api/templates.md`
- `ARCHITECTURE.md`, `ROADMAP.md`, `CHANGELOG.md`, `pyproject.toml` (release only)
- this ticket set (`tasks/open/18_4_*.md`)
