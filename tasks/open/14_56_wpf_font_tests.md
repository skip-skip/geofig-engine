# WP-F: Tests for font-size knobs + generic fallback

**Status**: open
**Phase**: 14.56
**Dependencies**: `14_56_wpa_axis_font_model.md`, `14_56_wpb_font_flat_keys.md`, `14_56_wpc_drawn_frame_fonts.md`, `14_56_wpd_native_path_fonts.md`, `14_56_wpe_figure_level_fonts.md`

## Description

Add comprehensive tests covering the font-size model, flat-key parsing, the
generic `fontsize` fallback cascade, and the render-time behavior across drawn
frames, the native path, and figure-level text.

## Changes

### `tests/test_axis_format.py`

- **Model**: default font knobs are `None`; `resolve_fontsize` returns the
  built-in default when nothing set; per-element overrides generic; generic
  overrides built-in default; unknown `kind` raises `ValueError`.
- **Validation**: non-positive / non-numeric values for every knob (incl. generic
  `fontsize`) raise `ValueError`.
- **Parse**: every `*_fontsize` key + `fontsize` round-trips via
  `parse_axis_settings`; generic-only sets generic; per-element sets only that field.
- **Drawn frames**: `tick_fontsize`, `title_fontsize`, `axis_label_fontsize`
  change the matching rendered text sizes (ternary + cartesian + polar).
- **Anion/Cation unification**: render text objects "Anions (%)"/"Cations (%)"
  have fontsize equal to `axis_label_fontsize` (default 7) for the piper.
- **Native path**: `set_title`/`set_xlabel`/`set_ylabel` use the resolved title /
  xlabel / ylabel sizes; facet panel titles/row ylabels use `facet_title`.
- **Generic fallback**: setting only `fontsize` changes unset elements; a set
  per-element knob wins over generic.

### `tests/test_piper.py`

- Update `test_children_have_settings` or add checks that ternary ion labels and
  cartesian secondary titles share the `axis_label` size, and that no frame
  element regresses vs. its default.

## Acceptance criteria

- [ ] New model/parse/validation tests pass
- [ ] Render tests confirm per-element, generic, and built-in-default resolution for drawn frames and native path
- [ ] Anion/Cation == `axis_label_fontsize` (7) confirmed for the piper
- [ ] Full test suite passes (no regressions)

## Files

- `tests/test_axis_format.py`
- `tests/test_piper.py`
- `tests/` (any others touched by WP-D / WP-E changes, e.g. legend tests)
