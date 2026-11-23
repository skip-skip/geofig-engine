# Phase 19: tests, docs, and roadmap closeout

**Status**: complete
**Phase**: 19
**Version target**: v0.5.0
**Dependencies**: `19_wp1_spec_only_template_api`,
`19_wp2_dashboard_wire_schema`, `19_wp3_incremental_update_protocol`

## Description

Close out Phase 19 with cross-cutting contract tests and documentation. Pin the
spec-only API, dashboard snapshot/patch schemas, strict JSON behavior, and the
boundary between the dashboard wire format and the unchanged Matplotlib path.
Finalize the roadmap/changelog record and review the epic. The version bump is a
separate release commit and is not part of this ticket.

## Changes

### Tests

- `tests/test_engine_new_api.py`
  - Finalize `build_template_specs` parity with `render_template` internals.
- `tests/test_serialize_dashboard.py`
  - Complete all-ten-key coverage, determinism, strict JSON, legend, and hash
    behavior checks.
- `tests/test_dashboard_patch.py`
  - Complete operation, validation, revision, and immutability coverage.
- `tests/test_no_upstream_imports.py` (or existing source-scan tests)
  - Add `serialize/dashboard.py` and `serialize/dashboard_patch.py` to the
    no-`geodata` / no-`geochemmodel` source scan.
- Run the pinned full suite invocation and record the final count.

### Documentation

- `docs/api/engine.md`
  - Document `build_template_specs(...)` signature, return type, supported
    inputs, and its relationship to `render_template`.
- `docs/api/serialize.md`
  - Add a `Dashboard wire format` section covering:
    - snapshot envelope and `schema_version`;
    - template definition vs columnar data split;
    - stable IDs, `template_hash`, and `revision`;
    - patch operations and stale-patch rejection;
    - strict JSON normalization rules;
    - the explicit statement that `spec_to_json` / `spec_from_json` remain the
      Python round-trip format and that `MatplotlibRenderer` still consumes
      `FigureSpec` objects.
- `ARCHITECTURE.md`
  - Add a short section for the dashboard serialization boundary.
  - State that the wire format is downstream of `FigureSpec` and parallel to
    (not replacing) the renderer path.
- `ROADMAP.md`
  - Replace the Phase 19 planned entry with a completed entry including WP names
    and final suite count.
- `CHANGELOG.md`
  - Draft `[v0.5.0]` Added/Changed entries; date is finalized at release.

### Epic review

- Update `tasks/open/19_00_epic.md` with explicit `[x]` completion markers as
  each criterion is verified.
- Record the epic review outcome and the release-step reminder in the epic.

## Acceptance criteria

- [ ] Full suite green with no new skips; baseline **1576 passed / 8 skipped**
      plus new tests; the 8 skips remain pyproj/upstream-gated
- [ ] All Phase 19 acceptance criteria in `19_00_epic.md` are checked
- [ ] Docs reflect the implemented API; no planned-but-missing API is documented
      as shipped
- [ ] `ROADMAP.md` records Phase 19 complete with final suite count
- [ ] `CHANGELOG.md` drafts v0.5.0 without bumping `pyproject.toml`
- [ ] No upstream imports, no new required dependency, no Matplotlib rendering
      behavior change
- [ ] Committed as a single commit
      (`geofig-engine: dashboard serialization tests and docs → v0.5.0`)

## Files

- `tests/test_engine_new_api.py`, `tests/test_serialize_dashboard.py`,
  `tests/test_dashboard_patch.py`, source-scan tests
- `docs/api/engine.md`, `docs/api/serialize.md`
- `ARCHITECTURE.md`, `ROADMAP.md`, `CHANGELOG.md`
- `tasks/open/19_00_epic.md`
