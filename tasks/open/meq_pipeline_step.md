# mg/L → meq/L preprocessing PipelineStep

**Status**: open
**Phase**: 14.5
**Dependencies**: (none)

## Description

Upstream unit-conversion step for Piper-style inputs (ROADMAP Phase 14.5). Applies the existing ion weight/charge tables from `geofig_engine.io` to convert configured mg/L columns to meq/L, packaged as a Phase 17 `PipelineStep` so it composes with the preprocessing pipeline.

Keeps chemistry tables out of `core.stat` — `StatIonFractions` receives meq/L columns and stays pure math, preserving the Data → Spec layering.

## Files to modify

- `src/geofig_engine/io/preprocess.py` — add a meq/L conversion function + factory returning a `PipelineStep(name="meq_conversion", func=..., kwargs=...)`
- `src/geofig_engine/io/__init__.py` — export if public API
- `tests/test_io.py` — extend

## Acceptance criteria

- [ ] Converts mg/L → meq/L for configured analyte columns using io charge/weight tables (valence-aware: Ca²⁺ ×2, etc.)
- [ ] Returns/registers as a `PipelineStep`; runs correctly inside the existing `Pipeline`
- [ ] Non-listed columns pass through unchanged
- [ ] Idempotence documented (re-applying raises or is prevented — pick one, test it)
- [ ] Tests cover known conversion values and pass-through behavior
