# Phase 18.1: Facet / iterator consistency fix (bug-fix mini-phase)

**Status**: complete
**Phase**: 18.1
**Version target**: v0.3.1 (finalized at epic review)
**Dependencies**: none (phase overview)

## Description

Facets are documented to split the data into panels within a **single figure**
(core/facet.py docstring; renderer `_facet_panels` / `_render_faceted`), while
iterators produce **one independent figure per combination**. The Phase-15
`FigureGenerator.build_specs` violates that contract: `_facet_groups`
pre-splits the provider by a cartesian product of facet column values, so
`render_template(..., facet=...)` emits **one single-panel figure per facet
group** and raises `ValueError: Facet produced zero panels` for empty
combinations — diverging from the legacy `FigureEngine.build_specs_from_layers`
path, which stamps the full frame + facet object on each spec and lets the
renderer draw genuine multi-panel figures.

This mini-phase restores consistency: the generator expands **iterators
only**; facets are applied panel-wise by the renderer on the full
iterator-context frame. `facet=` + `iterators=` compose as N independent
figures, each containing the full facet panel grid — matching legacy
semantics (`tests/test_integration.py::TestFacetIntegration` already asserts
the legacy behavior: `len(fig.axes) == 2` for a 2-group facet).

**Root cause trace (verified against the working tree):**

- `engine/generator.py:468-484` — `_facet_groups()`: cartesian product of
  `provider.unique_values(by-col)` → one `provider.subset` per combo
- `engine/generator.py:490-526` — `build_specs()`: one FigureSpec per
  (facet-combo × iterator-combo); `data` restricted to a single group;
  `context` / `iterator_key` include facet keys
- `renderers/matplotlib/renderer.py:108-117` — `_facet_panels()`: groupby on
  the spec's `data` (observed groups only) → with a single-group spec this
  yields one panel per figure
- `renderers/matplotlib/renderer.py:1337-1415` — `_render_faceted()`: draws
  the panel grid within one figure
- `renderers/matplotlib/renderer.py:1344-1345` — `ValueError("Facet produced
  zero panels")` fires on the pre-split empty cartesian combos

## Phase-level acceptance criteria

- [ ] `render_template(..., facet=FacetWrap(by=...))` returns **one** figure
      whose panel count equals the number of observed facet groups
- [ ] `FacetGrid` renders within one figure; missing row×col combos leave
      hidden axes (unchanged renderer behavior, now reachable from
      `render_template`)
- [ ] `facet=` + `iterators=` composes as N figures, each containing the full
      panel grid (parity with legacy `FigureEngine`)
- [ ] No `ValueError("Facet produced zero panels")` from the generator path;
      empty dataset + facet behaves like empty dataset without facet
- [ ] Spec `context` / `iterator_key` contain only iterator keys (facet keys
      removed — parity with legacy `merged_context`); savedir filenames use
      iterator keys only
- [ ] Renderer renderers (`test_renderers.py`), legacy `FigureEngine`
      (`test_engine_new_api.py` / `test_integration.py`), and facet
      serialization (`test_serialize.py`) untouched
- [ ] Full suite green (baseline 1387 passed / 6 skipped, 0 warning skips)
      after every WP
- [ ] Commits labeled `geofig-engine: <scope> → v0.3.1` (target finalized at
      epic review)

## Ticket map

| Ticket file | Scope | Depends |
| --- | --- | --- |
| `18_1_wp1_facet_generator.md` | generator + renderer edge + stale-test updates | epic (context) |
| `18_1_wp2_facet_tests.md` | new behavioral coverage (multi-panel, grid, composition, empty, parity) | `18_1_wp1_facet_generator` |
| `18_1_wp3_facet_docs_roadmap.md` | `docs/api/engine.md` + ROADMAP Phase 18.1 entry + Phase 18 statuses | `18_1_wp2_facet_tests` |

## Files

- `src/geofig_engine/engine/generator.py`
- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `tests/test_entry.py`, `tests/test_engine_new_api.py`,
  `tests/test_declarative_api.py`
- `docs/api/engine.md`, `ROADMAP.md`
- this ticket list (`tasks/open/18_1_*.md`)