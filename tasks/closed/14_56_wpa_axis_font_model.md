# WP-A: AxisFormat font-size model + resolution helper

**Status**: complete
**Phase**: 14.56
**Dependencies**: (none)

## Description

Add the font-size option model to `AxisFormat`: one knob per text element, plus
a generic `fontsize` fallback. Every font knob is `float | None` (default `None`
== "not set"), and the effective size for an element resolves as:

```
effective(kind) = per-element fontsize   if set
                else generic fontsize    if set
                else built-in default    (=== current rendered value)
```

This is the foundation WP; all other font WPs depend on `resolve_fontsize`.

## Changes

### `src/geofig_engine/core/axis.py`

- Add module-level `_FONT_DEFAULTS: dict[str, float]` mapping each `kind` to its
  current built-in rendered default:
  - `title`: 7, `axis_label`: 7 (ternary ion labels + cartesian secondary titles),
  - `xlabel`: 10, `ylabel`: 10 (native axis labels),
  - `tick`: 5, `suptitle`: 14, `legend`: 9, `facet_title`: 10.
- Change `tick_fontsize`, `label_fontsize`, `title_fontsize` defaults to `None`.
- Add new `float | None` fields: `fontsize` (generic fallback), `xlabel_fontsize`,
  `ylabel_fontsize`, `suptitle_fontsize`, `legend_fontsize`, `facet_title_fontsize`.
- Rename semantics: the ternary ion labels / cartesian secondary titles element is
  now the `axis_label` kind (an `axis_label_fontsize` knob), unifying the current
  Anion/Cation 6 vs ternary ion 7 inconsistency.
- Add method:
  ```python
  def resolve_fontsize(self, kind: str) -> float:
  ```
  implementing the cascade above; raise `ValueError` for an unknown `kind`.
- `__post_init__`: for every non-`None` font-size field (including generic
  `fontsize`), validate via `_scalar` + `> 0` (mirror existing `tick_fontsize`
  validation). Update the field docstring/comment.

## Acceptance criteria

- [ ] `_FONT_DEFAULTS` maps all 8 `kind`s to the current rendered defaults
- [ ] All font knobs are `float | None` defaulting to `None`; generic `fontsize` added
- [ ] `resolve_fontsize(kind)` cascade tested: per-element wins over generic; generic wins over built-in default; nothing set uses built-in default
- [ ] `resolve_fontsize("bad_kind")` raises `ValueError`
- [ ] Non-positive or non-numeric font values raise `ValueError` on construction
- [ ] Existing direct `AxisFormat(tick_fontsize=5, ...)` style construction still validates (now defaults to `None`)

## Files

- `src/geofig_engine/core/axis.py`
- `tests/test_axis_format.py`
