# WP1: Fluent orderable LinkTransform

**Status**: open
**Phase**: 14.52
**Depends on**: none (first WP)

## Description

Rewrite `LinkTransform` from a frozen dataclass with `(translate, rotate, scale)` fields into a **fluent, orderable builder** where each operation is applied to points in left-to-right call order:

```python
LinkTransform().rotate(45.0).scale(sx, sy).translate(0.5, 0.0)
```

Composition convention (pinned by tests): `matrix()` is built by left-multiplying each op's matrix in call order, so the **first-called op transforms points first**. For the classic diamond this reproduces the historical `M = T · S · R` exactly (points: rotate → scale → translate).

## Changes

### `src/geofig_engine/core/link.py` — rewrite `LinkTransform`

Replace the `(translate, rotate, scale)` fields with an **ordered list of operations**. Each op is a `(kind, params)` pair, e.g. `("rotate", 45.0)`, `("scale", (sx, sy))`, `("translate", (tx, ty))`. Keep it immutable — each fluent method returns a **new instance** (receiver unchanged).

API surface:
- `.rotate(deg)`, `.scale(sx, sy)`, `.translate(tx, ty)` — return a new `LinkTransform` with the op appended
- `matrix()` — 3×3 homogeneous, `M = op_n @ ... @ op_1` (first-called op rightmost = applied first to points)
- `transform_point(xy)`, `transform_points(pts)`, `transform_direction(vec)` — unchanged (derive from `matrix()`)
- `to_dict()` / `from_dict()` — serialize as ordered ops, e.g. `{"operations": [["rotate", 45.0], ["scale", [sx, sy]], ["translate", [tx, ty]]]}`
- `label_rotation(...)` (module-level) — unchanged
- `__repr__`, `__eq__` — compare the ops list
- Expose `.ops` (the ordered operation list) for introspection/tests

**Remove** the old constructor form `LinkTransform(translate=..., rotate=..., scale=...)` entirely (full fluent-only rewrite). Remove the frozen-field behavior; the class stays immutable via op-list + new-instance methods.

Update the module docstring (lines 1-24) and `test_links.py` docstring (lines 1-9) to describe fluent call-order semantics instead of `translate/rotate/scale` field ordering.

### `src/geofig_engine/core/spec.py`

- `build_spec()` signature keeps `transform: LinkTransform | None` — no structural change; `LinkTransform() == LinkTransform()` identity via empty ops still valid as default
- `validate_figure_spec()` transform type check (line 118) unchanged

## Acceptance criteria

- [ ] `LinkTransform().rotate(45).scale(sx, sy).translate(tx, ty).matrix() == T·S·R` (classic diamond exactly)
- [ ] First-called op transforms points first (call-order semantics)
- [ ] Fluent methods return new instances; receiver unchanged
- [ ] No `LinkTransform(translate=, rotate=, scale=)` constructor remains anywhere in src
- [ ] `.ops` exposes the ordered operation list
- [ ] `to_dict()`/`from_dict()` round-trip ordered ops
- [ ] `label_rotation(...)`, `transform_point(s)`, `transform_direction` still work
- [ ] All call sites in `piper.py`, `debug_piper_axes.py`, serializers, and tests updated (other WPs)

## Files

- `src/geofig_engine/core/link.py`
- `src/geofig_engine/core/spec.py` (only if needed for validation)
