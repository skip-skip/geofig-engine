# WP-A: AxisFormat model + `parse_axis_settings` (core/axis.py)

**Status**: open
**Phase**: 14.54
**Depends on**: none (first WP)

## Description

Introduce a single, shared, declarative axis-formatting model consumed by the
**unified frame-drawing pipeline**. Both the top-level path and the linked-axes
child-frame path use the exact same functions and the exact same formatting
specification. Formatting is declared under a structured `settings["axis"]`
dict, following the `SecondaryAxis` precedent (frozen dataclass + pure parser +
validation + tuple round-trip serialization).

The model is a **common core + per-coordinate `options` extension**, so each
coordinate type (cartesian, ternary, polar) can carry unique declarations while
sharing the common axis fields. It also carries **appearance-preserving style
knobs** whose defaults reproduce the current native matplotlib look, so
switching top-level cartesian/ternary/polar onto the unified custom frame does
not visibly regress existing templates.

## Changes

### `src/geofig_engine/core/axis.py` (new)

**`AxisFormat`** — frozen dataclass, matplotlib-free.

Common fields (consumed by both paths):
- `title: str = ""`
- `xlabel: str | None = None`
- `ylabel: str | None = None`
- `limits: tuple[tuple[float, float], tuple[float, float]] | None = None` — `(xlim, ylim)`
- `grid: bool | None = None`
- `grid_step: float | None = None`
- `tick_step: float | None = None`
- `label_policy: str = "upright"` — `"upright" | "parallel"`
- `xscale: str | None = None` — e.g. `"linear"`, `"log"`
- `yscale: str | None = None`
- `time_format: str | None = None`
- `tick_format: str = ":g"` — format-spec applied to numeric tick labels (default preserves current `f"{x:g}"` output)

Appearance-preserving style knobs (defaults match current native/custom output):
- `tick_fontsize: float = 5` (child custom frames) — overridable per coord via options for native-look top-level
- `label_fontsize: float = 7`
- `title_fontsize: float = 7`
- `grid_style: dict[str, Any] = field(default_factory=lambda: {"color": "gray", "linewidth": 0.3, "linestyle": ":"})`
- `frame_linewidth: float = 1.0`
- `label_offset: float | None = None` — tick-label offset from the edge (default derived from limits size)

Per-coordinate extension:
- `options: dict[str, Any] = field(default_factory=dict)` — e.g. polar `hide_spine`, `hide_angular_ticks`, `hide_angular_labels`, `hide_radial_ticks`, `hide_radial_labels`, `polar_tick_labels`; cartesian/ternary extras.

`__post_init__` enforces shape (pairs of real numbers for `limits`, positive
`grid_step`/`tick_step`, valid `label_policy`, valid `tick_format`), raising
`ValueError` like `SecondaryAxis`.

**`parse_axis_settings(settings, coord) -> AxisFormat`** — pure reader:
- If `settings.get("axis")` is a mapping, build from it (validated).
- Otherwise fall back to the current legacy flat keys so existing templates and
  tests keep working: `title`, `xlabel`, `ylabel`, `xlim`, `ylim`, `grid`,
  `grid_step`, `tick_step`, `label_policy`, `xscale`, `yscale`, `time_format`,
  and polar `hide_spine`/`hide_angular_ticks`/`hide_angular_labels`/
  `hide_radial_labels`/`hide_radial_ticks`/`polar_tick_labels` (mapped into
  `options`).
- `coord` provides context for coord-specific defaults/validation, but the
  common parse stays coord-agnostic.

Keep the module free of matplotlib imports so it can be unit-tested directly
and reused by the frame renderer (WP-B, WP-C) and the unified single path
(WP-D).

## Acceptance criteria

- [ ] `parse_axis_settings({}, coord)` returns a valid `AxisFormat` with defaults (no crash)
- [ ] Explicit `settings["axis"]` and the equivalent legacy flat keys produce **equal** `AxisFormat` instances
- [ ] Polar-specific legacy keys map into `AxisFormat.options`
- [ ] Malformed `limits` / negative `tick_step` / bad `label_policy` raise `ValueError`
- [ ] `tick_format` defaults to `":g"`; appearance knobs have the native-match defaults
- [ ] No matplotlib imports in `core/axis.py`

## Files

- `src/geofig_engine/core/axis.py` (new)
- `tests/test_axis_format.py` (new, model/parse/validation/parity)
