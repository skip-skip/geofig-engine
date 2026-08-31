# WP-F: Templates opt in to `axis_arrows` (preserve ternary arrows)

**Status**: complete
**Phase**: 14.55
**Dependencies**: `14_55_wpd_ternary_arrows_decouple.md`

## Description

Because `axis_arrows` defaults to **off** (WP-A), any ternary that previously
relied on the hardcoded arrows would silently lose them once WP-D decouples and
removes the fused arrows. Templates/examples that want to keep their ternary
edge arrows must explicitly set `axis_arrows: true`.

Affected: the piper template's two ternary children (each currently has empty
`settings={}`), and the hydro demo which renders piper diagrams.

## Changes

### `src/geofig_engine/templates/piper.py`

- The cation (right) ternary child — `settings={}` at ~line 96 — and the anion
  (left) ternary child — `settings={}` at ~line 111 — should each declare
  `settings={"axis_arrows": True, ...}` (merging with any existing keys) so both
  piper triangles keep their arrows through the new mechanism.
- The diamond cartesian child (`settings={...}` at ~line 128) currently has **no**
  arrows; by default leave `axis_arrows` off there to preserve current output
  (verify with the maintainer whether cartesian/secondary arrows are wanted —
  default: no).

### `examples/hydro_demo.py` (and any ternary example)

- Ensure the ternary specs enable `axis_arrows: true` so the rendered piper
  examples still show edge arrows after the overhaul.

### Examples/tests

- Update `examples/debug_piper_axes.py` and any piper/ternary test that relies
  on ternary arrows to reflect the new opt-in (arrow presence is now a function
  of `axis_arrows`, not implicit).

## Acceptance criteria

- [x] Piper `/ hydro / debug_piper_axes` ternary output shows ion labels AND arrows (via `axis_arrows: true`)
- [x] Ran `python hydro_demo.py` and `examples/debug_piper_axes.py` — piper triangles render identically to before (arrows preserved)
- [x] The diamond cartesian child stays unchanged (no arrows) unless the maintainer opts in cartesian arrows
- [x] No ternary example relies on implicit/hardcoded arrows anymore

## Files

- `src/geofig_engine/templates/piper.py`
- `examples/hydro_demo.py`
- `examples/debug_piper_axes.py`
