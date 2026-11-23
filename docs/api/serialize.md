# API Reference — Serialization

`geofig_engine.serialize` provides JSON round-trips for fully resolved
[`FigureSpec`](core.md#layers--specs) objects and their component types
(geoms, coords, facets, scales, stats, layer specs). Conversion is recursive —
a `FigureSpec`'s `children`, layers, coord, facet, and `LinkTransform` are all
covered. Phase 19 adds a separate [dashboard wire format](#dashboard-wire-format)
for browser snapshots and patches; it does not replace the round-trip API.

```python
from geofig_engine.serialize import (
    geom_from_dict, geom_to_dict,
    coord_from_dict, coord_to_dict,
    facet_from_dict, facet_to_dict,
    scale_from_dict, scale_to_dict,
    stat_from_dict, stat_to_dict,
    layer_spec_from_dict, layer_spec_to_dict,
    figure_spec_from_dict, figure_spec_to_dict,
    spec_from_json, spec_to_json,
)
```

## Contents

- [Component converters](#component-converters)
- [Spec converters](#spec-converters)
- [JSON convenience](#json-convenience)
- [Dashboard wire format](#dashboard-wire-format)
- [Round-trip notes](#round-trip-notes)

---

## Component converters

Each `*_to_dict` returns a JSON-compatible dict; each `*_from_dict` rebuilds
the object from such a dict.

| Function | Signature | Notes |
| --- | --- | --- |
| `geom_to_dict` / `geom_from_dict` | `geom_to_dict(geom: Geom) -> dict` · `geom_from_dict(data: dict) -> Geom` | Dispatch on the geom's `type` (from `Geom.name`). Preserves Abline slope/intercept or two-point form; FunctionLine `func`/`label`; Box/Violin/StepLine params; Point `jitter`/`dodge`; Bar `position`; Polygon edge styling. |
| `coord_to_dict` / `coord_from_dict` | `coord_to_dict(coord: Coord) -> dict` · `coord_from_dict(data: dict) -> Coord` | Reconstructs `cartesian`, `flipped`, `polar`, `fixed`, and `ternary` coords (Ternary keeps `channels`, `handedness`, `labels` where set). |
| `facet_to_dict` / `facet_from_dict` | `facet_to_dict(facet: Facet) -> dict` · `facet_from_dict(data: dict) -> Facet` | Reconstructs `null`, `wrap` (by/ncol/nrow/scales), and `grid` (row/col/scales) facets. |
| `scale_to_dict` / `scale_from_dict` | `scale_to_dict(scale: Scale) -> dict` · `scale_from_dict(data: dict) -> Scale` | Reconstructs `continuous` (trans/domain/range), `ordinal` (palette/domain/range), `constant` (value), `datetime` (format/domain/range), and `normalize` (range_min/range_max) scales. |
| `stat_to_dict` / `stat_from_dict` | `stat_to_dict(stat: Stat) -> dict` · `stat_from_dict(data: dict) -> Stat` | Serializes `{"type": name, "params": params}`. Deserializes `identity`, `bin`, `count`, `smooth`, `sum`, `pie_labels`, `radar`, `ion_fractions`, and `fn` (see [Round-trip notes](#round-trip-notes)). |
| `layer_spec_to_dict` / `layer_spec_from_dict` | `layer_spec_to_dict(layer: LayerSpec) -> dict` · `layer_spec_from_dict(data: dict) -> LayerSpec` | Wraps geom + stat + `visual_mapping` (series → column/constant representation) + optional `data_override`, `zorder`, `xlim`, `ylim`. |

---

## Spec converters

| Function | Signature | Description |
| --- | --- | --- |
| `figure_spec_to_dict` | `figure_spec_to_dict(spec: FigureSpec) -> dict` | Serializes a full `FigureSpec`: `template_name`, `iterator_key`, `coord`, `facet`, `layers`, `settings`, `context`, `mappings`, `data` (DataFrame → column-oriented records + index), `children` (recursive), and `transform` (via `LinkTransform.to_dict`). |
| `figure_spec_from_dict` | `figure_spec_from_dict(data: dict) -> FigureSpec` | Rebuilds a `FigureSpec` via `build_spec` (so it is re-validated) from the dict form. |

---

## JSON convenience

| Function | Signature | Description |
| --- | --- | --- |
| `spec_to_json` | `spec_to_json(spec: FigureSpec, **kwargs) -> str` | `json.dumps(figure_spec_to_dict(spec), **kwargs)` — extra kwargs (e.g. `indent`) pass through to `json.dumps`. |
| `spec_from_json` | `spec_from_json(json_str: str) -> FigureSpec` | `figure_spec_from_dict(json.loads(json_str))`. |

```python
import json
from geofig_engine import FigureGenerator, DataFrameProvider
from geofig_engine.serialize import spec_to_json, spec_from_json
from geofig_engine.templates import bivariate

template = bivariate(mapping={"x": "x", "y": "y"})
specs = FigureGenerator(
    provider=DataFrameProvider(df),
    layers=template.layers,
    coord=template.coord,
    settings={"figsize": (8, 6)},
).build_specs()          # render_template does not return specs; build them here

roundtrip = spec_from_json(spec_to_json(specs[0], indent=2))
assert roundtrip == specs[0]
```

---

## Dashboard wire format

Phase 19 adds a versioned, browser-safe projection for dashboards fed by
`build_template_specs(...)`. It is **parallel to** the Python round-trip
format above, not a replacement for it.

```python
from geofig_engine import (
    specs_to_dashboard_dict,
    specs_to_dashboard_json,
    diff_dashboard_payload,
    apply_dashboard_patch,
    validate_dashboard_patch,
)
from geofig_engine.serialize import DASHBOARD_SCHEMA, DASHBOARD_SCHEMA_VERSION
```

### Snapshot envelope

`specs_to_dashboard_dict(specs, *, legend=True, strict=True) -> dict` and
`specs_to_dashboard_json(specs, *, legend=True, strict=True) -> str` accept the
`list[FigureSpec]` returned by `build_template_specs` and emit a deterministic
envelope:

| Key | Meaning |
| --- | --- |
| `schema` | `DASHBOARD_SCHEMA` — currently `"geofig-engine/dashboard"`. |
| `schema_version` | `DASHBOARD_SCHEMA_VERSION` — currently `1`. |
| `engine_version` | Phase 19 target `"0.5.0"` (the release commit updates `pyproject.toml`). |
| `revision` | Integer derived from the figure payloads; changes when the snapshot content changes. |
| `figures` | One record per spec, in spec order. |

`legend=False` omits the per-figure legend payload. `strict=True` (default)
validates the finished envelope; `json.loads(specs_to_dashboard_json(...))`
equals `specs_to_dashboard_dict(...)`.

### Definition vs columnar data

Each figure record contains `figure_id`, `template_hash`, `definition`, `data`,
`children`, and optional `legend`. The `definition` holds low-frequency
structure — template name, context, layers, coord, facet, settings, layout,
transform, and child definitions — and references values by `{"$column":
name}`. All values live once in the figure's `data` payload:

```json
{"columns": {"x": [1, 2, 3]}, "index": [0, 1, 2]}
```

Named resolved series are added to the column store; only unnamed series fall
back to `{"$inline": [...]}`. Nested `piper` / `stiff` children reuse the
parent column store via `"data_ref": "$parent"`. Definitions never duplicate
data values.

### Stable identities

- `figure_id` deterministically combines template name, position, context, and
  iterator key.
- Each `layer_id` deterministically combines the figure identity, layer index,
  and structural layer definition.
- `template_hash` hashes the structural definition with instance/data identity
  fields stripped, so a data-only edit keeps the same hash while a coord,
  layer, or settings change produces a new one.
- `revision` is derived from the full figure payloads; patches carry both the
  new `revision` and the `base_revision` they were built against.

### Patches

`diff_dashboard_payload(old_payload, new_payload)` returns a patch envelope:
`schema` (`"geofig-engine/dashboard-patch"`), `schema_version` (`1`),
`revision`, `base_revision`, and `operations`. `apply_dashboard_patch(payload,
patch)` returns a **new** payload and never mutates its input;
`validate_dashboard_patch(patch)` validates schema/version, operation names,
required fields, figure IDs, and revision types with `ValueError`s.

| Operation | Effect |
| --- | --- |
| `replace_data` | Replace a figure's complete `columns` / `index`. |
| `append_data` | Append `columns` and their `index` rows to existing data. |
| `replace_definition` | Replace a definition, carrying the new `template_hash` (and children when changed). |
| `update_settings` | Replace settings/layout without touching data or other structure. |
| `remove_figure` | Remove a figure by ID. |

Data-only diffs emit only data operations and leave `template_hash` unchanged;
structural diffs emit `replace_definition`; settings-only diffs emit
`update_settings`. Changes the five operations cannot express (for example an
added figure) use a self-contained `payload` fallback so applying the patch
still reproduces the fresh snapshot exactly. If `base_revision` is present and
differs from the target payload's `revision`, apply rejects the patch as stale
or out-of-order. No transport (WebSocket/SSE/HTTP) is included.

### Strict JSON normalization

- `NaN`, `NaT`, and positive/negative infinity normalize to `null` in both
  strict and non-strict modes.
- datetimes and pandas `Timestamp`s become ISO-8601 strings.
- NumPy scalars become Python scalars; tuples become arrays.
- Callables are rejected with a `TypeError` naming the payload seam and the
  callable source.

`strict=True` additionally validates the envelope and uses `allow_nan=False`,
so emitted snapshots contain no non-finite tokens.

### Boundary with the existing serializer

`spec_to_json` / `spec_from_json` (and `figure_spec_to_dict` /
`figure_spec_from_dict`) remain the **Python round-trip format** with the
semantics described below. The dashboard schema is a display/update projection
only. `MatplotlibRenderer` still consumes `FigureSpec` objects directly; there
is no dashboard-JSON ingestion in v0.5.0.

---

## Round-trip notes

- **`StatFn` degrades to `StatIdentity`** on deserialization: a callable cannot
  be serialized, and the engine transforms data before serializing, so the
  post-engine state is authoritative. `stat_to_dict` still records
  `{"type": "fn", "params": ...}`; `stat_from_dict` returns `StatIdentity()`.
- **Tuple settings restored:** the JSON round-trip coerces length-2 lists back
  to tuples for `xlim`/`ylim`, `figsize`, and secondary-axis `range` keys in
  `settings`, so specs compare equal after round-tripping.
- **Strictnesses:** children recursion is depth-preserving (depth-1 enforced
  by `validate_figure_spec` on rebuild); `GeomAbline` round-trips whichever
  form was declared; `TernaryCoord` labels round-trip only when set.

---

*Next: [core.md](core.md) · [engine.md](engine.md) · [provider.md](provider.md) · [templates.md](templates.md) · [renderers.md](renderers.md) · [data.md](data.md) · [io.md](io.md)*