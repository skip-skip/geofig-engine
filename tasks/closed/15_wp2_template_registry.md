# Phase 15: Template registry + recipe shape

**Status**: complete
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_00_epic`

## Description

Add the exported template registry and the duck-typed **template recipe**
(`ARCHITECTURE.md` "Template recipe" rule in §1a, and `## Templates & Registry`).
A recipe is returned by builders and consumed by the new `render_template`
(`15_wp4`):

```python
recipe = {"name": "bivariate", "layers": [...], "coord": CoordCartesian(),
          "default_settings": {...}}
```

`FigureTemplate` objects from `templates/base.py` are adapted to the same
shape so the whole legacy template set stays usable through the registry.
Missing *required channels* are **not** validated here — that check happens
lazily at spec-build time in `15_wp4`/`15_wp3` so every template has a usable
no-argument behavior.

## Changes

### `src/geofig_engine/engine/api.py` (new)

- `TemplateRecipe` shape — a small dataclass (`name`, `layers`, `coord`,
  `default_settings`) plus `recipe_from(template_or_recipe)`: passes recipes
  through, adapts `FigureTemplate` (its layers/coord/default settings) to a
  recipe.
- `TEMPLATES: dict[str, Callable[..., TemplateRecipe]]` — exported registry
  mapping template key → builder callable (builders may accept mapping/settings
  overrides; plain-dict semantics for now).
- `register_template(name, builder)` — string name + callable; **override
  allowed** (downstream adapters like geochemmodel workflows register/resolve
  keys without engine changes). Invalid name/builder raises `ValueError`.
- `get_template(name)` — returns the builder; unknown key raises `KeyError`
  with a helpful message listing available keys.

### `src/geofig_engine/__init__.py`

- Export `TEMPLATES`, `register_template`, `get_template` (public `__all__`
  split finalized in `15_wp5`).

## Acceptance criteria

- [ ] `TEMPLATES` is exporter-visible and a plain dict of key → builder
- [ ] `register_template("x", builder)` adds; re-registering the same key overrides without error
- [ ] `get_template("x")` returns the builder; `get_template("nope")` raises `KeyError` listing keys
- [ ] `recipe_from(FigureTemplate)` yields `layers`/`coord`/`default_settings`/`name`
      matching the template's definition; recipes pass through unchanged
- [ ] `register_template` rejects non-string names and non-callables
- [ ] No `geodata`/`geochemmodel` import in `engine/api.py`
- [ ] New `tests/test_template_registry.py` covers the above
- [ ] Committed as a single commit (`geofig-engine: add template registry + recipe → v0.2.0`); full suite green

## Files

- `src/geofig_engine/engine/api.py` (new)
- `src/geofig_engine/__init__.py`
- `tests/test_template_registry.py` (new)