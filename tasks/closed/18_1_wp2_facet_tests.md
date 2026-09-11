# Phase 18.1: WP2 — Facet behavioral coverage (multi-panel, composition, parity)

**Status**: complete
**Phase**: 18.1
**Version target**: v0.3.1+
**Dependencies**: `18_1_wp1_facet_generator`

## Description

Add the regression coverage that pins the restored contract: facets split
into panels **within** one figure through `render_template`, `facet=`
composes with `iterators=` as one figure per iterator combination each
carrying the full panel grid, and the Phase-15 generator agrees with the
legacy `FigureEngine` on facet output.

## Changes

1. **`tests/test_entry.py`** — extend the WP1-updated
   `test_with_facet_renders_multi_panel_figure`:
   - `len(figures) == 1`; `isinstance(figures[0], matplotlib.figure.Figure)`
   - `len(figures[0].axes) == 2` for a 2-group `FacetWrap(by="group")`
   - panel titles contain `group=A` / `group=B` (via `ax.get_title()`)
2. **`tests/test_declarative_api.py`** — new `TestFacet` class:
   - `test_facet_wrap_single_multi_panel_figure`: `render_template(facet=
     FacetWrap(by="group"))` → 1 figure, 2 axes, per-panel titles
   - `test_facet_grid_single_figure_layout`: `FacetGrid(row=..., col=...)`
     → 1 figure with `nrow × ncol` axes; axes for missing combos
     `not ax.get_visible()`; row/col labels on the leading edge
   - `test_facet_with_iterators_composes`: `facet=FacetWrap(by="group")` +
     one VALUE-mode `DimensionIterator` over a 2-value column →
     `len(figures) == 2`, and **each** figure exposes one axis per facet
     group
   - `test_facet_empty_data_returns_one_figure`: empty frame + `facet=`
     → 1 figure, no `ValueError`
3. **`tests/test_engine_new_api.py`** — parity test
   `test_generator_matches_legacy_facet_behavior`: same data/layers/facet
   through `FigureEngine.build_specs_from_layers` and
   `FigureGenerator.build_specs` → equal spec counts (no iterators: 1 each),
   both `spec.facet.name == "wrap"`, both rendered spec sets produce the
   same number of axes per figure via `MatplotlibRenderer`
4. Leave untouched: `test_renderers.py::TestMatplotlibRendererFacet`
   (direct-spec renderer tests), `test_integration.py::TestFacetIntegration`
   (legacy path), `test_serialize.py` facet round-trips, `test_facet.py`
   (core model)

## Acceptance criteria

- [ ] Every new/updated test above present and passing
- [ ] `ValueError("Facet produced zero panels")` not raised anywhere in the
      new tests (incl. empty data + facet)
- [ ] Generator ↔ legacy parity test passes (spec count and rendered axes
      per figure equal)
- [ ] Existing renderer/legacy/serialization facet tests unchanged and green
- [ ] Full suite green (1387 baseline + new; no warning-policy skips)

## Files

- `tests/test_entry.py`
- `tests/test_declarative_api.py`
- `tests/test_engine_new_api.py`