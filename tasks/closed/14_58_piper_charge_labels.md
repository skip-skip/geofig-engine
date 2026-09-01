# Phase 14.58: Charge-bearing ion labels for the Piper diagram

**Status**: complete
**Phase**: 14.58
**Dependencies**: `14_57` (label/tick rotation policies), `14_56` (font-size knobs)

## Description

Add chemical sub/superscripts (charge notation) to the Piper diagram ion labels
using matplotlib mathtext, while keeping the underlying data column names
unchanged. Also update the three textual labels the user asked for: the HCO3
triangle vertex, and the diamond's anion/cation axis titles.

Requested label changes:
- Show charge superscripts on the ternary ion names.
- HCO3 axis vertex → `HCO3- + CO3--`.
- Diamond anions title (was "Anions (%)") → `SO4-- + Cl-`.
- Diamond cations title (was "Cations (%)") → `Ca++ + Mg++`.

## Changes

### `src/geofig_engine/core/coord.py`

- Add `labels: tuple[str, str, str] | None = None` to `TernaryCoord`. `None`
  (default) falls back to `channels`, so display text can differ from the data
  column names while data mapping still uses `channels`.
- Validate labels (3 strings) via `_validate_labels`; store them in `params`
  only when explicitly provided (round-trip fidelity).

### `src/geofig_engine/serialize/converters.py`

- Ternary converter round-trips `labels` (omitting it when absent).

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- `_draw_ternary_frame` draws ion edge labels from `coord.labels` when set,
  else `coord.channels`.

### `src/geofig_engine/templates/piper.py`

- Default charge-bearing mathtext labels for standard ions:
  - Cations: `Ca^{++}`, `Mg^{++}`, `(Na+K)^{+}`
  - Anions: `SO_4^{--}`, `Cl^{-}`, compound `HCO_3^{-} + CO_3^{--}` for HCO3
- Diamond axis titles derived from the summed ions:
  - anions: `SO_4^{--} + Cl^{-}` (was "Anions (%)")
  - cations: `Ca^{++} + Mg^{++}` (was "Cations (%)")
- New `labels: dict[str, str] | None` argument to override any label; unknown
  ion columns fall back to their plain channel name.

## Acceptance criteria

- [x] All six ternary ion labels render with charge sub/superscripts
- [x] HCO3 vertex renders as `HCO3- + CO3--` (compound mathtext)
- [x] Diamond axis titles show `SO4-- + Cl-` and `Ca++ + Mg++`
- [x] Display labels are independent of the data columns (channels unchanged)
- [x] Custom per-ion label override via `labels=` arg
- [x] `TernaryCoord.labels` serializes/round-trips
- [x] Full suite passes (**972**)

## Files

- `src/geofig_engine/core/coord.py`
- `src/geofig_engine/serialize/converters.py`
- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `src/geofig_engine/templates/piper.py`
- `tests/test_piper.py`
- `ROADMAP.md` (Phase 14.58 entry)
