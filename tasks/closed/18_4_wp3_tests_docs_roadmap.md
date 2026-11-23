# Phase 18.4: tests, docs, and roadmap closeout

**Status**: complete
**Phase**: 18.4
**Version target**: v0.4.0
**Dependencies**: `18_4_wp1_native_recipe_builders`,
`18_4_wp2_spec_builder_templates`

## Description

Close out the template-pathway unification with contract/parity coverage and
documentation. Replace the old "spec builder keys raise with guidance" tests
with successful canonical rendering, pin compatibility surfaces, and update the
docs/roadmap so all ten seeded keys are described as first-class registry
templates. Prepare the v0.4.0 changelog; the version bump itself stays in the
separate release commit.

## Changes

### Tests

- `tests/test_pipeline_templates.py`
  - Replace `SPEC_BUILDER_KEYS` guidance-error tests with successful
    `render_template` tests for `piper` / `stiff`.
  - Assert all ten seeded keys resolve to native builders and render.
  - Add PNG-hash parity for the eight factory keys where deterministic.
  - Pin that `legacy_adapter` is no longer referenced by registry seeding.
- `tests/test_templates.py`
  - Update `TestLegacyAdapter` to require the new `DeprecationWarning`.
  - Add native-builder tests proving factories delegate to builders.
- `tests/test_declarative_api.py`
  - Pin that string-key rendering passes `mapping` / `settings` into the
    builder (use a recording builder).
  - Keep direct `FigureTemplate` / recipe override tests unchanged.
- `tests/test_piper.py` / `tests/test_stiff.py`
  - Add canonical `render_template` parity tests against the existing direct
    spec builders.
  - Pin the `SpecRecipe` `iterators` / `facet` error contract.

### Documentation

- `docs/api/engine.md`
  - Seeded-keys table: native builders for all ten keys; remove the
    legacy-adapted and "raises TypeError" notes.
  - Document builder call arguments and flat template-specific settings keys.
  - Document `SpecRecipe` scope/limits and the one-row `stiff` frame contract.
  - Keep the deprecation table unchanged except for the new
    `legacy_adapter` row (removed no earlier than 1.0.0).
- `docs/api/templates.md`
  - Builder-first framing; `FigureTemplate` and scalar/spec-builder functions
    documented as compatibility surfaces.
  - Add native builder signatures and settings tables.

### Repository docs

- `ARCHITECTURE.md`
  - `## Templates & Registry`: all seeded keys share the canonical pathway;
    `SpecRecipe` documented as the linked/composite spec variant.
  - Update any remaining "legacy factory adapters" / "piper, stiff cannot be
    registered" wording.
- `ROADMAP.md`
  - Add a `## ✅ Phase 18.4 — Legacy template pathway unification` entry with
    WP names and final suite count.
  - Update Phase 15 wording from "thin adapters re-register the legacy factory
    set" to reflect native builders plus retained compatibility shims.
- `CHANGELOG.md`
  - Draft the `[v0.4.0]` Added/Changed/Deprecated entries (date finalized at
    release).
  - State explicitly that nothing was removed and shims remain until >= 1.0.0.

### Verification

- Run `git diff --check`.
- Run targeted tests, then the full suite with the pinned invocation:
  `$env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider`
- Confirm suite stays at or above the 1501-pass baseline plus new tests; the 8
  upstream-gated skips remain the only skips.

## Acceptance criteria

- [ ] All ten legacy keys render through `render_template` with no
      "not registry-adaptable" errors
- [ ] Builder contract, native seeding, and compatibility wrappers are covered
      by tests
- [ ] Full suite green with no warning-policy skips
- [ ] `docs/api/engine.md`, `docs/api/templates.md`, `ARCHITECTURE.md`,
      `ROADMAP.md`, and `CHANGELOG.md` reflect the finalized architecture
- [ ] No public key, factory, or shim removed; no upstream imports or new
      required dependencies
- [ ] Committed as a single commit
      (`geofig-engine: template unification tests and docs -> v0.4.0`)

## Files

- `tests/test_pipeline_templates.py`, `tests/test_templates.py`,
  `tests/test_declarative_api.py`, `tests/test_piper.py`, `tests/test_stiff.py`
- `docs/api/engine.md`, `docs/api/templates.md`
- `ARCHITECTURE.md`, `ROADMAP.md`, `CHANGELOG.md`
