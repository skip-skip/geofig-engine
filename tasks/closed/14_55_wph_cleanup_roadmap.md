# WP-H: Cleanup + ROADMAP + close task files (Phase 14.55)

**Status**: closed
**Phase**: 14.55
**Dependencies**: all other 14.55 WPs (A–G)

## Description

Final pass for Phase 14.55: verify no stale hardcoded ternary-arrow code
remains, document the phase in `ROADMAP.md`, and move the WP-A..H task files
from `tasks/open/` to `tasks/closed/` once their acceptance criteria are met.

## Changes

### Consistency / grep check

- No reference to the old fused ternary arrow closure / `reverse` arrowstyle
  logic remains outside `_draw_axis_arrow`.
- `axis.show_arrows()` is the single source of truth for arrow presence across
  cartesian (x/y + secondary), ternary, and polar drawers.
- Every framed drawer honors the `axis_arrows` flag; default-off preserves
  output unless a template opts in (see WP-F).

### `ROADMAP.md`

Add a `## ✅ Phase 14.55 — General axis-direction arrows` section (before/after
the 14.54 entry as appropriate) documenting:
- New common `AxisFormat` field `axis_arrows` (flat top-level key, default off)
  parsed by `parse_axis_settings`, with `show_arrows()` accessor and bool
  validation.
- Shared `_draw_axis_arrow(ax, matrix, start, end, local_vec, ...)` helper —
  arrows parallel to each axis, **pointing toward increasing (ascending)
  values** regardless of declared/descending limit order (the "axis values must
  be sorted" rule). Optional label rotates via `label_rotation`.
- Cartesian framed: x + y (+ secondary_x/secondary_y when declared) arrows.
- Ternary: ion edge labels **decoupled** from arrows; arrows now opt-in via
  `axis_arrows` instead of hardcoded / handedness-driven.
- Polar: radial arrow pointing outward for increasing `r`.
- Templates (piper/hydro) opt in to preserve ternary arrows.
- Note the default-off behavior: a ternary without `axis_arrows` loses its
  (formerly implicit) arrows; cartesian/polar output is unchanged by default.

### Task files

- Move WP-A..H from `tasks/open/` to `tasks/closed/`, marking each
  `**Status**: closed`.

## Acceptance criteria

- [x] Grep confirms no hardcoded ternary arrow logic remains
- [x] `ROADMAP.md` has the Phase 14.55 entry (model, helper, per-coord arrows, decoupling, opt-in templates, default-off note)
- [x] All 14.55 task files moved to `tasks/closed/` and marked closed
- [x] Full suite (incl. WP-G additions) passes; example outputs for opted-in templates (piper/hydro) verified

## Files

- `ROADMAP.md`
- `tasks/closed/14_55_*.md` (moved from `tasks/open/`)
