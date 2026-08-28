# WP10: Serializer removes frame_config

**Status**: open
**Phase**: 14.52
**Depends on**: 14_52_wp7_remove_frame_config_field.md

## Description

Remove `frame_config` from serialization. `settings` already round-trips raw via
`data["settings"]`, so the now-unneeded `_frame_config_from_dict` helper (which restored
tuple-valued `xlim`/`ylim` after JSON) can be deleted.

## Changes

- `src/geofig_engine/serialize/converters.py`
  - `figure_spec_to_dict`: drop the `if spec.frame_config is not None` block (lines ~446-447)
  - `_spec_to_dict`: drop the matching block (lines ~466-467)
  - `_spec_from_dict`: drop `frame_config=_frame_config_from_dict(...)` (line ~496)
  - Delete `_frame_config_from_dict` helper (lines ~500-513)
- `tests/test_links.py`
  - `test_*serialization*` (~line 348/369) -> assert `settings` round-trips

## Verification

- [ ] FigureSpec dict/JSON round-trip preserves `settings` (incl. tuple xlim/ylim)
- [ ] Serialization tests pass

## Files

- `src/geofig_engine/serialize/converters.py`
- `tests/test_links.py`
