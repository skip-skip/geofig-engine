# WP-G: Tests for axis-arrow behavior

**Status**: complete
**Phase**: 14.55
**Dependencies**: `14_55_wpa_axis_arrows_model.md`, `14_55_wpc_cartesian_axis_arrows.md`, `14_55_wpd_ternary_arrows_decouple.md`, `14_55_wpe_polar_radial_arrow.md`

## Description

Add automated coverage for the new `axis_arrows` feature across the model and
each framed coordinate path, and update any existing tests whose assertions
touch the old hardcoded ternary arrows. Arrow "direction" is asserted from the
`annotate`/`arrow` geometry (which endpoint holds the arrowhead) rather than by
eyeballing pixels.

## Changes

### `tests/test_axis_format.py` — model/parse (WP-A)

- `parse_axis_settings({}, coord).show_arrows()` is `False`
- `parse_axis_settings({"axis_arrows": True}, coord).show_arrows()` is `True`
- `AxisFormat(axis_arrows="nope")` / bad `axis_arrows` raise `ValueError`

### `tests/test_axis_format.py` — cartesian framed arrows (WP-C)

- Framed cartesian (`_render_single_top`/`_render_child` with `xlim`/`ylim`):
  - `axis_arrows: true` → at least one arrow artist present; `false`/absent → none
  - X + Y arrows both present
  - With `secondary_x`/`secondary_y` → arrows also on top/right edges
  - Direction: with ascending `xlim=(0,100)` the arrowhead is at the high-x end;
    with descending `xlim=(100,0)` it is still pointed toward the larger numeric
    value (verify via the annotate endpoint coordinates / arrowhead position)

### `tests/test_axis_format.py` — ternary arrows + decoupled labels (WP-D)

- Ion labels (`Mg`/`Ca`/`Na+K`) still render with `axis_arrows` off (decoupled —
  labels present, no arrows)
- `axis_arrows: true` → 3 edge arrows present, each pointing toward ascending
  value; off/absent → no edge arrows
- Update the loose "ion arrows" comments/assertions in
  `test_top_level_ternary_renders_triangle` and `test_linked_render.py:150`
  to be explicit about labels vs. arrows

### `tests/test_axis_format.py` — polar radial arrow (WP-E)

- Polar (`_draw_polar_frame`) with `axis_arrows: true` → a radial arrow pointing
  outward; off/absent → none; independent of `hide_radial_ticks`/`hide_spine`
  toggles

### Regression

- Full suite green after WP-F template opt-ins (piper/hydro/ternary).

## Acceptance criteria

- [x] Model parse/validation covered (default off, True, invalid type)
- [x] Cartesian x/y (+ secondary) arrow counts and direction covered, including the descending-limits (sorted) case
- [x] Ternary labels-decoupled-from-arrows covered (labels without arrows, arrows on/off)
- [x] Polar radial arrow covered
- [x] Full suite passes with only the intended additions/light updates

## Files

- `tests/test_axis_format.py`
- `tests/test_linked_render.py` (light update)
- `tests/test_piper.py` (as needed, light update)
