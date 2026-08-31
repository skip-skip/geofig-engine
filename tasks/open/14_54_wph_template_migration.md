# WP-H: Migrate templates to `settings["axis"]`

**Status**: open
**Phase**: 14.54
**Depends on**: 14_54_wpa_axis_format_model.md

## Description

Move per-template axis-formatting defaults from flat top-level settings keys
into the structured `settings["axis"]` dict. Keep non-axis keys (`figsize`,
`title`, `figname`, etc.) at the top level. `y2scale` is intentionally left
untouched (dormant key — not part of this phase).

Because the unified pipeline (WP-D) switches top-level cartesian/ternary/polar
to the shared custom/frame path, retune the `AxisFormat` appearance defaults per
template so rendered output matches the prior native look — this is what keeps
template tests green with only light updates (WP-I).

## Changes

### `src/geofig_engine/templates/` — per template

Move these into `settings["axis"] = {...}`:
- `timeseries.py` — `xscale`, `yscale`, `time_format`, `grid`
- `bivariate.py` — `xscale`, `yscale`, `grid` (leave `y2scale` untouched)
- `isotope.py` — `xscale`, `yscale`, `grid`
- `histogram.py` — `xscale`, `yscale`, `grid`
- `boxplot.py` — `xscale`, `yscale`, `grid`
- `radar.py` — `xscale`, `yscale`, `grid`, and polar toggles (`hide_spine`,
  `hide_angular_ticks`, `polar_tick_labels`) into `axis.options`; `xlabel`,
  `ylabel` into `axis.xlabel`/`axis.ylabel`
- `pie.py` — `xscale`, `yscale`, `grid`, polar toggles (`hide_spine`,
  `hide_angular_ticks`, `hide_radial_labels`, `hide_radial_ticks`,
  `polar_tick_labels`) into `axis.options`; `xlabel`/`ylabel` into axis fields
- `npr_nnp.py`, `nagph_nag.py`, `anp_agp.py` — `grid`, `xlabel`, `ylabel`
- `stiff.py` — no axis changes (`figsize` stays top-level; frame reads coord params, not settings)
- `piper.py` — diamond child: move `xlim`/`ylim` → `axis.limits`,
  `grid_step`/`tick_step` → `axis.grid_step`/`axis.tick_step`; keep
  `secondary_x`/`secondary_y` at the child-settings top level. Parent
  `figsize`/`title` stay top-level.

Tune `AxisFormat` appearance defaults (tick fontsize, grid style, frame
linewidth, label offset) per template as needed to preserve the current native
look through the unified `_draw_frame` path.

## Acceptance criteria

- [ ] Every migrated template produces output matching its pre-unification render (appearance preserved)
- [ ] `y2scale` is unchanged in `timeseries.py` / `bivariate.py`
- [ ] `piper.py` diamond still carries `secondary_x`/`secondary_y`
- [ ] Existing template tests that assert on flat-key defaults are updated to the new `settings["axis"]` shape (light updates)

## Files

- `src/geofig_engine/templates/*.py` (above)
- `examples/debug_piper_axes.py` (mirror the diamond's `settings["axis"]` change)
- `tests/test_piper.py`, template tests asserting settings shape
