# WP-L: Piper diamond — normalized limits + explicit reversal flags (templates/piper.py)

**Status**: complete
**Phase**: 14.55
**Dependencies**: `14_55_wpi_reverse_flag_model.md`, `14_55_wpj_cartesian_normalize_range.md`, `14_55_wpk_cartesian_reverse_arrows.md`

## Description

Update the piper template's diamond child to use the new declarative reversal
instead of the fragile descending `xlim`/`ylim` hack. The current diamond
(templates/piper.py:125-150) declares `"xlim": (100, 0), "ylim": (100, 0)` in an
attempt to reverse the axes; after WP-J/WP-K normalization + flags, the correct
expression is **normalized limits** plus explicit `x_reversed`/`y_reversed`.

Data placement is unaffected: linked-child data is placed via
`visual_mapping` + `LinkTransform` + `_children_world_limits`, none of which read
frame `xlim`/`ylim`. Reversal is purely a frame-reading (labels + arrows + grid)
concern. The diamond's `_dia_anion_pct`/`_dia_cation_pct` raw percent values stay
in local coordinates unchanged.

## Changes

### `src/geofig_engine/templates/piper.py` — diamond `settings` (128-136)

Replace:

```python
"xlim": (100, 0),
"ylim": (100, 0),
```

with:

```python
"xlim": (0, 100),
"ylim": (0, 100),
"x_reversed": True,
"y_reversed": True,
```

Keep `"axis_arrows": True`, `"grid_step": 20`, `"tick_step": 20`, and the
`secondary_x`/`secondary_y` declarations (`range [0, 100]`, labels unchanged).

## Acceptance criteria

- [ ] Diamond declares normalized `xlim`/`ylim` `(0, 100)` with `x_reversed`/`y_reversed` `True`
- [ ] `test_piper.py::test_children_have_settings` updated to the new settings
- [ ] Diamond grid + ticks render (non-empty)
- [ ] "Anions (%)"/"Cations (%)" titles on the upper/right edges
- [ ] Diamond arrows point toward increasing data consistent with the reversed labels

## Files

- `src/geofig_engine/templates/piper.py`
- `tests/test_piper.py`
