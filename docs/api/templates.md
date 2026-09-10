# API Reference — Templates

Templates bundle a configured set of [`Layer`](core.md#layers--specs)s, a
default settings dict, and (optionally) a coordinate system + name into one
reusable `FigureTemplate`. All builders return a fresh `FigureTemplate` and are
safe to use directly with `FigureEngine` / `render_template`.

```python
from geofig_engine.templates import (
    FigureTemplate,
    bivariate, boxplot_with_points, histogram, timeseries, pie, radar,
    isotope, npr_nnp, anp_agp, nagph_nag,
    build_piper_specs, plot_stiff,
)
```

## Contents

- [FigureTemplate](#figuretemplate)
- [Generic templates](#generic-templates)
- [Pie & radar](#pie--radar)
- [Hydrogeochemical templates](#hydrogeochemical-templates)
- [Spec builders](#spec-builders)

---

## FigureTemplate

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

Usage via the engine:

```python
specs = FigureEngine().build_specs_from_template(
    dataset=dataset,
    template=bivariate(mapping={"x": "x", "y": "y"}),
    settings={"figsize": (8, 6)},   # merged OVER template defaults
)
```

---

## Generic templates

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

These two functions do **not** return a `FigureTemplate` — they build
renderer-ready [`FigureSpec`](core.md#layers--specs) objects directly.

### `build_piper_specs(data, left_tri=("Ca", "Mg", "Na+K"), right_tri=("HCO3", "SO4", "Cl"), mapping=None, title="Piper Diagram", labels=None, axis_label_policy="parallel")`

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

**Raises:** `ValueError` if `axis_label_policy` is invalid or if any ion column
is missing from `data`.

### `plot_stiff(ca, mg, na_k, cl, hco3, so4, title="", figsize=(6, 6))`

Builds a single stiff-diagram `FigureSpec` from one water analysis.

| Param | Type | Description |
| --- | --- | --- |
| `ca`, `mg`, `na_k`, `cl`, `hco3`, `so4` | `float` | Concentrations in meq/L (takes the max, picks a "nice" tick max from the built-in ladder). |
| `title` | `str` | Figure title. |
| `figsize` | `(float, float)` | Figure size. |

Returns a `FigureSpec` with a `GeomPolygon` (filled, light blue, black
1.5-width edge) and a dashed `GeomLine` divider at x=0, plus `settings` that
declare named y ticks (`Mg²⁺`, `Ca²⁺`, `Na⁺+K⁺`), a `secondary_y` axis
(`SO₄²⁻`, `HCO₃⁻`, `Cl⁻`), absolute tick labels, and majortick styling.

---

*Next: [core.md](core.md) · [engine.md](engine.md) · [renderers.md](renderers.md) · [serialize.md](serialize.md) · [data.md](data.md) · [io.md](io.md)*