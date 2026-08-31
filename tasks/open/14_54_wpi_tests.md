# WP-I: Tests for the unified axis/frame pipeline

**Status**: open
**Phase**: 14.54
**Depends on**: 14_54_wpa..14_54_wph

## Description

Add and update tests covering the `AxisFormat` model, `parse_axis_settings`
parsing/fallback, unified `_draw_frame` behavior, top-level ≡ child parity
(cartesian, ternary, polar), the top-level ternary frame, facet formatting,
serialization, and validation. Emphasize that a top-level spec renders through
the **same functions and spec** as a child.

## Changes

### New `tests/test_axis_format.py`

- **Model/parse**
  - `parse_axis_settings({}, coord)` returns defaults (no crash).
  - Explicit `settings["axis"]` equals the equivalent legacy flat keys
    (method parity for cartesian, ternary, polar).
  - Polar legacy keys map into `AxisFormat.options`.
  - `tick_format` defaults to `":g"`; appearance knobs have native-match defaults.
- **Validation**
  - Malformed `limits` / non-positive `tick_step` / bad `label_policy` /
    bad `tick_format` raise `ValueError`, both from the parser directly and from
    `FigureSpec` construction (WP-F).
- **Serialization**
  - `settings["axis"]["limits"]` and `figsize` survive a JSON round-trip as
    tuples (WP-G).
- **Rendering parity (unified pipeline)**
  - Top-level cartesian ≡ child cartesian via the same `_draw_frame` (compare
    artist/text counts and titles/limits/grid where applicable).
  - **Top-level ternary draws a frame**: a single `TernaryCoord` spec produces
    the same triangle/ticks/ion-arrows as a child ternary (WP-D).
  - Polar: pie/radar frame driven by `AxisFormat` + options (WP-C).
  - Faceted panels formatted from `AxisFormat` (WP-E).
  - `tick_format` (e.g. `"{:.1f}"`) changes numeric tick labels only.

### Existing test updates

- `tests/test_piper.py` — diamond child now asserts `settings["axis"]` for
  `limits`/`grid_step`/`tick_step` (WP-H), `secondary_x`/`secondary_y` unchanged.
- Template/polar/facet tests asserting flat-key defaults — update to the new
  `settings["axis"]` shape and any light appearance changes (WP-H).

## Verification

- [ ] `python -m pytest tests/ -q` — all pass (849 + new)
- [ ] `python examples/hydro_demo.py` — 7 figures render, appearance preserved
- [ ] `python examples/debug_piper_axes.py` — diamond unchanged (children path)

## Files

- `tests/test_axis_format.py` (new)
- `tests/test_piper.py`
- Template/polar/facet tests touched by WP-H / WP-D / WP-C / WP-E
