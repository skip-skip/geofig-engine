# API Reference — Serialization

`geofig_engine.serialize` provides JSON round-trips for fully resolved
[`FigureSpec`](core.md#layers--specs) objects and their component types
(geoms, coords, facets, scales, stats, layer specs). Conversion is recursive —
a `FigureSpec`'s `children`, layers, coord, facet, and `LinkTransform` are all
covered.

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
from geofig_engine.templates import bivariate
from geofig_engine.engine import render_template
from geofig_engine.serialize import spec_to_json, spec_from_json

specs, _, _ = render_template(dataset=df, template=bivariate(mapping={"x": "x", "y": "y"}))
roundtrip = spec_from_json(spec_to_json(specs[0], indent=2))
assert roundtrip == specs[0]
```

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

*Next: [core.md](core.md) · [engine.md](engine.md) · [templates.md](templates.md) · [renderers.md](renderers.md) · [data.md](data.md) · [io.md](io.md)*