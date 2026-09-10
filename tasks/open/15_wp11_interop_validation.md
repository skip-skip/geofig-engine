# Phase 15: Interop validation (standalone + upstream smoke)

**Status**: open
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_wp4_render_template`, `15_wp5_legacy_shims`,
`15_wp6_base_templates`, `15_wp7_dendrogram`, `15_wp8_coordgeo_geoms`,
`15_wp9_site_map`, `15_wp10_particle_overlay`

## Description

Prove the interop contract holds end to end and the full suite stays green.
This ticket adds the cross-cutting validation tests only — the shared-contract
pieces behind them land in the WP tickets above.

Three validation axes (Dependency rules in `ARCHITECTURE.md` must hold —
`geofig_engine` itself never imports `geodata`/`geochemmodel`):

1. **Standalone** — raw `pandas.DataFrame` + `render_template` with no other
   package (basic analysis path from `## Example Flow`).
2. **Protocol conformance** — a minimal duck-typed provider (third-party,
   no subclassing) renders through `FigureGenerator`/`render_template`.
3. **Upstream smoke** — `geochemmodel.ModelResult.render()` drives the new
   API via its **lazy** import; `AgglomerativeClusterModel` on a tiny frame →
   `result.render()` → `list[Figure]`; `ParticleImageModel` result →
   `particle_overlay`. Use `pytest.importorskip("geochemmodel")` so the engine
   suite never requires it (mirrors the cv2 skip pattern).

## Changes

### `tests/test_interop.py` (new)

- `test_standalone_bivariate` — `render_template(df, template="bivariate", mapping=...)`
  returns `list[Figure]` with no geodata/geochemmodel import.
- `test_raw_dataframe_wrapping` — NaN rows / non-str columns don't break the
  wrap (DataFrameProvider).
- `test_duck_provider_renders` — minimal 5-member Protocol implementor passes
  through and renders.
- `test_upstream_lazy_render` — importorskip geochemmodel; tiny cluster fit →
  `result.render(data=...)` returns figures for `bivariate` and `dendrogram`.
- `test_no_upstream_import` — assert `geofig_engine` modules import without
  `geodata`/`geochemmodel` in `sys.modules` (fresh import under a guard).
- `test_legacy_path_warns` — `render_template_legacy` returns the tuple and
  warns (bridge to `15_wp5`).

### `README.md`

- Add a short "Standalone" snippet (raw DataFrame → `render_template`).

## Acceptance criteria

- [ ] Standalone test passes without any upstream package installed
- [ ] Duck-typed provider renders; generator never instantiates `Dataset`
- [ ] Upstream test runs and passes when `geochemmodel` is importable; skips
      cleanly otherwise (counted skip, not failure)
- [ ] `assert "geodata" not in sys.modules`-style guard passes on a fresh import
- [ ] Full suite: **1039 baseline + all new WP tests** pass with no regressions
- [ ] `README.md` standalone snippet is accurate and runnable
- [ ] Committed as a single commit (`geofig-engine: interop validation → v0.2.0`); full suite green

## Files

- `tests/test_interop.py` (new)
- `README.md`