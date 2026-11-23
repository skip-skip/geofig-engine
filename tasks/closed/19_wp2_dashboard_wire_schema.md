# Phase 19: dashboard wire schema

**Status**: complete
**Phase**: 19
**Version target**: v0.5.0
**Dependencies**: `19_wp1_spec_only_template_api`

## Description

Add a versioned, browser-safe serialization format for dashboard display. The
format is a projection from resolved `FigureSpec` objects, not a replacement for
the existing Python round-trip serializer. It separates low-frequency template
structure from high-frequency columnar data, assigns stable identities, includes
legend data, and normalizes values so the JSON is safe for browser `JSON.parse`.

## Changes

### `src/geofig_engine/serialize/dashboard.py` (new)

- Define schema constants:

  ```python
  DASHBOARD_SCHEMA = "geofig-engine/dashboard"
  DASHBOARD_SCHEMA_VERSION = 1
  ```

- Implement:

  ```python
  specs_to_dashboard_dict(specs, *, legend=True, strict=True) -> dict
  specs_to_dashboard_json(specs, *, legend=True, strict=True) -> str
  validate_dashboard_payload(payload) -> None
  ```

- Emit a top-level envelope:

  ```json
  {
    "schema": "geofig-engine/dashboard",
    "schema_version": 1,
    "engine_version": "0.5.0",
    "revision": 12,
    "figures": []
  }
  ```

- Each figure carries:
  - `figure_id` — deterministic from template name, context, and position;
  - `template_hash` — canonical hash of the structural definition only;
  - `definition` — layers, geom/stat metadata, coord, facet, settings, layout,
    and column references; no inline data values;
  - `data` — columnar `{columns: {name: [...]}, index: [...]}` payload;
  - `legend` — serialized legend groups/entries when `legend=True`.

- Represent `visual_mapping` series as column references
  (`{"$column": "x"}`) or constants; do not duplicate the same values in both
  `data` and `visual_mapping`. Fall back to inline series only when a series has
  no usable column name.

- Normalize for strict browser JSON:
  - `NaN` / `NaT` / `Infinity` → `null` by default; with `strict=True` either
    raise on unrepresentable non-finite values or document the normalization
    explicitly in the ticket implementation;
  - datetimes / `Timestamp` → ISO-8601 strings;
  - numpy scalars → Python scalars;
  - tuples → arrays on output; restore tuples only in the Python round-trip
    serializer, not here;
  - callables rejected with a message naming the unsupported seam/source.

### `src/geofig_engine/serialize/_legend.py` (new)

- Add renderer-agnostic legend extraction using only `pandas` plus existing
  marker/palette constants.
- Do not import `matplotlib.pyplot` or any renderer module from the dashboard
  serialization path.
- Return plain `LegendEntry` / `LegendGroup`-shaped dataclasses or dicts suitable
  for `dataclasses.asdict`.
- Keep `MatplotlibRenderer` and its legend API unchanged in this phase.

### `src/geofig_engine/serialize/__init__.py`

- Export the three dashboard snapshot functions and the validator.
- Keep all existing exports unchanged.

### `src/geofig_engine/__init__.py`

- Export `specs_to_dashboard_dict` and `specs_to_dashboard_json` at package root.

### Tests

- `tests/test_serialize_dashboard.py` (new)
  - Full snapshot for every seeded template key, including `piper` / `stiff`
    children and facet/iterator cases.
  - Determinism: same specs → byte-identical JSON.
  - Template hash unchanged for data-only changes; changed for layer/settings/
    coord changes.
  - No inline duplication of column values in a definition.
  - Strict JSON cases: NaN, NaT, datetime, numpy scalar, tuple, callable.
  - Legend payload matches `LegendAccumulator`-derived groups for representative
    mappings.
- `tests/test_serialize.py`
  - Add a guard that existing round-trip functions still pass unchanged.

## Acceptance criteria

- [ ] Existing `figure_spec_to_dict` / `spec_to_json` behavior is unchanged
- [ ] Dashboard snapshots are valid strict JSON with schema/version/revision
- [ ] Template definitions contain no inline data values; data is columnar
- [ ] Stable `figure_id`, layer IDs, and `template_hash` are present and
      deterministic
- [ ] Legend data is included and derived without pyplot
- [ ] Non-JSON-native values are normalized or rejected with clear errors
- [ ] No upstream imports, no new required dependency, no renderer behavior
      change
- [ ] Committed as a single commit
      (`geofig-engine: dashboard wire schema → v0.5.0`)

## Files

- `src/geofig_engine/serialize/dashboard.py` (new)
- `src/geofig_engine/serialize/_legend.py` (new)
- `src/geofig_engine/serialize/__init__.py`
- `src/geofig_engine/__init__.py`
- `tests/test_serialize_dashboard.py` (new), `tests/test_serialize.py`
