# WP-D: Wire native-path text through font knobs (single + facet)

**Status**: open
**Phase**: 14.56
**Dependencies**: `14_56_wpa_axis_font_model.md`, `14_56_wpb_font_flat_keys.md`

## Description

Route the native (non-affine-stamped) axis text - used by top-level single plots
and facet panels via `_apply_axis_format_native` - through the font-size knobs.
Today `set_title`/`set_xlabel`/`set_ylabel` use matplotlib defaults (not wired to
AxisFormat) and tick `labelsize` is only wired in the polar branch.

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- `_apply_axis_format_native` (lines ~982-1043):
  - `ax.set_title(axis.title)` (line 994): `ax.set_title(axis.title, fontsize=axis.resolve_fontsize("title"))`
  - `ax.set_xlabel(ylabel)` / `ax.set_ylabel(xlabel)` (lines 999-1006, both flipped and normal branches):
    - xlabel -> `fontsize=axis.resolve_fontsize("xlabel")`
    - ylabel -> `fontsize=axis.resolve_fontsize("ylabel")`
  - Respect the CoordFlipped swap: the "x" slot renders via the `ylabel`
    local-variable mapping, so pass the matching resolved `xlabel`/`ylabel` size.

### Facet path (lines ~1242-1270)

- Facet panel titles (lines 1252/1268): replace `fontsize=10` with
  `fontsize=axis.resolve_fontsize("facet_title")`.
- Facet row ylabel (line 1270): replace `fontsize=10` with
  `fontsize=axis.resolve_fontsize("facet_title")`.

## Acceptance criteria

- [ ] Native `set_title` uses `resolve_fontsize("title")` (default 7)
- [ ] Native `set_xlabel`/`set_ylabel` use `resolve_fontsize("xlabel")`/`resolve_fontsize("ylabel")` (default 10), including CoordFlipped (swapped) case
- [ ] Facet panel titles and row ylabels use `resolve_fontsize("facet_title")` (default 10)
- [ ] Setting generic `fontsize` changes unset native text; set per-element knobs still win

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `tests/test_axis_format.py`
