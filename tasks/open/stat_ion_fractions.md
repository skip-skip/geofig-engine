# StatIonFractions stats transform

**Status**: open
**Phase**: 14.5
**Dependencies**: (none)

## Description

Chemistry-to-geometry stat for Piper-style diagrams (ROADMAP Phase 14.5). Consumes meq/L ion columns, performs concentration addition (Na+K, HCO3+CO3 grouping) and percent normalization, and emits fixed-slot fraction columns plus derived diamond coordinates. Replaces the coordinate math currently embedded in `templates/piper.py` (`_cat_fracs`/`_ternary_x`/`_ternary_y`/`_diamond_xy`, lines 16–37).

Design decisions locked during planning:
- Operates on **meq/L inputs only** — unit conversion lives upstream (see `meq_pipeline_step`)
- Fixed-slot output naming (`cation_f0/f1/f2`, `anion_f0/f1/f2`, `diamond_x/y`) avoids identifier problems with names like "Na+K"
- One configured instance is shared by all piper layers; each layer's mapping references the slots it needs; resolution flows through the existing stat_data routing in `engine/generator.py` (StatBin/StatRadar precedent)

## Files to modify

- `src/geofig_engine/core/stat.py` — add `StatIonFractions(cations: tuple[str,str,str], anions: tuple[str,str,str])` implementing `compute(data) -> DataFrame`
- `src/geofig_engine/engine/generator.py` — verify (extend if needed) that multi-output stat columns resolve into visual mappings for all consumers of one shared stat instance
- `tests/test_stat_ion_fractions.py` (new)

## Acceptance criteria

- [ ] Emits `cation_f0/f1/f2`, `anion_f0/f1/f2` normalized per sample from meq/L inputs
- [ ] Emits `diamond_x/diamond_y` matching current `_diamond_xy()` math within float tolerance
- [ ] Zero-total rows handled deterministically (NaN policy chosen and tested, mirroring current `.fillna(0)`/nan_to_num behavior)
- [ ] Pure function: no state, same input → same output
- [ ] Hand-computed chemistry values verified in unit tests
- [ ] Mapping strings referencing stat outputs resolve via generator stat_data routing for a spec with three layers sharing one instance
