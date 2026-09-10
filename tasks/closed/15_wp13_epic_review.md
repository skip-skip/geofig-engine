# Phase 15: Epic review + release v0.2.0 + close tickets

**Status**: complete
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_wp12_docs_roadmap`

## Description

Final "epic review" ticket for Phase 15. Verify the phase against the epic
(`15_00_epic.md`) acceptance criteria and the versioning policy, then release
v0.2.0 and close out the phase — mirroring the per-phase closing pattern
(see `14_59_wp17_commit`, but structured as an end-of-phase review rather than
a single-feature commit).

The release is an explicit task/commit per the `## Versioning` policy
("A version bump is its own explicit task/commit (`release: v0.2.0`)").
The bump is **MINOR**: additive public API (interop surface) + deprecations
introduced; nothing removed.

## Steps

1. **Review vs epic** — walk each `15_wp*` ticket; confirm its acceptance
   criteria are met; re-run the full suite (`pytest` from `geofig-engine/` with
   `PYTHONPATH=src`) and confirm the count (1039 baseline + new).
2. **Contract compliance** — confirm `geofig_engine` imports neither `geodata`
   nor `geochemmodel`; interop tests use `pytest.importorskip`; legacy path is a
   call/import-time `DeprecationWarning` only.
3. **Release** — `pyproject.toml` `version = "0.1.0"` → `"0.2.0"`; finalize
   `CHANGELOG.md` v0.2.0 entry (date, features, deprecations); commit
   `release: geofig-engine v0.2.0`; tag `geofig-engine-v0.2.0`.
4. **ROADMAP** — mark Phase 15 ✅ (entry added in `15_wp12`).
5. **Close out** — review `git status`/`git diff` (no secrets/stray files);
   move this and all `15_*` ticket files from `tasks/open` to `tasks/closed`
   with **Status**: complete; confirm working tree clean.

## Acceptance criteria

- [ ] Every `15_wp*` acceptance set met; full suite green
- [ ] Dependency rules verified (no upstream imports in `geofig_engine`)
- [ ] `version = "0.2.0"` in pyproject; `CHANGELOG.md` finalized
- [ ] Release commit + tag `geofig-engine-v0.2.0` present
- [ ] ROADMAP Phase 15 marked ✅
- [ ] All 14 `15_*` tickets (incl. epic) moved to `tasks/closed` with
      **Status**: complete; working tree clean
- [ ] Phase summary posted (what shipped, test totals, what M2 defers)

## Files

- none (git + task-file housekeeping + `pyproject.toml` version + `CHANGELOG.md`)