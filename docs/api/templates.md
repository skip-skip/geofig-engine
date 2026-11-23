# API Reference — Templates

Templates bundle a configured set of [`Layer`](core.md#layers--specs)s, a
default settings dict, and (optionally) a coordinate system + name. The
**native `*_builder` functions are the source of truth**: all ten legacy keys
are seeded directly into the [`TEMPLATES` registry](engine.md#templates-registry)
and render through `render_template` without an adapter. `FigureTemplate` and
the scalar/spec-builder functions below remain supported as **compatibility
surfaces**; the factories delegate to the same native builders.

```python
from geofig_engine.templates import (
    FigureTemplate,
    bivariate, boxplot_with_points,
    histogram, histogram_builder,
    timeseries, timeseries_builder,
    pie, pie_builder, radar, radar_builder,
    isotope, isotope_builder,
    npr_nnp, npr_nnp_builder,
    anp_agp, anp_agp_builder,
    nagph_nag, nagph_nag_builder,
    build_piper_specs, piper_builder,
    plot_stiff, stiff_builder,
)
```

## Contents

- [FigureTemplate (compatibility surface)](#figuretemplate-compatibility-surface)
- [Native builders](#native-builders)
- [Generic templates](#generic-templates)
- [Pie & radar](#pie--radar)
- [Hydrogeochemical templates](#hydrogeochemical-templates)
- [Spec builders](#spec-builders)

---

## FigureTemplate (compatibility surface)

`FigureTemplate` objects are still accepted directly by `render_template` and
are adapted via `recipe_from`; prefer the native builders or registry keys for
new code.

```python
@dataclass(frozen=True)
class FigureTemplate:
    layers: list[Layer]
    default_settings: dict[str, Any] = {}
    coord: Coord = CoordCartesian()
    name: str = "custom"
```

`__post_init__` raises `ValueError` if `layers` is empty, `TypeError` if a
layer isn't a `Layer`, if `default_settings` isn't a dict, or if `coord` isn't
a `Coord`.

Usage via `render_template` (key form — the factory set is registered in
[`TEMPLATES`](engine.md#templates-registry)):

```python
from geofig_engine import render_template

figures = render_template(
    data=df,                                    # raw DataFrame is fine
    template="bivariate",                       # registry key
    mapping={"x": "x", "y": "y"},
    settings={"figsize": (8, 6)},   # merged OVER template defaults
)
```

or equivalently with a constructed template object:

```python
figures = render_template(
    data=df,
    template=bivariate(mapping={"x": "x", "y": "y"}),
    settings={"figsize": (8, 6)},
)
```

`mapping`/`settings`/`coord` passed to `render_template` are merged **over**
the template's defaults (per-layer mapping override: only channels already
bound to a string source are remapped).

---

## Native builders

The eight layer-recipe builders seeded for the legacy factory keys share this
call shape:

```python
builder(mapping=None, settings=None, **kwargs) -> TemplateRecipe
```

`render_template(key, ...)` passes `mapping` and `settings` only. When calling
a builder directly through `get_template(key)`, the listed template kwargs may
be passed as `**kwargs` instead of flat `settings` entries. Renderer settings
(`figsize`, `title`, `grid`, axis/label keys, …) always merge into
`default_settings`.

| Builder | Effective template parameters | Flat `settings` keys | Default settings |
| --- | --- | --- | --- |
| `histogram_builder` | `bins=10`, `density=False`, `cumulative=False`, `scales=None` | `bins`, `density`, `cumulative` | `{"figsize": (10, 6), "xscale": "linear", "yscale": "linear", "grid": True}` |
| `pie_builder` | `show_percent=False`, `show_count=False`, `show_name=True` | `show_percent`, `show_count`, `show_name` | `{"figsize": (8, 8), "grid": False, "polar_tick_labels": True, ...}` |
| `radar_builder` | `fill=True`, `fill_alpha=0.7`, `shared_axes=True` | `fill`, `fill_alpha`, `shared_axes` | `{"figsize": (8, 8), "grid": True, "polar_tick_labels": True, ...}` |
| `timeseries_builder` | `scales=None` | — | `{"figsize": (10, 6), "time_format": "%Y-%m-%d", "grid": True, ...}` |
| `isotope_builder` | `scales=None`, `functions=None`, `auto_filter=True` | `functions`, `auto_filter` | `{"figsize": (10, 6), "grid": True, ...}` |
| `npr_nnp_builder` | `npr_crit=3`, `nnp_crit=20`, `scales=None` | `npr_crit`, `nnp_crit` | `{"figsize": (8, 8), "title": "NPR vs NNP — ARD Classification", ...}` |
| `anp_agp_builder` | `scales=None` | — | `{"figsize": (8, 8), "title": "ANP vs AGP — Classification", ...}` |
| `nagph_nag_builder` | `scales=None` | — | `{"figsize": (8, 6), "title": "NAG pH vs NAG — Classification", ...}` |

Each builder fills a default `x`/`y` mapping stub so its registry key works
without a user mapping; a supplied `mapping` overrides those stubs. The eight
factory functions for these legacy keys call the builders with
`_legacy_factory=True` and wrap the result in a `FigureTemplate`, preserving
the original mapping validation (for example, `histogram()` still requires
`mapping["x"]`).

---

## Generic templates

The factory functions in this section are compatibility wrappers. Their
outputs are unchanged; see [Native builders](#native-builders) for the
registry path.

### `bivariate(mapping=None, scales=None)`

Scatter template (`GeomPoint` + `StatIdentity`, `coord=CoordCartesian`).

| Param | Type | Description |
| --- | --- | --- |
| `mapping` | `dict[str, SourceType] \| None` | Mapping to forward to the point layer (e.g. `x`, `y`, `color`, `marker`). |
| `scales` | `dict[str, Scale] \| None` | Per-channel scales passed to the point layer. |

**Defaults:** `{"figsize": (10, 6), "xscale": "linear", "yscale": "linear", "y2scale": "linear", "grid": True}`.

### `boxplot_with_points(mapping=None, scales=None, box_width=0.8, jitter_width=0.08, point_size=8, point_alpha=0.4, sort_mode="none", smush=False, showfliers=True, showmeans=False, show_n=False, min_box_n=1)`

Composes two layers sharing the same `x`/`y`/`color` mapping: a `GeomBox`
boxplot layer and a `GeomPoint` jittered point layer (dodged to the box
positions). See `GeomBox`/`GeomPoint` in [core](core.md#geoms) for the
parameters.

**Defaults:** `{"figsize": (10, 6), "xscale": "linear", "yscale": "linear", "grid": True}`.

### `timeseries(mapping=None, scales=None)`

Line + point template using `GeomLine` and `GeomPoint`, sharing `mapping` and
`scales`.

**Defaults:** `{"figsize": (10, 6), "xscale": "linear", "yscale": "linear", "y2scale": "linear", "time_format": "%Y-%m-%d", "grid": True}`.

### `histogram(mapping=None, scales=None, bins=10, density=False, cumulative=False)`

Bar histogram (`GeomBar` + `StatBin` on `mapping["x"]`).

| Param | Type | Description |
| --- | --- | --- |
| `mapping` | `dict[str, SourceType] \| None` | Must include `x`; may include `color` and `alpha` (forwarded to the `StatBin`). |
| `scales` | `dict[str, Scale] \| None` | Per-channel scales. |
| `bins` | `int \| str` | Bin count (or binning spec) for `StatBin`. |
| `density` | `bool` | Density-weighted histogram. |
| `cumulative` | `bool` | Cumulative counts. |

**Raises:** `ValueError` if `mapping["x"]` is missing.

**Defaults:** `{"figsize": (10, 6), "xscale": "linear", "yscale": "linear", "grid": True}`.

---

## Pie & radar

### `pie(mapping=None, show_percent=False, show_count=False, show_name=True)`

Pie template (`GeomBar` + `StatSum`, `coord=CoordPolar(theta="x")`).

| Param | Type | Description |
| --- | --- | --- |
| `mapping` | `dict[str, SourceType] \| None` | Must include `x` (category) and `y` (value). |
| `show_percent` | `bool` | Append `NN.N%` to slice labels. |
| `show_count` | `bool` | Append `n=N` to slice labels. |
| `show_name` | `bool` | Include the category name in slice labels. |

**Raises:** `ValueError` if `x` or `y` is missing from `mapping`.

**Defaults:** `{"figsize": (8, 8), "xscale": "linear", "yscale": "linear", "grid": False, "hide_spine": True, "hide_angular_ticks": True, "hide_radial_labels": True, "hide_radial_ticks": True, "polar_tick_labels": True, "xlabel": "", "ylabel": ""}`.

### `radar(mapping=None, fill=True, fill_alpha=0.7, shared_axes=True)`

Radar/star template (`GeomArea` + `GeomLine` with `StatRadar`,
`coord=CoordPolar(theta="x")`, `ScaleNormalize` on `y`).

| Param | Type | Description |
| --- | --- | --- |
| `mapping` | `dict[str, SourceType] \| None` | Must include `x` (axis/category) and `y` (value); may include `color`. |
| `fill` | `bool` | Draw the filled area layer (plus the line layer). |
| `fill_alpha` | `float` | Area fill opacity. |
| `shared_axes` | `bool` | Passed to `StatRadar`. |

**Raises:** `ValueError` if `x` or `y` is missing from `mapping`.

**Defaults:** `{"figsize": (8, 8), "xscale": "linear", "yscale": "linear", "grid": True, "hide_spine": True, "hide_angular_ticks": True, "polar_tick_labels": True, "xlabel": "", "ylabel": ""}`.

---

## Hydrogeochemical templates

These prepend reference/annotation layers to a final data point layer and
stamp hydrogeochemical default settings. The point layer takes the provided
`mapping`/`scales`; the reference layers use constant mappings.

### `npr_nnp(mapping=None, npr_crit=3, nnp_crit=20, scales=None)`

ARD classification: NPR vs NNP. Layers: `GeomVSpan` + `GeomHSpan` shaded
regions, two `GeomAbline` criteria lines, three `GeomText` region labels, and
the data `GeomPoint` layer (`zorder=10`).

| Param | Type | Description |
| --- | --- | --- |
| `mapping` | `dict[str, SourceType] \| None` | Data point mapping (e.g. `x="NPR", y="NNP"`). |
| `npr_crit` | `float` | NPR criterion value (vertical half-width / annotations). |
| `nnp_crit` | `float` | NNP criterion value (horizontal half-width / annotations). |
| `scales` | `dict[str, Scale] \| None` | Scales for the point layer. |

**Defaults:** `{"figsize": (8, 8), "title": "NPR vs NNP — ARD Classification", "grid": True, "xlabel": "NPR (Neutralisation Potential Ratio)", "ylabel": "NNP (Net Neutralisation Potential)"}`.

### `anp_agp(mapping=None, scales=None)`

ANP vs AGP classification. Layers: four labeled `GeomAbline` ratio lines
(NP:AP 1:1–4:1) with `GeomText` labels, three region `GeomText` labels, and the
data `GeomPoint` layer.

**Defaults:** `{"figsize": (8, 8), "title": "ANP vs AGP — Classification", "grid": True, "xlabel": "AGP (Acid Generation Potential)", "ylabel": "ANP (Acid Neutralisation Potential)"}`.

**Requires:** `mapping` with `x`/`y` for the point layer.

### `nagph_nag(mapping=None, scales=None)`

NAG pH vs NAG classification (reference lines at NAG pH 4.5 and 18.14 kg
H₂SO₄/t with four region labels and two boundary annotations).

**Defaults:** `{"figsize": (8, 6), "title": "NAG pH vs NAG — Classification", "grid": True, "xlabel": "NAG pH", "ylabel": "NAG (kg H₂SO₄/t)"}`.

**Requires:** `mapping` with `x`/`y` for the point layer.

### `isotope(mapping=None, scales=None, functions=None, auto_filter=True)`

Isotope plot: `GeomFunctionLine` reference layers from the geom preset
registry plus a `GeomPoint` data layer. See [data](data.md) for the registry.

| Param | Type | Description |
| --- | --- | --- |
| `mapping` | `dict[str, SourceType] \| None` | Data point mapping (e.g. `x="δ18O", y="δD"`). |
| `scales` | `dict[str, Scale] \| None` | Scales for the point layer. |
| `functions` | `Sequence[str] \| None` | Explicit preset IDs to load; `None` + `auto_filter=True` loads all `water_isotope`/`function_line` presets. |
| `auto_filter` | `bool` | When `functions is None` and `auto_filter=True`, include all applicable presets; if `auto_filter=False`, no reference layers are added. |

**Validation:** each requested preset must have `category == "water_isotope"`,
use only `function_line` geoms, and expose the required variable `x`.
Violations raise `ValueError`.

**Defaults:** `{"figsize": (10, 6), "xscale": "linear", "yscale": "linear", "grid": True}`.

---

## Spec builders

`piper` and `stiff` are inherently composite linked-axes figures. Their native
registry builders return a `SpecRecipe`, which `render_template` calls with the
coerced provider frame; the resulting [`FigureSpec`](core.md#layers--specs)
objects then follow the normal renderer/legend/savedir path. `iterators` and
`facet` are not supported for these keys. The scalar/spec-builder functions at
the end of this section remain direct compatibility entry points.

### `piper_builder(mapping=None, settings=None, **_) -> SpecRecipe`

| Flat `settings` key | Default | Description |
| --- | --- | --- |
| `left_tri` | `("Ca", "Mg", "Na+K")` | Cation channels `(apex, bottom-left, bottom-right)`. |
| `right_tri` | `("HCO3", "SO4", "Cl")` | Anion channels. |
| `title` | `"Piper Diagram"` | Figure title. |
| `labels` | `None` | Channel → display-label overrides (charge-bearing mathtext by default). |
| `axis_label_policy` | `"parallel"` | `"parallel"` or `"upright"` ion/diamond label rotation. |
| `fontsize` | `None` | Generic font fallback on the parent and three children. |
| `point_size` | `None` | Constant marker size on the point layers. |

The frame must contain the six ion columns (or the columns named by
`left_tri` / `right_tri`). `mapping` may add visual channels such as `color`
or `marker`.

### `stiff_builder(mapping=None, settings=None, **_) -> SpecRecipe`

| Flat `settings` key | Default | Description |
| --- | --- | --- |
| `title` | `""` | Figure title. |
| `figsize` | `(6, 6)` | Figure size. |
| `fontsize` | `None` | Generic font fallback; omitted by default. |

The frame must be a **one-row** `pd.DataFrame` with columns `ca`, `mg`,
`na_k`, `cl`, `hco3`, `so4` (values in meq/L). Missing columns or multiple rows
raise `ValueError`.

### `build_piper_specs(data, left_tri=("Ca", "Mg", "Na+K"), right_tri=("HCO3", "SO4", "Cl"), mapping=None, title="Piper Diagram", labels=None, axis_label_policy="parallel", fontsize=None, point_size=None)` (compatibility)

Builds a Piper diagram using linked axes. Returns a single-element `list` of
`FigureSpec`: a parent cartesian axis (the diamond, world space) with three
children — the cation triangle (`TernaryCoord`, left-handed, scale 0.5), the
anion triangle (`TernaryCoord`, right-handed, mirrored + translated), and the
diamond (`CoordCartesian`, `LinkTransform` rotate 45° + scale + translate)
with two `SecondaryAxis` declarations for the cation/anion percentage scales.

| Param | Type | Description |
| --- | --- | --- |
| `data` | `pd.DataFrame` | Must contain the ion columns in `left_tri` and `right_tri` (meq/L — no unit conversion). |
| `left_tri` | `tuple[str, str, str]` | Cation channels `(apex, bottom-left, bottom-right)` reading order. |
| `right_tri` | `tuple[str, str, str]` | Anion channels (mirrored for right-handed reading). |
| `mapping` | `dict[str, SourceType] \| None` | Passthrough visual channels (`color`, `marker`, …) applied to all four sub-plots. Values may be column names or `pd.Series`. |
| `title` | `str` | Figure title. |
| `labels` | `dict[str, str] \| None` | Channel → display label overrides (defaults provide charge-bearing mathtext, e.g. `$Ca^{++}$`). |
| `axis_label_policy` | `"upright" \| "parallel"` | Rotation of axis labels (ternary ion names + diamond titles). Default `"parallel"`. |
| `fontsize` | `float \| None` | Generic font-size fallback on the parent and all three children; omitted by default. |
| `point_size` | `float \| None` | Constant marker size on the three point layers; omitted by default. A `size` channel in `mapping` wins. |

**Raises:** `ValueError` if `axis_label_policy` is invalid or if any ion column
is missing from `data`.

### `plot_stiff(ca, mg, na_k, cl, hco3, so4, title="", figsize=(6, 6), fontsize=None)` (compatibility)

Builds a single stiff-diagram `FigureSpec` from one water analysis.

| Param | Type | Description |
| --- | --- | --- |
| `ca`, `mg`, `na_k`, `cl`, `hco3`, `so4` | `float` | Concentrations in meq/L (takes the max, picks a "nice" tick max from the built-in ladder). |
| `title` | `str` | Figure title. |
| `figsize` | `(float, float)` | Figure size. |
| `fontsize` | `float \| None` | Generic font-size fallback; omitted by default. |

Returns a `FigureSpec` with a `GeomPolygon` (filled, light blue, black
1.5-width edge) and a dashed `GeomLine` divider at x=0, plus `settings` that
declare named y ticks (`Mg²⁺`, `Ca²⁺`, `Na⁺+K⁺`), a `secondary_y` axis
(`SO₄²⁻`, `HCO₃⁻`, `Cl⁻`), absolute tick labels, and majortick styling.

---

*Next: [core.md](core.md) · [engine.md](engine.md) · [provider.md](provider.md) · [renderers.md](renderers.md) · [serialize.md](serialize.md) · [data.md](data.md) · [io.md](io.md)*