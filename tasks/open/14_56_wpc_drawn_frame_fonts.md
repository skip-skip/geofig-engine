# WP-C: Wire drawn-frame text through font knobs (ternary/cartesian/polar)

**Status**: open
**Phase**: 14.56
**Dependencies**: `14_56_wpa_axis_font_model.md`, `14_56_wpb_font_flat_keys.md`

## Description

Route all text drawn inside the affine-stamped coordinate frames
(`_draw_ternary_frame`, `_draw_cartesian_axis`, `_draw_polar_frame`) through
`axis.resolve_fontsize(kind)` so the per-element knob + generic `fontsize`
fallback control every frame label. Defaults preserve today's output, except the
deliberate unification of the cartesian secondary titles under `axis_label`
(Anion/Cation 6 -> 7, matching ternary ion labels).

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- `_draw_ternary_frame` (lines ~219-364):
  - tick labels (lines 273/280/288): `fontsize=axis.resolve_fontsize("tick")`
  - edge title (line 296): `fontsize=axis.resolve_fontsize("title")`
  - ion labels (line 310-312): `fontsize=axis.resolve_fontsize("axis_label")`
  - arrow `label_fs` (lines 328-364): pass `axis.resolve_fontsize("axis_label")`
    when a label is present
- `_draw_cartesian_axis` (lines ~367-543):
  - tick labels (lines 446/456/467/478): `fontsize=axis.resolve_fontsize("tick")`
  - edge title (line 499): `fontsize=axis.resolve_fontsize("title")`
  - **secondary titles (lines 486/492)**: replace hardcoded `fontsize=6` with
    `axis.resolve_fontsize("axis_label")` (the Anion/Cation 6->7 unification)
  - arrow calls (lines 511-542): thread `axis_label` fontsize where a label is drawn
- `_draw_polar_frame` (lines ~1056-1115):
  - tick labels (line 1093): `ax.tick_params(labelsize=axis.resolve_fontsize("tick"))`
  - radial arrow (lines 1109-1114): thread `axis_label` fontsize if a label is added

Preserve the existing `_tick_fontsize`/`tick_fs` local variable naming or replace
as appropriate; keep `frame_lw`/tick/title locals consistent.

## Acceptance criteria

- [ ] Default render (no font keys set) produces identical sizes to today, except Anion/Cation titles now `7`
- [ ] Setting `tick_fontsize` changes tick labels in ternary, cartesian (primary + secondary), and polar
- [ ] Setting `title_fontsize` changes edge titles in ternary and cartesian
- [ ] Setting `axis_label_fontsize` changes ternary ion labels and cartesian secondary titles together
- [ ] Setting generic `fontsize` alone changes all unset frame elements; a set per-element knob still wins
- [ ] No hardcoded `fontsize=6` remains for the secondary titles in `_draw_cartesian_axis`

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `tests/test_piper.py`
