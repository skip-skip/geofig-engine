# Phase 15: Docs, ROADMAP renumber, CHANGELOG

**Status**: open
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_wp11_interop_validation`

## Description

Synchronize the documentation with the implemented M1 surface, renumber the
ROADMAP to sequential phase order (as agreed — implementation order, not
historical numbering), and open the package `CHANGELOG.md` per the `##
Versioning` policy.

## Changes

### `ARCHITECTURE.md`

- `### Implementation status (documented plan ahead of code)` table: flip the
  implemented M1 rows from *planned* to *implemented* — `DataProvider` /
  `DataFrameProvider` / `DatasetProvider`, new `render_template`, legacy edge,
  `TEMPLATES` + `register_template`, `FigureGenerator`, geo geoms, `CoordGeo` +
  `[geo]` extra, `dendrogram`/`site_map`/`particle_overlay`, deprecation shims.
  Keep **deferred** rows as deferred (DEM contour / stream geoms, basemap tiles).
- §1a "Declarative API surface (planned implementation)" → "(implemented)";
  update any signature drift found while implementing (all-optional args,
  `savedir`, ndarray wrap).
- `## Versioning` "Public surface" stays as-is (matches what shipped).
- Note in Templates & Registry the concrete keys registered this phase.

### `ROADMAP.md`

- Insert a **Phase 15** entry after Phase 14.59 summarizing the delivered
  declarative API + provider refactor (list WPs, new test counts).
- Renumber the tail by **implementation order** so phase numbers ascend:
  - **Phase 16** — Categorized geom preset database ✅ (was Phase 18)
  - **Phase 17** — IO / Data subpackage 📋 (was Phase 16)
  - **Phase 18** — Infrastructure 📋 (was Phase 17)
  - The unnumbered legend/annotation backlog bullets stay unnumbered under a
    "Backlog" heading above Phase 15.
- This renumber is ROADMAP-only; no task-file renames.

### `CHANGELOG.md` (new, geofig-engine root)

- Skeleton per the versioning policy: `# Changelog`, then an
  `## [v0.2.0] - <date>` entry listing the additive M1 features and the new
  deprecations (shims + `render_template_legacy`), noting removals are ≥1.0.0.

## Acceptance criteria

- [ ] ARCHITECTURE status table truthfully reflects implemented vs deferred
- [ ] ROADMAP phase numbers are sequential (15 → 16 → 17 → 18) and Phase 15
      documents the delivered work
- [ ] No task-file renames performed; renumber is doc-only
- [ ] `CHANGELOG.md` created with a v0.2.0 entry (features + deprecations)
- [ ] All doc examples checked: `render_template` snippets in ARCHITECTURE
      §1a / `## Example Flow` match the shipped signature
- [ ] Committed as a single commit (`geofig-engine: docs + renumber ROADMAP → v0.2.0`); full suite green

## Files

- `ARCHITECTURE.md`
- `ROADMAP.md`
- `CHANGELOG.md` (new)