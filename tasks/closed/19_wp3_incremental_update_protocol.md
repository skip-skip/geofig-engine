# Phase 19: incremental update protocol

**Status**: complete
**Phase**: 19
**Version target**: v0.5.0
**Dependencies**: `19_wp2_dashboard_wire_schema`

## Description

Add a transport-agnostic patch format so a frontend can apply higher-frequency
template and data updates without resending a full figure snapshot. Patches are
derived from two dashboard snapshots and can be applied to a prior snapshot to
reproduce the newer one exactly. No WebSocket/SSE/HTTP transport is added.

## Changes

### `src/geofig_engine/serialize/dashboard_patch.py` (new)

- Define schema constants:

  ```python
  DASHBOARD_PATCH_SCHEMA = "geofig-engine/dashboard-patch"
  DASHBOARD_PATCH_SCHEMA_VERSION = 1
  ```

- Implement:

  ```python
  diff_dashboard_payload(old_payload, new_payload) -> list[dict] | dict
  apply_dashboard_patch(payload, patch) -> dict
  validate_dashboard_patch(patch) -> None
  ```

- Support these operations:

  ```json
  {"op": "replace_data", "figure_id": "...", "columns": {}}
  {"op": "append_data", "figure_id": "...", "columns": {}}
  {"op": "replace_definition", "figure_id": "...", "definition": {}}
  {"op": "update_settings", "figure_id": "...", "settings": {}}
  {"op": "remove_figure", "figure_id": "..."}
  ```

- Patches carry `schema`, `schema_version`, `revision`, and optional
  `base_revision`. `apply_dashboard_patch` rejects stale or out-of-order
  patches when `base_revision` is present and does not match the target.
- `apply_dashboard_patch` returns a new payload; it never mutates its input.
- Data-only diffs emit `replace_data` / `append_data` with unchanged
  `template_hash`. Structural changes emit `replace_definition` with the new
  hash. Setting-only changes emit `update_settings` when the template hash is
  unchanged.
- Validation checks schema/version, operation names, required fields, known
  `figure_id`s, and revision types. Errors are clear `ValueError`s.

### `src/geofig_engine/serialize/__init__.py`

- Export the three patch functions and validator.
- Keep existing snapshot and round-trip exports unchanged.

### `src/geofig_engine/__init__.py`

- Export `diff_dashboard_payload`, `apply_dashboard_patch`, and
  `validate_dashboard_patch` at package root.

### Tests

- `tests/test_dashboard_patch.py` (new)
  - Data-only update: patch has only data ops; `template_hash` unchanged.
  - Append rows: patched payload equals fresh snapshot.
  - Definition update: patch carries new `template_hash` and definition.
  - Settings update: patch leaves data/definition unchanged except settings.
  - Remove figure: patched payload equals fresh snapshot.
  - Stale `base_revision`, unknown ID, unknown op, and unknown schema version
    each raise informative errors.
  - Input payload/patch remain unmutated after apply.
- `tests/test_serialize_dashboard.py`
  - Add an end-to-end build → snapshot → mutate data → diff → apply → compare
    test using `build_template_specs`.

## Acceptance criteria

- [ ] Applying a patch reproduces a freshly generated full snapshot
- [ ] Data-only updates never send a new template definition
- [ ] Definition changes are keyed by the new `template_hash`
- [ ] Stale/out-of-order patches are rejected
- [ ] Invalid patches raise clear errors without mutating inputs
- [ ] No transport implementation or frontend code added
- [ ] No upstream imports, no new required dependency
- [ ] Committed as a single commit
      (`geofig-engine: incremental dashboard update protocol → v0.5.0`)

## Files

- `src/geofig_engine/serialize/dashboard_patch.py` (new)
- `src/geofig_engine/serialize/__init__.py`
- `src/geofig_engine/__init__.py`
- `tests/test_dashboard_patch.py` (new), `tests/test_serialize_dashboard.py`
