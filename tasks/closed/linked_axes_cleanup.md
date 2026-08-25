# Linked-axes cleanup and ROADMAP closure

**Status**: done
**Phase**: 14.5
**Dependencies**: `piper_linked_rewrite`

## Description

Final pass for Phase 14.5: remove the superseded renderer special cases once parity is confirmed, tidy serialization/tests, mark the phase complete in ROADMAP.

## Files modified

- `src/geofig_engine/renderers/matplotlib/renderer.py` — deleted `_render_piper()`, `_draw_ternary_frame`, `_draw_ternary_edge_labels`, `_draw_diamond_frame`, PiperCoord isinstance dispatch in `render()` and `supports()`, unused `Polygon`/`GridSpec` imports
- `ROADMAP.md` — Phase 14.5 marked complete with summary + 818 test count

## Acceptance criteria

- [x] No dead Piper-specific code paths remain in the renderer
- [x] Full test suite passes (no skips introduced by cleanup)
- [x] Deprecation policy for PiperCoord executed consistently (class, serializer, docs)
- [x] ROADMAP Phase 14.5 marked complete with accurate description of what shipped
- [x] Stiff/Durov noted as follow-up beneficiaries in ROADMAP
