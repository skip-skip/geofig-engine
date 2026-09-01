# WP-B: Parse font-size flat keys in parse_axis_settings

**Status**: open
**Phase**: 14.56
**Dependencies**: `14_56_wpa_axis_font_model.md`

## Description

Extend `parse_axis_settings` to read all font-size keys as flat settings keys so
they work directly from figure YAML/JSON. Today **no** `*_fontsize` key is parsed
from settings (they only work via direct `AxisFormat(...)` construction); this WP
closes that gap and adds the generic `fontsize` fallback key.

## Changes

### `src/geofig_engine/core/axis.py` - `parse_axis_settings`

- Add parsing for the generic key `fontsize`.
- Add parsing for each per-element key:
  - `title_fontsize` -> `title_fontsize`
  - `axis_label_fontsize` -> `axis_label_fontsize`
  - `xlabel_fontsize` -> `xlabel_fontsize`
  - `ylabel_fontsize` -> `ylabel_fontsize`
  - `tick_fontsize` -> `tick_fontsize`
  - `suptitle_fontsize` -> `suptitle_fontsize`
  - `legend_fontsize` -> `legend_fontsize`
  - `facet_title_fontsize` -> `facet_title_fontsize`
- Use the existing `_pick(...)` helper so unknown keys are ignored and `None`
  values pass through as unset.
- Update the `parse_axis_settings` docstring to list the new keys.

## Acceptance criteria

- [ ] Every `*_fontsize` key and `fontsize` round-trips through `parse_axis_settings`
- [ ] Setting only generic `fontsize` leaves all per-element fields `None`
- [ ] Setting a per-element key sets that field and leaves others `None`
- [ ] Absent keys remain `None` (unset), preserving defaults at render
- [ ] Non-positive / non-numeric values raise `ValueError` (propagated from WP-A validation)

## Files

- `src/geofig_engine/core/axis.py`
- `tests/test_axis_format.py`
