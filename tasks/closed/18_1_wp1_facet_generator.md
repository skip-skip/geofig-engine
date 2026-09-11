# Phase 18.1: WP1 — Facet-agnostic generator + renderer empty-frame guard

**Status**: complete
**Phase**: 18.1
**Version target**: v0.3.1+
**Dependencies**: `18_1_epic` (phase context)

## Description

Make `FigureGenerator.build_specs` facet-agnostic so facets are applied
panel-wise by the renderer (single multi-panel figure) instead of being
pre-split into one spec per group. Also guard the renderer against the
empty-frame edge so the "Facet produced zero panels" error can no longer
surface from the generator path.

## Changes

1. **`engine/generator.py` — `build_specs()`** (lines 490-526): stop
   iterating `_facet_groups()`. Iterate `self.provider.expand(self.iterators
   or [])` once per the whole provider, and for each `(frame, iter_ctx)` emit
   exactly one `FigureSpec` with:
   - `data=frame` — the full iterator-context frame (all facet groups'
     rows present; the renderer's `_facet_panels` splits it into panels)
   - `context={**iter_ctx}` — **no facet keys** (parity with legacy
     `merged_context` at `build_specs_from_layers`)
   - `iterator_key=tuple(sorted(iter_ctx))` — facet keys removed from
     filenames (matches legacy `result.iterator_key`)
   - `facet=self.facet` — unchanged, stamped on every spec
   - settings resolution, `resolve_layer_sources`, `_check_required_channels`
     unchanged (stats now compute over the full iterator-context frame —
     the same as the legacy path; document this in the docstring)
2. **`engine/generator.py` — remove `_facet_groups()`** (lines 468-484) and
   the now-unused `from itertools import product` import (line 11). Update
   the `build_specs` docstring resolution order to: expand
   (`provider.expand`) → resolve channel selectors (`provider.resolve`) +
   scales → package into validated specs (facets are stamped, not split).
3. **`renderers/matplotlib/renderer.py` — `_facet_panels()`** (line 108):
   after the `FacetNull` guard, return `[(data, {})]` when `data.empty`
   (a single empty panel — consistent with the no-facet empty-dataset
   behavior of one figure). Keep the `ValueError("Facet produced zero
   panels")` raise at `_render_faceted` (lines 1344-1345) as a defensive
   invariant — it becomes unreachable from `render_template` after this WP.
4. **`engine/api.py` — `render_template` docstring** (line 226): rewrite the
   `facet` parameter description from "one-spec-per-group splitting" to
   panel-splitting-within-one-figure semantics (iterator figures × facet
   panels).
5. **Stale tests updated to the new contract** (so WP1 leaves the suite
   green; new coverage lands in WP2):
   - `tests/test_entry.py::TestRenderTemplate::test_with_facet_splits_figures`
     (line 123) → `test_with_facet_renders_multi_panel_figure`: exactly one
     figure with one panel per facet group; savedir contains only the single
     figure PNG + `legend.png`
   - `tests/test_engine_new_api.py::test_expansion_uses_provider_expand_and_subset`
     (line ~336): assert `subset` is **not** called and exactly one spec
   - `tests/test_engine_new_api.py::test_facet_splitting_one_spec_per_group`
     (line 359) → `test_facet_does_not_split_specs`: one spec, `data`
     contains all groups, `context`/`iterator_key` contain no `group` key,
     `spec.facet.name == "wrap"`
   - `tests/test_declarative_api.py::TestSavedir::test_savedir_naming_with_facet_and_legend`
     (line 222): expected PNGs become `["001.png", "legend.png"]`

## Acceptance criteria

- [ ] `build_specs()` emits one spec per iterator-expansion result, never per
      facet group; facet/iterator count no longer multiplies specs
- [ ] `_facet_groups()` and the `itertools.product` import removed; no other
      callers of `_facet_groups` remain (grep-verified)
- [ ] Spec `context` and `iterator_key` contain zero facet keys; `data` is
      the full iterator-context frame; `facet=self.facet` on every spec
- [ ] `_facet_panels` returns a single `(data, {})` panel for an empty frame;
      no `ValueError` from `render_template(facet=...)` on empty data
- [ ] `api.py` / `build_specs` docstrings describe panel semantics, not
      per-spec splitting
- [ ] Full suite green (1387 passed / 6 skipped baseline; stale tests updated
      in this WP; new coverage deferred to WP2)

## Files

- `src/geofig_engine/engine/generator.py`
- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `src/geofig_engine/engine/api.py`
- `tests/test_entry.py`, `tests/test_engine_new_api.py`,
  `tests/test_declarative_api.py`