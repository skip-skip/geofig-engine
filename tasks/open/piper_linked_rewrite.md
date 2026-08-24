# Piper re-expression as declarative linked-axes spec

**Status**: open
**Phase**: 14.5
**Dependencies**: `link_model`, `ternary_coord`, `stat_ion_fractions`, `meq_pipeline_step`, `linked_axes_renderer`

## Description

Rewrite the Piper diagram (ROADMAP Phase 14.5 proof of concept) from renderer-hardcoded GridSpec + template-side math into a pure declarative spec:

- **Main axis**: cartesian square with a root transform — rotate 45° then squash y (~0.5) declared as `M_main`; no dedicated DiamondCoord class
- **Two links**: cation triangle (`TernaryCoord` left-handed, world-unit translate lower-left) and anion triangle (`TernaryCoord` right-handed, translate lower-right)
- **Stats**: one shared `StatIonFractions` instance attached to all three layers; layers reference fixed-slot columns; optional `unit_convert=True` sugar wraps input through the meq/L PipelineStep
- Template math helpers (`_cat_fracs`, `_ternary_x/y`, `_diamond_xy`) and the eager Series-injection mapping plumbing are deleted; `piper_overlay_diamond()` becomes an ordinary layer append

Old `PiperCoord` deprecated after visual parity is confirmed.

## Files to modify

- `src/geofig_engine/templates/piper.py` — full rewrite per above
- `src/geofig_engine/templates/__init__.py` — exports unchanged names
- `src/geofig_engine/core/coord.py` — deprecation notice on `PiperCoord`
- `tests/test_piper.py` — update expectations to linked-axes spec
- parity harness script/test comparing rendered point extraction old vs new

## Acceptance criteria

- [ ] `build_piper_specs()` returns FigureSpec with root-transform main axis + two `AxisLink`s; no renderer knowledge in template
- [ ] Diamond coordinates derive from shared stat output; triangles from TernaryCoord fractions
- [ ] Visual parity: extracted point positions match current implementation within tolerance
- [ ] Frames/tick labels follow Piper conventions via frame providers (upright numerals, parallel edge labels)
- [ ] `piper_overlay_diamond()` works as plain layer routing
- [ ] Serialization round-trips a full piper spec including links
- [ ] `PiperCoord` still importable but marked deprecated; `"piper_layout"`/`"piper_overlay"` setting branches unused by new path
