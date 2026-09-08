# Phase 14.59: Tests for the stiff-as-cartesian migration

**Status**: open
**Phase**: 14.59
**Dependencies**: `14_59_wp4_stiff_template_cartesian`, `14_59_wp5_remove_stiff_piper_coords`, `14_59_wp3_geom_polygon`

## Description

Update and extend the test suite for the migration. The legacy `tests/test_stiff.py`
covers `StiffCoord` (model, serialization) and the normalized polygon spec; both
must be rewritten to assert the new cartesian formulation. Deprecated-coord tests
in `tests/test_piper.py` are removed. `CoordFlipped` / `CoordFixed` tests are
untouched.

## Changes

### `tests/test_stiff.py`

- Rewrite `TestStiffCoord` (coord-model tests) → assert the spec-level contract:
  - `coord.name == "cartesian"`
  - symmetric `xlim` (equal magnitudes, opposite signs)
  - `tick_step == tick_max / 2`, `abs_ticks` set, `xlabel == "meq/L"`
  - y `tick_labels` (cations) + `secondary_y.tick_labels` (anions) present
- Rewrite `TestPlotStiff`:
  - `plot_stiff(...)` returns a `FigureSpec` with `template_name` unchanged
  - polygon trace: raw signed meq/L vertices (left negative, right positive,
    y trace 2→1→0→0→1→2→2), 7 points
  - `figsize` honored; `title` lands in `settings["title"]`
  - serialization round-trip preserves the polygon data + settings
  - render smoke test: one axis, filled polygon present, ion labels present
- `_nice_tick_max` tests retained unchanged.

### `tests/test_piper.py`

- Delete `TestPiperCoord` (lines covering the deprecated class); keep all
  current children-based spec/render/serialization tests. Remove the now-unused
  `PiperCoord` import (keep `CoordCartesian` / `TernaryCoord`).

### `tests/test_polygon.py` (new, WP3 coverage)

- `GeomPolygon` model: required/optional channels, default outline params,
  invalid `edgestyle` rejected.
- Render: closed filled polygon via `ax.fill` (auto-close verified), fill
  `color`/`alpha` honored, outline `edgecolor` / `edgealpha` / `edgewidth` /
  `edgestyle` applied.
- Serialization round-trip preserves non-default outline params.
- `GeomArea` renders the below-a-line `fill_between` path (regression: no
  change, no `ax.fill`).

## Acceptance criteria

- [ ] `tests/test_stiff.py` asserts cartesian coord, symmetric limits, abs/named ticks
- [ ] Polygon geometry asserted in raw meq/L coordinates
- [ ] `plot_stiff` render smoke test passes (1 axis, filled polygon, labels)
- [ ] `TestPiperCoord` removed; no dangling imports
- [ ] No test references `StiffCoord` / `PiperCoord`
- [ ] `hydro_demo.py` produces all 7 figures without error
- [ ] Full suite passes (with WP1/WP2/WP3 additions)

## Files

- `tests/test_stiff.py`
- `tests/test_piper.py`
- `tests/test_polygon.py` (new)