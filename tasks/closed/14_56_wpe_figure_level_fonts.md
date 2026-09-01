# WP-E: Wire figure-level text through font knobs (suptitle + legend)

**Status**: complete
**Phase**: 14.56
**Dependencies**: `14_56_wpa_axis_font_model.md`, `14_56_wpb_font_flat_keys.md`

## Description

Route the two figure-level text elements - the top-level bundled `fig.suptitle`
and the standalone legend text - through the font-size knobs. These live outside
the per-coordinate frame drawers, so they are resolved from the spec's
`AxisFormat` (via `parse_axis_settings`) and threaded into the figure painters.

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- `_render_single_framed` (line ~655-657) and `_render_children` (line ~821-823):
  - `fig.suptitle(title, ...)` reads the resolved suptitle size:
    `fontsize=axis.resolve_fontsize("suptitle")` with `axis` parsed from
    `spec.settings`, replacing the hardcoded `fontsize=14`.

### `src/geofig_engine/renderers/matplotlib/legend.py`

- `render_legend_figure(legend_data, figsize=(6,4), fontsize=9)`:
  - Add optional `fontsize` param (default 9) used for `ax.legend(..., fontsize=...)`
    (line 249) and the subgroup text (line 257) as `fontsize - 1`.
- Thread the resolved value from the renderer:
  - `MatplotlibRenderer.render_legend(self, legend_data, fontsize=9)` (line ~1339):
    accepts an optional `fontsize` (default 9) and forwards it to
    `render_legend_figure`. The engine (`generator.py:133`) keeps calling without
    an argument, preserving the default; callers with access to spec settings can
    pass `axis.resolve_fontsize("legend")`.

## Acceptance criteria

- [ ] Top-level `fig.suptitle` uses `resolve_fontsize("suptitle")` (default 14) in both the single-framed and children paths
- [ ] Legend text uses `resolve_fontsize("legend")` (default 9); subgroup text is `legend - 1`
- [ ] Setting `suptitle_fontsize`/`legend_fontsize` changes output; generic `fontsize` fallback works when unset
- [ ] Default output unchanged when no font keys set

## Implementation notes

- `suptitle`: both `_render_single_framed` and `_render_children` now build an
  `AxisFormat` via `parse_axis_settings(spec.settings, spec.coord)` and use
  `resolve_fontsize("suptitle")` (default 14). Tests added in `test_axis_format.py`
  (`test_suptitle_uses_resolved_fontsize`) cover default, knob, and generic fallback.
- `legend`: `render_legend_figure` gained a `fontsize=9` param applied to the
  legend text and subgroup text (`fontsize - 1`); `MatplotlibRenderer.render_legend`
  gained an optional `fontsize=9` forwarded through. Test added in `test_legend.py`
  (`TestRenderLegendFigure::test_fontsize_propagates`).
- Full suite: 953 passed.

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `src/geofig_engine/renderers/matplotlib/legend.py`
- `src/geofig_engine/engine/generator.py` (only if `render_legend` wiring requires it)
- `tests/test_legend.py` (if present) / `tests/test_piper.py`
