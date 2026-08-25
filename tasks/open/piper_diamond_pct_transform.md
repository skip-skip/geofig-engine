# Diamond: percentage data + LinkTransform (rotate 45°, scale, translate)

**Status**: open
**Phase**: 14.5
**Depends on**: `piper_frame_local_space`

## Description

Replace the baked-in `_compute_diamond_xy()` formula with percentage-normalized data and a proper LinkTransform. This completes the transform architecture: every link has a local coordinate space and a transform that maps it to world.

## Template changes (`templates/piper.py`)

**Remove**: `_compute_diamond_xy()`, `_ternary_xy()`

**Replace diamond data** with percentage-normalized coordinates:
- `dia_anion_pct = (SO4 + Cl) / (HCO3 + SO4 + Cl) * 100` — range `[0, 100]`
- `dia_cation_pct = (Ca + Mg) / (Ca + Mg + Na+K) * 100` — range `[0, 100]`

**Replace diamond AxisLink**:
```python
h = sqrt(3) / 2.0
dia_pct = h / 100  # ≈ 0.00866
diamond_link = AxisLink(
    name="diamond",
    coord=CoordCartesian(),
    transform=LinkTransform(
        translate=(0.5, 0.0),
        rotate=45.0,
        scale=(dia_pct * 0.5, dia_pct),
    ),
    frame={"provider": "piper_diamond_frame"},
)
```

This maps `[0,100]²` → world:
- `(0, 0)` → `(0.5, 0.0)` — bottom vertex (shared with ternary bases)
- `(100, 0)` → `(0.75, 0.433)` — right vertex (right tri apex)
- `(100, 100)` → `(0.5, 0.866)` — top vertex
- `(0, 100)` → `(0.25, 0.433)` — left vertex (left tri apex)

**Update `piper_overlay_diamond`**: Use percentage data instead of `_compute_diamond_xy`.

**Update `StatIonFractions`**: Replace `diamond_x`/`diamond_y` with `dia_anion_pct`/`dia_cation_pct`.

## Acceptance criteria

- [ ] Diamond layer carries `[0,100]²` percentage data
- [ ] Diamond LinkTransform correctly maps percentages to world positions
- [ ] Diamond frame grid deforms into diamond shape through the same transform
- [ ] Parity with legacy `_compute_diamond_xy` output (within numerical tolerance)
- [ ] `piper_overlay_diamond` works with new data format
- [ ] `StatIonFractions` outputs new column names
- [ ] Full test suite passes (parity tests updated)

## Files

- `src/geofig_engine/templates/piper.py`
- `src/geofig_engine/core/stat.py`
- `tests/test_piper.py`
- `tests/test_stat_ion_fractions.py`
