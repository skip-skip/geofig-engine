# Linked-axes cleanup and ROADMAP closure

**Status**: open
**Phase**: 14.5
**Dependencies**: `piper_linked_rewrite`

## Description

Final pass for Phase 14.5: remove the superseded renderer special cases once parity is confirmed, tidy serialization/tests, mark the phase complete in ROADMAP.

## Files to modify

- `src/geofig_engine/renderers/matplotlib/renderer.py` — delete `_render_piper()` (lines 291–336), PiperCoord isinstance dispatch (line 103), `"piper_layout"`/`"piper_overlay"` setting branches, and `_draw_ternary_frame`/`_draw_ternary_edge_labels`/`_draw_diamond_frame` helpers (lines 338–~450)
- `src/geofig_engine/core/coord.py` — decide final disposition of deprecated `PiperCoord` (keep with warning or remove; serializers updated to match)
- `src/geofig_engine/serialize/converters.py` — drop PiperCoord branch if removed
- `ROADMAP.md` — mark Phase 14.5 ✅ with summary + test count

## Acceptance criteria

- [ ] No dead Piper-specific code paths remain in the renderer
- [ ] Full test suite passes (no skips introduced by cleanup)
- [ ] Deprecation policy for PiperCoord executed consistently (class, serializer, docs)
- [ ] ROADMAP Phase 14.5 marked complete with accurate description of what shipped
- [ ] Stiff/Durov noted as follow-up beneficiaries in ROADMAP
