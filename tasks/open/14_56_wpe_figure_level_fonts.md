# WP-E: Wire figure-level text through font knobs (suptitle + legend)

**Status**: open
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
  - `MatplotlibRenderer.render_legend(self, legend_data)` (line ~1339): parse the
    spec axis format or accept an optional fontsize and forward it to
    `render_legend_figure`. Confirm how `render_legend` is invoked by the engine
    (`engine/generator.py:133`) to pass the resolved `legend_fontsize`; if the
    legend has no clean path to settings, route via the spec's
    `parse_axis_settings(spec.settings, ...).resolve_fontsize("legend")`.

## Acceptance criteria

- [ ] Top-level `fig.suptitle` uses `resolve_fontsize("suptitle")` (default 14) in both the single-framed and children paths
- [ ] Legend text uses `resolve_fontsize("legend")` (default 9); subgroup text is `legend - 1`
- [ ] Setting `suptitle_fontsize`/`legend_fontsize` changes output; generic `fontsize` fallback works when unset
- [ ] Default output unchanged when no font keys set

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `src/geofig_engine/renderers/matplotlib/legend.py`
- `src/geofig_engine/engine/generator.py` (only if `render_legend` wiring requires it)
- `tests/test_legend.py` (if present) / `tests/test_piper.py`
