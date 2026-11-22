# Style knobs: generic `point_size`, native tick fonts, Piper/Stiff font sizes

**Status**: complete
**Version target**: v0.3.2 (patch — v0.3.1 is already tagged)
**Dependencies**: none

## Description

Close the remaining style-knob gaps in the declarative renderer and spec
builders:

- a generic `settings["point_size"]` knob for point/site-point layers, resolved
  through iterator context and validated;
- native-axis tick labels routed through `tick_fontsize` / generic `fontsize`,
  without changing the appearance when no font knob is set;
- explicit `fontsize` / `point_size` parameters on the Piper and Stiff spec
  builders, with documentation.

These are additive, appearance-preserving defaults: omitting the knobs keeps
the current rendered look.

## Changes

### `src/geofig_engine/engine/generator.py`

- Normalize `point_size` as a positive real number (accept numeric strings so
  iterator-formatted settings work); invalid values raise `ValueError`.
- Pass the **resolved** settings value into `resolve_layer_sources`, not the
  pre-resolution value, and record the normalized value on the `FigureSpec`.
- Keep the injection limited to `point` / `site_point` geoms and skip layers
  that already bind a `size` channel, so text/annotation font sizes are not
  affected.

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- In `_apply_axis_format_native`, apply
  `ax.tick_params(labelsize=axis.resolve_fontsize("tick"))` only when
  `tick_fontsize` or generic `fontsize` is set. With neither set, keep
  matplotlib's rcParam default.

### `src/geofig_engine/templates/piper.py`

- Keep the `fontsize` and `point_size` parameters on `build_piper_specs`;
  document their scope and precedence in the docstring.

### `src/geofig_engine/templates/stiff.py`

- Keep the `fontsize` parameter on `plot_stiff`; document it.

### `docs/api/engine.md` / `docs/api/templates.md`

- Document the generic `point_size` setting and the Piper/Stiff builder kwargs.

### Tests

- `tests/test_declarative_api.py`: marker sizing, unset default, site-point
  coverage, text `size` isolation, iterator-resolved `point_size`, validation,
  native tick font size and precedence, rcParam default preservation.
- `tests/test_piper.py`: `fontsize` on parent + children, `point_size` baked
  into point layers, knobs absent by default.
- `tests/test_stiff.py`: `fontsize` opt-in and absence by default.

## Acceptance criteria

- [ ] `settings={"point_size": ...}` resizes point/site-point markers through `render_template`
- [ ] Explicit layer `size` channels still win; text/annotation `size` is untouched
- [ ] `point_size` is resolved from iterator context and validated
- [ ] Native tick labels honor `tick_fontsize`/`fontsize` and otherwise keep matplotlib defaults
- [ ] Piper/Stiff kwargs are documented and reflected in spec behavior
- [ ] Full suite green; stop before committing for review
- [ ] Committed as `geofig-engine: style knobs and native tick fonts -> v0.3.2`

## Files

- `src/geofig_engine/engine/generator.py`
- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `src/geofig_engine/templates/piper.py`
- `src/geofig_engine/templates/stiff.py`
- `tests/test_declarative_api.py`
- `tests/test_piper.py`
- `tests/test_stiff.py`
- `docs/api/engine.md`
- `docs/api/templates.md`
- `tasks/open/style_knobs_point_size_ticks.md`
