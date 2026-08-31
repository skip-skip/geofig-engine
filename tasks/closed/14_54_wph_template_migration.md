# WP-H: Templates — keep flat axis defaults, unify on `AxisFormat`

**Status**: complete
**Phase**: 14.54
**Depends on**: 14_54_wpa_axis_format_model.md

## Description

Per-template axis-formatting defaults remain **flat top-level settings keys**
(`title`, `xlabel`, `ylabel`, `xlim`/`ylim`, `grid`, `grid_step`, `tick_step`,
`xscale`, `yscale`, `time_format`, polar toggles). There is **no nested
`settings["axis"]` dict** — an earlier structured form was trialled and reverted
as confusing. Non-axis keys (`figsize`, `figname`, `secondary_x`, `secondary_y`)
stay at the top level. `y2scale` is intentionally left untouched (dormant key —
not part of this phase).

Because the unified pipeline (WP-D) switches top-level cartesian/ternary/polar
to the shared custom/frame path, retune the `AxisFormat` appearance defaults per
template so rendered output matches the prior native look — this is what keeps
template tests green with only light updates (WP-I).

## Changes

### `src/geofig_engine/templates/` — per template

Keep axis-formatting as flat top-level defaults (no `settings["axis"]` wrapper):
- `timeseries.py` — `xscale`, `yscale`, `time_format`, `grid`
- `bivariate.py` — `xscale`, `yscale`, `grid` (leave `y2scale` untouched)
- `isotope.py` — `xscale`, `yscale`, `grid`
- `histogram.py` — `xscale`, `yscale`, `grid`
- `boxplot.py` — `xscale`, `yscale`, `grid`
- `radar.py` — `xscale`, `yscale`, `grid`, and polar toggles (`hide_spine`,
  `hide_angular_ticks`, `polar_tick_labels`) as flat keys; `xlabel`, `ylabel`
- `pie.py` — `xscale`, `yscale`, `grid`, polar toggles (`hide_spine`,
  `hide_angular_ticks`, `hide_radial_labels`, `hide_radial_ticks`,
  `polar_tick_labels`) as flat keys; `xlabel`/`ylabel`
- `npr_nnp.py`, `nagph_nag.py`, `anp_agp.py` — flat `grid`, `xlabel`, `ylabel`,
  `title`
- `stiff.py` — no axis changes (`figsize` stays top-level; frame reads coord params, not settings)
- `piper.py` — diamond child: keep `xlim`/`ylim`/`grid_step`/`tick_step` as flat
  keys; `secondary_x`/`secondary_y` stay at the child-settings top level. Parent
  `figsize`/`title` stay top-level.

Tune `AxisFormat` appearance defaults (tick fontsize, grid style, frame
linewidth, label offset) per template as needed to preserve the current native
look through the unified `_draw_frame` path.

## Acceptance criteria

- [ ] Every template produces output matching its pre-unification render (appearance preserved)
- [ ] `y2scale` is unchanged in `timeseries.py` / `bivariate.py`
- [ ] `piper.py` diamond still carries `secondary_x`/`secondary_y`
- [ ] Templates/examples/tests declare axis formatting with flat top-level keys (no `settings["axis"]`)

## Files

- `src/geofig_engine/templates/*.py` (above)
- `examples/debug_piper_axes.py` (mirror the diamond's flat keys)
- `tests/test_piper.py`, template tests asserting settings shape
