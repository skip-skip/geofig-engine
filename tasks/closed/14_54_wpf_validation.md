# WP-F: Validate `settings["axis"]` in `validate_figure_spec`

**Status**: complete
**Phase**: 14.54
**Depends on**: 14_54_wpa_axis_format_model.md

## Description

Surface axis-format validation at `FigureSpec` construction time so a malformed
`settings["axis"]` declaration fails fast with a clear error — mirroring the
existing `_validate_secondary_settings` hook. Currently the only axis validation
is the secondary-axis check; all other axis keys (`xlim`/`ylim`, `grid`,
`grid_step`, `tick_step`, `label_policy`, `title`, `xscale`, `yscale`,
`time_format`, polar toggles) are unvalidated.

## Changes

### `src/geofig_engine/core/spec.py`

- Add `_validate_axis_settings(settings, coord=None)` that delegates to
  `parse_axis_settings(...)`, which enforces: `limits` pair/pair-of-pairs,
  positive `grid_step`/`tick_step`, valid `label_policy` enum, valid
  `tick_format` string, and (when present) recognized `options` and appearance
  knobs.
- Call it from `validate_figure_spec` alongside `_validate_secondary_settings`
  (line ~108), passing `spec.coord` so coord-specific validation can apply.
- `_validate_secondary_settings` is unchanged.

## Acceptance criteria

- [ ] `FigureSpec(settings={"axis": ...})` with a bad `limits` raises `ValueError` at construction
- [ ] Bad `label_policy` / non-positive `tick_step` / bad `tick_format` raise `ValueError`
- [ ] A valid `settings["axis"]` (and legacy flat keys with no `axis`) constructs without error
- [ ] Existing templates/specs without an `axis` key are unaffected

## Files

- `src/geofig_engine/core/spec.py`
- `tests/test_axis_format.py` (validation-on-construction cases)
