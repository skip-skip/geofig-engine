# WP-J: Always normalize the cartesian range in `_draw_cartesian_axis` (renderer.py)

**Status**: complete
**Phase**: 14.55
**Dependencies**: `14_55_wpi_reverse_flag_model.md`

## Description

Make `_draw_cartesian_axis` insensitive to the **declared order** of `xlim`/
`ylim`, so a descending declaration (e.g. the diamond's `xlim=(100, 0)`) no
longer breaks the frame. Today the function builds grid tick positions with
`np.arange(x0 + grid_step, x1, grid_step)` (renderer.py:415-416) and primary tick
labels with `np.arange(x0, x1 + 0.5 * tick_step, tick_step)` (renderer.py:439,
448). When `x0 > x1`, those `start > stop` `np.arange` calls return **empty**
arrays, so grid and primary ticks silently vanish. Offset math like
`0.20 * (y1 - y0)` (renderer.py:481, 487) goes negative and drives secondary
titles ("Anions (%)"/"Cations (%)") to the wrong (lower/corner) edges.

The fix is to compute **sorted (normalized) bounds** once and drive all
iteration and offset logic from them. This is the "always normalize the range"
half of the design; the explicit `x_reversed`/`y_reversed` flags (WP-K) then
supply the data/arrow reversal on top of a correctly-rendered frame.

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py` — `_draw_cartesian_axis`

After `x0, x1 = xlim; y0, y1 = ylim` (renderer.py:406-407), add:

- `xlo, xhi = min(x0, x1), max(x0, x1)`
- `ylo, yhi = min(y0, y1), max(y0, y1)`

Then replace the order-sensitive uses:

- **Grid** (415-416): `np.arange(xlo + grid_step, xhi, grid_step)` and
  `np.arange(ylo + grid_step, yhi, grid_step)`.
- **Tick offset `d`** (428-430): use `d = 1.0 if xhi - xlo == 1.0 else (xhi - xlo) / 20.0`
  so `d` stays positive.
- **Primary bottom ticks** (439-445): iterate `np.arange(xlo, xhi + 0.5 * tick_step, tick_step)`,
  place at `ylo - d`; skip endpoints against `(xlo, xhi)`.
- **Primary left ticks** (448-454): iterate `np.arange(ylo, yhi + 0.5 * tick_step, tick_step)`,
  place at `xlo - d`; skip endpoints against `(ylo, yhi)`.
- **Secondary top ticks** (456-465): place at `yhi + d`; skip vs `(xlo, xhi)`.
- **Secondary right ticks** (468-476): place at `xhi + d`; skip vs `(ylo, yhi)`.
- **Secondary x title** (479-484): `((xlo + xhi) / 2.0, yhi + 0.20 * (yhi - ylo))`.
- **Secondary y title** (485-490): `(xhi + 0.20 * (xhi - xlo), (ylo + yhi) / 2.0)`.
- **Edge title** (493-496): `((xlo + xhi) / 2.0, yhi + 0.12 * (yhi - ylo))`.

The box outline (410-412) and gridline spans (418-425) keep using `x0`/`x1`/`y0`/`y1`
(order-independent for drawing a rectangle/span) — no change needed there.

## Acceptance criteria

- [ ] A frame declared `xlim=(100,0), ylim=(100,0)` renders a **non-empty grid**
- [ ] ...and **non-empty primary ticks** (bottom + left)
- [ ] Secondary titles ("Anions (%)"/"Cations (%)") land above/right, not lower/corner
- [ ] Existing ascending `(0,100)` output is **unchanged** (normalization is a no-op for ascending)
- [ ] `test_cartesian_arrow_points_to_ascending_when_limits_descending` still passes
  (descending declaration + no flag ⇒ arrows still ascending)

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `tests/test_axis_format.py` (new frame-normalization coverage)
