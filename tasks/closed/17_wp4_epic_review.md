# Phase 17: Epic review + close tickets

**Status**: complete
**Phase**: 17
**Version target**: v0.3.0
**Dependencies**: `17_00_epic`, `17_wp3_column_utilities`

## Description

Final "epic review" ticket for Phase 17 — mirroring the per-phase closing
pattern (see `15_wp13_epic_review`). Verify the phase against the epic
(`17_00_epic.md`) acceptance criteria and the repository contracts, update
the ROADMAP (Phase 17 📋 → ✅), and close out the phase tickets.

## Steps

1. **Review vs epic** — walk the epic's six phase-level acceptance criteria;
   confirm `geofig_engine.io` exports the full utility set, conversions are
   deterministic/pure-pandas/non-mutating, contracts are docstring-documented
   with informative `ValueError`s, Excel access is `openpyxl`-gated in tests
   only, the full suite is green after every WP, and all commits are labeled
   `geofig-engine: <scope> → v0.3.0`.
2. **Contract compliance** — confirm `geofig_engine` still imports neither
   `geodata` nor `geochemmodel` and that `io/` modules add no new required
   dependencies (stdlib + numpy/pandas only).
3. **ROADMAP** — mark Phase 17 ✅ with the delivered WP trail and test counts;
   remove the Backlog "Marker/color combinatorial generator" item (shipped).
4. **Close out** — review `git status`/`git diff` (no secrets/stray files);
   move the epic and this ticket from `tasks/open` to `tasks/closed` with
   **Status**: complete; confirm working tree clean.

## Acceptance criteria

- [ ] Every epic phase-level criterion met; full suite green (1387 passed /
      6 skipped)
- [ ] Dependency rules verified (no upstream imports; no new required deps)
- [ ] ROADMAP Phase 17 marked ✅; shipped Backlog item removed
- [ ] Epic + review ticket moved to `tasks/closed` with **Status**: complete;
      working tree clean
- [ ] Phase summary posted (what shipped, test totals, follow-ups)

## Files

- `ROADMAP.md` (Phase 17 status + Backlog item)
- ticket housekeeping (`tasks/open/17_*.md` → `tasks/closed/`)

## Review findings

- **Findings for this phase:** all six epic ACs verified (see commit trail:
  `d091b7b` tasking, `c369361` equis, `98ca9b3` units, `2bf5a48` columns,
  `f6ea6a5` bicarbonate-drop) — counts 1353/1365/1387 passed, 6 skipped.
- **Recommendation (not performed here):** release commit `release:
  geofig-engine v0.3.0` + tag `geofig-engine-v0.3.0` (pyproject is still
  `0.2.0`) — an explicit release action per the versioning policy.
- **Follow-up (out of scope here):** `docs/api/io.md` + the README API table
  predate wp1–3 and document only geo/markers/preprocess; the equis/units/
  columns functions are documented in docstrings. A docs pass is recommended
  (either a small docs WP before the v0.3.0 release cut, or the next phase).
- **Pre-existing docs debt (observed, not touched):** Backlog "Dimension
  legend builder" also shipped earlier (`build_dimension_legend` already
  documented in `docs/api/renderers.md`) but is still listed in the Backlog.