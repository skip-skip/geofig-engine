# Phase 18.1: WP3 — Docs + ROADMAP (facet panel semantics)

**Status**: complete
**Phase**: 18.1
**Version target**: v0.3.1+
**Dependencies**: `18_1_wp2_facet_tests`

## Description

Sync the public documentation with the restored facet contract (one
multi-panel figure, not one figure per group) and record the mini-phase in
the ROADMAP with accurate Phase 18 statuses.

## Changes

1. **`docs/api/engine.md`**
   - `render_template` parameter table, `facet` row (line 57): replace
     "Optional facet spec for one-spec-per-group splitting" with panel
     semantics — e.g. "Optional facet spec; splits the data into panels
     within a single figure (renderer-side). One figure per iterator
     combination, each containing the full facet panel grid. Defaults to
     `FacetNull()`."
   - `FigureGenerator.build_specs` row (line 178): replace the
     facet-split resolution order with: expands iterators (`provider.expand`)
     → resolves channel selectors (`provider.resolve`) + scales → packages
     into validated specs; facets are stamped on each spec and applied
     panel-wise by the renderer.
2. **`ROADMAP.md`** — insert after the Phase 17 entry:
   - Add `## ✅ Phase 18.1 — Facet / iterator consistency (bug-fix
     mini-phase)` bullet: one multi-panel figure per facet spec through
     `render_template`; `facet=` + `iterators=` compose as N figures each
     carrying the full panel grid; empty combos no longer raise
     `ValueError: Facet produced zero panels`; generator context/`iterator_key`
     carry iterator keys only (parity with legacy). Reference
     `tasks/closed/18_1_*.md` once closed.
   - Annotate the `## 📋 Phase 18 — Infrastructure` item list with statuses:
     "Data preprocessing pipeline" → shipped (Phase 17, `io/preprocess.py`);
     "Axis limit overrides per layer" → shipped (Phase 14, `de36ea1`);
     "Multithread / parallel iteration processing" and "Multi-page figure
     output" → remain open.
3. No code changes in this WP (docs/ROADMAP only).

## Acceptance criteria

- [ ] `docs/api/engine.md` describes `facet` as panel-splitting within one
      figure; `build_specs` row no longer mentions facet pre-splitting
- [ ] ROADMAP gains the Phase 18.1 entry and updated Phase 18 item statuses
- [ ] No source/test files modified in this WP
- [ ] Full suite green (docs-only changes)

## Files

- `docs/api/engine.md`
- `ROADMAP.md`