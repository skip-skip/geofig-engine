# API Reference — Core

The `geofig_engine.core` package defines the declarative model that describes
what a figure *is*. These classes are renderer-agnostic; they are resolved
into renderer-ready `FigureSpec` objects by the [engine](engine.md).

Imports used throughout this page assume:

```python
from geofig_engine import core as g
```

## Contents

- [Data model](#data-model) — Dataset, Dimension, DimensionSelector
- [Mappings](#mappings) — AttributeMapping, resolve_source
- [Iterators](#iterators) — DimensionIterator, expand, IteratorContext
- [Layers & Specs](#layers--specs) — Layer, LayerSpec, FigureSpec, build_spec, validate_figure_spec
- [Geoms](#geoms) — geometric marks and their channels
- [Stats](#stats) — statistical transformations
- [Scales](#scales) — data → visual domain transforms
- [Coords](#coords) — coordinate systems
- [Facets](#facets) — panel splitting
- [Links](#links) — LinkTransform, label_rotation
- [Axis & plot settings](#axis--plot-settings) — AxisFormat, parse_axis_settings, flat settings keys
- [Secondary axes](#secondary-axes) — SecondaryAxis, parse_secondary_settings

---

## Shared types (`geofig_engine.utils.typing`)

| Name | Value / meaning |
| --- | --- |
| `SourceType` | `DimensionSelector \| str \| Sequence[str] \| Any` — anything a mapping channel may point at (a selector, a column name, a list of column names, or a constant). |
| `Selector` | `str \| Sequence[str] \| Dict[str, Any]` — selector shorthand used by `DimensionSelector`. |
| `DimensionsMap` | `Dict[str, Dimension]`. |
| `Channel` (enum) | Visual channels whose `.value` matches mapping keys: `x`, `y`, `x2`, `y2`, `color`, `marker`, `size`, `style`, `alpha`, `width`. |
| `ALLOWED_TARGETS` | `{"x","y","x2","y2","color","marker","size","style","alpha","width"}` — valid `AttributeMapping.target` values. |
| `VISUAL_ATTRIBUTES` | Alias of `ALLOWED_TARGETS`. |
| `Mapping` (enum) | Declares each semantic mapping (`X`, `Y`, `X2`, `Y2`, `COLOR`, `MARKER`, `SIZE`, `STYLE`, `ALPHA`, `WIDTH`, `OXYGEN_18`, `DEUTERIUM`) with its `MappingData` (name, channel, allowed types, alignment requirement, required flag). |
| `MappingData` | Frozen dataclass: `name`, `channel`, `allowed_types`, `enforce_alignment`, `required`. |
| Validation constants | `MAX_TEMPLATE_NAME_LENGTH = 100`, `MAX_DIMENSION_NAME_LENGTH = 100`, `MAX_STRING_LENGTH = 1000`. |

The geom-level channel enum is `geofig_engine.core.geom.Channel` (see
[Geoms](#geoms)); it adds `label`, `func`, `ymin`, `ymax`, `xmin`, `xmax`,
`angle`, and `bbox` beyond the visual-channel enum above.

---

## Data model

### `Dataset` (dataclass)

```python
@dataclass
class Dataset:
    dataframe: pd.DataFrame
    key_column: str
    dimensions: dict[str, Dimension] = {}
```

`__post_init__` deep-copies the dataframe and runs `validate_schema()`.

| Attribute | Type | Description |
| --- | --- | --- |
| `dataframe` | `pd.DataFrame` | The tabular data. Deep-copied on init; column names must be unique. |
| `key_column` | `str` | Column used as a row identifier. Must exist. |
| `dimensions` | `dict[str, Dimension]` | Name → `Dimension` metadata. Keys must be existing dataframe columns; `Dimension.name` must match the key. |

**Methods:**

| Signature | Returns | Notes |
| --- | --- | --- |
| `Dataset.load_dataset(filepath, key_column="GENERATED_KEY", label_rows=1, sheet_name=0)` | `Dataset` | Loads `.xlsx` (via openpyxl, `data_only=True`, merged cells in label rows are expanded) or `.csv`. Layout: `label_rows` label rows, then a header row, then data. Fails with `FileNotFoundError` for missing files and `ValueError` for unsupported suffixes. Each column becomes a `Dimension` whose labels are the non-empty label-row values. If `key_column` is absent from the data it is added as `range(len(data))`. |
| `validate_schema()` | `None` | Raises `ValueError` for duplicate columns, missing/non-string `key_column`, dimensions naming missing columns, or dimension name mismatches. |
| `get_column(name)` | `pd.Series` | Copy of a column; `KeyError` if missing. |
| `select_columns(names)` | `pd.DataFrame` | Copy of the selected columns; `KeyError` if any are missing. |
| `query_dimensions(label, value)` | `list[str]` | Column names whose dimension has `label` with value `value`. |
| `get_dimension_names()` | `dict_keys` | Keys of `dimensions`. |
| `get_all_labels()` | `dict[str, Any]` | Union of all dimension labels. |
| `filter_rows(mask)` | `Dataset` | `mask` is a boolean `pd.Series` (index must match) or a boolean sequence. Returns a new `Dataset` with the filtered frame (dimensions shared). |
| `unique_values(dimension_name)` | `pd.Index` | Unique, non-null values of a column, named after the column. |
| `has_dimension(name)` | `bool` | Whether `name` is a dimension. |

**Properties:** `dimension_names` (`tuple[str, ...]`), `shape`, and `__len__`.

### `Dimension` (frozen dataclass)

```python
@dataclass(frozen=True)
class Dimension:
    name: str
    labels: dict[str, Any] = {}
```

Validates `name` is a string and `labels` is a `dict` with string keys.

| Method | Signature | Returns |
| --- | --- | --- |
| `get_label(key, default=None)` | `get_label(self, key: str, default=None)` | The label value for `key` or `default`. |
| `has_label(key)` | `has_label(self, key: str)` | Whether `key` is present. |

### `DimensionSelector` (frozen dataclass)

```python
@dataclass(frozen=True)
class DimensionSelector:
    selector: Selector  # str | Sequence[str] | dict[str, Any]
```

A `Selector` is one of:

- a string column name,
- a sequence of column names,
- a `{label: value}` attribute dict matching dimensions by metadata.

Validated in `__post_init__` (raises `TypeError` for invalid forms).

| Method | Signature | Returns |
| --- | --- | --- |
| `resolve(dataset)` | `resolve(self, dataset: Dataset)` | `list[str]` of matching column names. `str` resolves to `[name]` (`KeyError` if absent); a sequence resolves each name (`KeyError` if any absent); a dict resolves dimensions whose labels match all `{key: value}` pairs (`ValueError` if none match). |
| `is_explicit()` | `is_explicit(self)` | `True` for string / sequence selectors (name-based). |
| `is_metadata_based()` | `is_metadata_based(self)` | `True` for dict selectors (attribute-based). |

### `ColumnSelector(DimensionSelector)`

Trivial subclass of `DimensionSelector` used to select *columns to iterate
over rather than values* in iterator mode (see [Iterators](#iterators)).

---

## Mappings

### `AttributeMapping` (frozen dataclass)

```python
@dataclass(frozen=True)
class AttributeMapping:
    target: str   # one of ALLOWED_TARGETS
    source: SourceType
```

Validates on construction via `validate_attribute_mapping(self)`.

### `validate_attribute_mapping(mapping)`

Raises `ValueError` if `target` is not in `ALLOWED_TARGETS`, or `TypeError` if a
`list` source contains non-strings or a plain `dict` is passed as `source`
(use a `DimensionSelector` for metadata selection).

### `resolve_source(source, dataset, strict=False, context=None)`

Resolves a `SourceType` to concrete columns or a constant.

| Param | Type | Description |
| --- | --- | --- |
| `source` | `SourceType` | `DimensionSelector`, `str`, `list[str]`, or a constant. |
| `dataset` | `Dataset` | Source of columns/dimensions. |
| `strict` | `bool` | If `True`, a string that is not a column raises `KeyError`; if `False` (default) it is treated as a constant. |
| `context` | `dict[str, Any] \| None` | Optional string-formatting placeholders applied to string/list sources (silently skipped if a key is missing). |

**Returns:** `DimensionSelector` → resolved column names; `str` → `[col]` if a
column else the constant (or `KeyError` in `strict` mode); `list[str]` →
resolved list (`KeyError` if any column missing and non-strict formatting
applies); any other value → returned as-is.

**Raises:** `ValueError` if a `DimensionSelector` matches nothing; `KeyError`
for missing columns in strict/list cases.

---

## Iterators

`DimensionIterator` drives multi-figure expansion: each combination of
dimension values (or of selected columns) produces a filtered `IteratorResult`
feeding one figure.

### `DimensionIterator` (frozen dataclass)

```python
class DimensionIterator.Mode(Enum):
    VALUE = "value"        # iterate over unique row values of the selected columns
    DIMENSION = "dimension"  # iterate over the selected column names themselves

@dataclass(frozen=True)
class DimensionIterator:
    channel: str                    # context key under which iteration values are stored
    dimensions: Sequence[str] | dict[str, Any]
    mode: Mode = Mode.DIMENSION
```

`DIMENSION` mode builds a `ColumnSelector` from `dimensions` and iterates the
resolved *column names*; `VALUE` mode builds a `DimensionSelector` and
iterates the unique *values* across the resolved columns. For value mode the
`dimensions` argument may also be a `{label: value}` metadata dict.

### `IteratorContext` (frozen dataclass)

```python
@dataclass(frozen=True)
class IteratorContext:
    values: dict[str, Any]
    def get(self, key, default=None): ...
```

`__repr__` renders `IteratorContext(empty)` or sorted `k=v` pairs.

### `IteratorResult` (frozen dataclass)

```python
@dataclass(frozen=True)
class IteratorResult:
    subset_df: pd.DataFrame
    context: IteratorContext
    iterator_key: tuple[str, ...]
```

### `expand(dataset, iterators=None)`

Generates every combination of iteration values (deterministic: selector keys
sorted, values sorted). `iterators=None` produces a single result over the
full dataset with an empty context and empty `iterator_key`.

| Param | Type | Description |
| --- | --- | --- |
| `dataset` | `Dataset` | Source dataset. |
| `iterators` | `Sequence[DimensionIterator] \| None` | Iterators to expand over. |

**Returns:** `list[IteratorResult]`. Each result's `subset_df` is the rows
matching that context (value mode: rows where *any* of the selector's columns
equals the context value; column mode: no row filtering, the columns are
selected instead).

**Raises:** `ValueError` if a `DimensionSelector` matches nothing; `KeyError`
for unknown columns.

### `get_iterator_columns(dataset, selectors)`

Resolves `{name: selector}` where each selector is a `DimensionSelector`,
`str`, or `list[str]`, returning `{name: [columns]}`.

### `generate_contexts(dataset, iterator_columns, column_selector_keys=None)`

Returns the sorted `list[IteratorContext]` of all combinations.

### `filter_by_context(df, context, iterator_columns, column_selector_keys=None)`

Filters rows to those matching the context for value iterators (skips column
iterators). Accepts the modern dict form or the legacy list-of-column-lists
form of `iterator_columns`.

---

## Layers & Specs

### `Layer` (frozen dataclass)

```python
@dataclass(frozen=True)
class Layer:
    geom: Geom
    stat: Stat = StatIdentity()
    mapping: dict[str, SourceType] = {}
    scales: dict[str, Scale] | None = None
    data_override: str | None = None
    zorder: int | None = None
    xlim: tuple[float, float] | None = None
    ylim: tuple[float, float] | None = None
```

A `Layer` is the declarative binding of one mark to its data sources.
`__post_init__` type-checks every field (`TypeError` on mismatch; `xlim` /
`ylim` must be 2-tuples, `zorder` an `int`).

### `LayerSpec` (frozen dataclass)

```python
@dataclass(frozen=True)
class LayerSpec:
    geom: Geom
    stat: Stat
    visual_mapping: dict[str, Any]   # channel → pd.Series or constant
    data_override: str | None = None
    zorder: int | None = None
    xlim: tuple[float, float] | None = None
    ylim: tuple[float, float] | None = None
```

The *resolved* layer: all channels have been converted to concrete
`pd.Series` (or constants) and scales applied. Produced by the engine, not
declared directly.

### `FigureSpec` (frozen dataclass)

```python
@dataclass(frozen=True)
class FigureSpec:
    data: pd.DataFrame
    mappings: dict[str, Any]
    settings: dict[str, Any]
    context: dict[str, Any]
    template_name: str
    iterator_key: tuple[str, ...] = ()
    layers: list[LayerSpec] = []
    coord: Coord = CoordCartesian()
    facet: Facet = FacetNull()
    children: tuple[FigureSpec, ...] = ()
    transform: LinkTransform = LinkTransform()
```

The concrete, renderer-agnostic plotting instruction. All selectors have been
resolved to columns and all data references validated. `children` are linked
axes — each is a self-contained `FigureSpec` with its own `coord`, `transform`,
`layers`, and `settings`; depth is limited to 1 (children may not have
children). `transform` maps this spec's local space into parent world space.

`__post_init__` runs `validate_figure_spec(self)`.

### `validate_figure_spec(spec)`

Validates a `FigureSpec`:
- `data` is a DataFrame; `mappings`, `settings`, `context` are dicts.
- Each mapping value is either a `list[str]` of existing columns (non-empty;
  `KeyError` via `validate_columns_exist`) or a constant — a plain dict (that
  isn't a `DimensionSelector`) raises `TypeError`.
- `template_name` is a non-empty string; `iterator_key` is a tuple of strings.
- Axis and secondary-axis settings are validated (see below).
- `children` must be a tuple of `FigureSpec` with no nested children.
- `transform` must be a `LinkTransform` when not `None`.

**Raises:** `TypeError` / `ValueError` as described.

### `build_spec(data, mappings, settings, context, template_name, iterator_key=(), layers=None, coord=None, facet=None, children=None, transform=None)`

Factory that constructs and validates a `FigureSpec`. `coord`, `facet`,
`children`, and `transform` default to `CoordCartesian()`, `FacetNull()`,
`()`, and `LinkTransform()` respectively.

### `extract_data_for_mapping(spec, mapping_key)`

Returns the data behind a mapping key:
- single-column mapping → its `pd.Series`;
- multi-column mapping → `pd.concat(series_list, ignore_index=True)`;
- constant mapping → the constant;
- missing key → `None`.

---

## Geoms

`Channel` enum (`geofig_engine.core.geom.Channel`): `x`, `y`, `y2`, `color`,
`marker`, `size`, `style`, `alpha`, `width`, `label`, `func`, `ymin`, `ymax`,
`xmin`, `xmax`, `angle`, `bbox`.

`Geom` base (frozen dataclass): `name: str`, `required_channels: tuple[str, ...]`,
`optional_channels: tuple[str, ...]`. Validates that channel names are valid
`Channel` values. Geoms are purely declarative — no rendering logic.

| Geom | `name` | Constructor | Required channels | Optional channels |
| --- | --- | --- | --- | --- |
| `GeomPoint` | `point` | `(jitter=0.0, dodge=0.0)` | `x`, `y` | `color`, `marker`, `size`, `alpha` |
| `GeomLine` | `line` | `()` | `x`, `y` | `color`, `style`, `width`, `alpha` |
| `GeomFunctionLine` | `function_line` | `(func="", label=None)` | `x` | `color`, `style`, `width`, `alpha`, `label` |
| `GeomBar` | `bar` | `(position="identity")` — `position` ∈ `identity`/`stack`/`fill` | `x`, `y` | `color`, `alpha`, `width`, `label` |
| `GeomArea` | `area` | `()` | `x`, `y` | `color`, `alpha` |
| `GeomPolygon` | `polygon` | `(edgecolor="black", edgealpha=None, edgewidth=0.5, edgestyle="-")` — validates all values | `x`, `y` | `color`, `alpha` |
| `GeomRibbon` | `ribbon` | `()` | `x`, `ymin`, `ymax` | `color`, `alpha` |
| `GeomText` | `text` | `()` | `x`, `y`, `label` | `color`, `size`, `alpha`, `angle`, `bbox` |
| `GeomErrorbar` | `errorbar` | `()` | `x`, `y`, `ymin`, `ymax` | `color`, `width`, `alpha` |
| `GeomBox` | `box` | `(showfliers=True, showmeans=False, show_n=False, min_box_n=1, is_horizontal=False, sort_mode="none", smush=False, box_width=0.8)` | `x`, `y` | `color`, `alpha` |
| `GeomViolin` | `violin` | `(show_medians=True, sort_mode="none", smush=False)` | `x`, `y` | `color`, `alpha` |
| `GeomStepLine` | `step_line` | `(where="pre")` | `x`, `y` | `color`, `style`, `width`, `alpha` |
| `GeomAbline` | `abline` | `(slope=None, intercept=0.0, x1=None, y1=None, x2=None, y2=None)` — exactly one of slope+intercept or two-point; raises `ValueError` otherwise | — | `color`, `style`, `width`, `alpha` |
| `GeomHSpan` | `hspan` | `()` | `ymin`, `ymax` | `color`, `alpha` |
| `GeomVSpan` | `vspan` | `()` | `xmin`, `xmax` | `color`, `alpha` |
| `GeomRect` | `rect` | `()` | `xmin`, `xmax`, `ymin`, `ymax` | `color`, `alpha` |

**Notes:**

- `GeomAbline` form 1: `slope`+`intercept` (y = mx+b). Form 2: bounded
  segment `x1,y1,x2,y2`. `GeomHSpan`/`GeomVSpan`/`GeomRect` bounds are
  provided through the mapping's `ymin`/`ymax`/`xmin`/`xmax` channels.
- `GeomFunctionLine` renders `func` as an expression line over the data `x`
  values (used by isotope reference lines); `label` can supply the legend
  entry.
- `GeomBox`'s `sort_mode` ("none"/"asc"/"desc") and `smush` control group
  ordering/spacing; `show_n` appends counts to category labels; `min_box_n`
  drops groups below the threshold. `box_width` is the dodged box unit width
  used to align jittered points.

---

## Stats

`Stat` base (frozen dataclass): `name: str`, `params: dict`. Subclasses
implement `compute(data: pd.DataFrame) -> pd.DataFrame`.

| Stat | `name` | Constructor | `compute` behavior |
| --- | --- | --- | --- |
| `StatIdentity` | `identity` | `()` | Returns data unchanged. |
| `StatFn` | `fn` | `(func=None, params=None)` | Applies `func(data)`; passthrough if `func` is `None`. |
| `StatBin` | `bin` | `(column=None, bins=10, range=None, density=False, cumulative=False)` | Bins `column` via `np.histogram`; returns `x` (bin centers), `y` (counts or densities), `width`. Passthrough if `column` missing. |
| `StatCount` | `count` | `()` | Passthrough (placeholder). |
| `StatSmooth` | `smooth` | `(method="loess", span=0.75, degree=2)` | Passthrough (smoothing not yet wired). |
| `StatSum` | `sum` | `(column=None, group=None, sort=True, show_percent=False, show_count=False, show_name=True)` | Groups `group` summing `column`; emits `label`, `y`, `width`, `x` (angular starts derived for pie wedges). Label parts compose name / `n=N` / `NN.N%`. Passthrough if either column missing. |
| `StatPieLabels` | `pie_labels` | `(column=None, group=None, show_percent=True, show_count=False, label_distance=1.3, sort=True)` | Emits `x` (wedge angle), `y` (`label_distance`), `label_text` (percent/count/name). |
| `StatRadar` | `radar` | `(shared_axes=True, x_col="x", y_col="y", color_col=None)` | Copies `x_col`/`y_col` into `x`/`y`, adds `x_label`, optionally sorts by `color_col`. |
| `StatIonFractions` | `ion_fractions` | `(cations=((Ca,), (Mg,), (Na, K)), anions=((HCO3, CO3), (SO4,), (Cl,)))` | Sums slot groups per row, normalizes to fractions, and emits `cation_f0/f1/f2`, `anion_f0/f1/f2`, `dia_anion_pct`, `dia_cation_pct` (see note). |

**Notes:**

- `StatIonFractions` slot order is `(bottom-left, apex, bottom-right)` per the
  ternary convention. Rows with zero total become all-zero fractions. Inputs
  must already be in meq/L — no unit conversion is performed.
- `StatSum`/`StatPieLabels` require both `column` and `group` to exist before
  transforming.

---

## Scales

`Scale` base (frozen dataclass): `name: str`, `params: dict`, `domain`,
`range`. Subclasses implement `transform(values)` and `invert(values)`,
applied to channels while resolving layers (before rendering).

| Scale | `name` | Constructor | `transform` behavior | `invert` |
| --- | --- | --- | --- | --- |
| `ScaleContinuous` | `continuous` | `(trans="identity", domain=None, range=None)` — `trans` ∈ `identity`/`log`/`sqrt`/`reverse` | `log` → `np.log`, `sqrt` → `np.sqrt`, `reverse` → negate; else identity | `exp`, square, negate, identity |
| `ScaleOrdinal` | `ordinal` | `(palette=None, domain=None, range=None)` | Cycles `palette` over unique values (`val % len(palette)`) | Identity |
| `ScaleConstant` | `constant` | `(value=None)` | Broadcasts `value` | Identity |
| `ScaleDateTime` | `datetime` | `(fmt="%Y-%m-%d", domain=None, range=None)` | Identity | Identity |
| `ScaleNormalize` | `normalize` | `(range_min=0.0, range_max=1.0)` — raises `ValueError` if `range_min >= range_max` | Min-max normalizes to `[range_min, range_max]`; degenerate data → `range_min` | Identity |

---

## Coords

`Coord` base (frozen dataclass): `name: str`, `params: dict`. Optional
`aspect_ratio() -> float | None` and
`transform_visual_mapping(visual_mapping, geom)` (a no-op by default).

| Coord | `name` | Constructor | Behavior |
| --- | --- | --- | --- |
| `CoordCartesian` | `cartesian` | `()` | Standard x/y axes. |
| `CoordFlipped` | `flipped` | `()` | Swapped x/y axes. |
| `CoordPolar` | `polar` | `(theta="x", start=0.0, end=360.0)` | `aspect_ratio` = 1.0; converts categorical `x` series into angular positions evenly spaced on `[0, 2π)`. |
| `CoordFixed` | `fixed` | `(ratio=1.0)` — must be positive | `aspect_ratio` = `ratio`. |
| `TernaryCoord` | `ternary` | `(channels=("a","b","c"), handedness="left", labels=None)` | See below. |

### `TernaryCoord`

Projects three fraction channels into local x/y on an equilateral triangle.
`channels` order is `(apex, bottom-left, bottom-right)`; `handedness="right"`
mirrors horizontally. `labels` (3-strings) are display labels for the
vertices, defaulting to `channels`. `transform_visual_mapping` requires all
three channels as `pd.Series`, normalizes rows by their sum (zero-total →
NaN), and rewrites them into `x`/`y`.

Helpers:

- `TERNARY_HEIGHT` — `sqrt(3)/2`, the triangle's height with unit base.
- `ternary_project(a, b, c, handedness="left")` — projects fraction arrays
  onto local coordinates `(x, y)` (`x = 0.5a + c`, `y = TERNARY_HEIGHT · a`,
  mirrored when `handedness="right"`, rows normalized by row sum).

---

## Facets

`Facet` base (frozen dataclass): `name`, `by: tuple[str, ...]`,
`scales` ∈ `fixed`/`free`/`free_x`/`free_y`, `params`. Subclasses implement
`split(dataset) -> list[(subset_df, context)]`.

| Facet | `name` | Constructor | `split` behavior |
| --- | --- | --- | --- |
| `FacetNull` | `null` | `()` | Single panel over the whole dataframe with empty context. |
| `FacetWrap` | `wrap` | `(by, ncol=0, nrow=0, scales="fixed")` — `by` is `str` or sequence | Groupby `by` (sorted); one panel per group with `{col: value}` context. |
| `FacetGrid` | `grid` | `(row, col, scales="fixed")` | Two-key groupby; context carries both the row and column values. |

`split` returns panels with no data for empty groups (groupby.dropna is not
applied); `ncol`/`nrow` of `0` mean "auto".

---

## Links

### `LinkTransform` (frozen dataclass)

```python
@dataclass(frozen=True)
class LinkTransform:
    ops: tuple[tuple[str, tuple | float], ...] = ()
```

Fluent, orderable affine placement of a linked axis in parent world space.
Operations are applied to points in call order (first-called op first); the
matrix is the left-multiplication `M = last ∘ … ∘ first`, so for a point `p`
the transform is `M @ p`. Every fluent method returns a **new** `LinkTransform`
(the receiver is unchanged).

| Method | Signature | Description |
| --- | --- | --- |
| `translate` | `translate(tx, ty=0.0)` | Translate by `(tx, ty)`. |
| `scale` | `scale(sx, sy=None)` | Scale by `(sx, sy)`; `sy` defaults to `sx` (uniform). |
| `rotate` | `rotate(deg)` | Rotate by `deg` degrees CCW. |
| `matrix` | `matrix()` | Returns the 3×3 homogeneous matrix. |
| `transform_point` | `transform_point(xy)` | Maps one local point to world space. |
| `transform_points` | `transform_points(pts)` | Maps an `(n, 2)` array; raises `ValueError` for other shapes. |
| `transform_direction` | `transform_direction(vec)` | Applies only the linear part (rotate+scale). |
| `to_dict` | `to_dict()` | JSON-compatible `{"operations": [[kind, params], …]}`. |
| `from_dict` | `from_dict(data)` (classmethod) | Reconstructs a `LinkTransform` from its dict form. |

Example (Piper diamond: rotate 45°, squash y, then center):

```python
LinkTransform().rotate(45.0).scale(0.0035, 0.0061).translate(0.5, 0.0)
```

### `label_rotation(local_vec, matrix, policy="upright")`

Computes the rotation (degrees) for a label attached to a transformed axis.
`policy="upright"` (default) always returns `0.0`; `policy="parallel"`
returns the transformed tangent direction's angle (the linear part only), then
flips angles outside ±90° so the label reads rightside-up. Vertical labels
(±90°) are not flipped. Raises `ValueError` for an unknown policy.

---

## Axis & plot settings

The axis model (`AxisFormat`) is validated, matplotlib-free, and consumed by
both the top-level figure path and linked-axis child frames. It is populated
from the `FigureSpec.settings` dict by `parse_axis_settings`.

### `AxisFormat` (frozen dataclass)

Common fields:

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `title` | `str` | `""` | Figure/frame title. |
| `xlabel`, `ylabel` | `str \| None` | `None` | Axis label texts. |
| `limits` | `tuple[(xlim), (ylim)] \| None` | `None` | Data limits, each a pair of floats. |
| `grid` | `bool \| None` | `None` | Grid on/off. |
| `grid_step` | `float \| None` | `None` | Grid line spacing. |
| `tick_step` | `float \| None` | `None` | Tick spacing. |
| `axis_arrows` | `bool \| None` | `None` | Draw axis-direction arrows. |
| `x_reversed`, `y_reversed` | `bool` | `False` | Reverse an axis. |
| `label_policy` | `str` | `"upright"` | `"upright"` or `"parallel"`. |
| `axis_label_policy` | `str \| None` | `None` | Overrides axis-label rotation; else inherits `label_policy`. |
| `tick_label_policy` | `str \| None` | `None` | Overrides tick-label rotation; else inherits `label_policy`. |
| `xscale`, `yscale` | `str \| None` | `None` | Scale names (e.g. `"linear"`). |
| `time_format` | `str \| None` | `None` | Datetime tick format (e.g. `"%Y-%m-%d"`). |
| `tick_format` | `str` | `":g"` | Format-spec for numeric tick labels. |
| `abs_ticks` | `bool` | `False` | Absolute-value tick labels. |
| `tick_labels` | `dict[float, str]` | `{}` | Named `{position: label}` tick labels. |
| `x_abs_ticks`, `y_abs_ticks` | `bool \| None` | `None` | Per-axis absolute-tick overrides. |
| `x_tick_labels`, `y_tick_labels` | `dict \| None` | `None` | Per-axis named-tick overrides. |

Appearance-preserving style knobs (all default to the current rendered look):

| Field | Type | Default / meaning |
| --- | --- | --- |
| `fontsize` | `float \| None` | Generic font size fallback. |
| `tick_fontsize`, `axis_label_fontsize`, `title_fontsize`, `xlabel_fontsize`, `ylabel_fontsize`, `suptitle_fontsize`, `legend_fontsize`, `facet_title_fontsize` | `float \| None` | Per-element font sizes. |
| `grid_style` | `dict` | `{"color": "gray", "linewidth": 0.3, "linestyle": ":"}` |
| `frame_linewidth` | `float` | `1.0` |
| `label_offset` | `float \| None` | Offset of axis labels from the frame. |
| `axis_arrow_offset` | `float \| None` | Offset of axis arrows. |
| `majortick_length` | `float \| None` | Major-tick line length in local units; `None` disables. |
| `majortick_offset` | `float \| None` | `0` = wholly exterior, `1` = wholly interior, `0.5` = bisected. |
| `majortick_width`, `majortick_color` | `float \| None`, `str \| None` | Major-tick line styling. |
| `options` | `dict` | `{}` | Per-coordinate extension (e.g. polar toggles). |

**Methods:**

| Method | Signature | Returns |
| --- | --- | --- |
| `xlim` / `ylim` | property | `limits[0]` / `limits[1]` or `None`. |
| `coord_grid_step` | property | `grid_step` or `0.2`. |
| `coord_tick_step` | property | `tick_step`, else `grid_step`, else `0.2`. |
| `effective_polar_step` | property | `grid_step` or `0.2`. |
| `option(key, default=None)` | `option(self, key, default=None)` | `options.get(key, default)`. |
| `show_arrows()` | `show_arrows(self)` | `bool(axis_arrows)`. |
| `resolve_fontsize(kind)` | `resolve_fontsize(self, kind)` | Per-element knob → generic `fontsize` → built-in default. `kind` ∈ `title`, `axis_label`, `xlabel`, `ylabel`, `tick`, `suptitle`, `legend`, `facet_title`. |
| `axis_label_policy_eff()` | `axis_label_policy_eff(self)` | `axis_label_policy` or `label_policy`. |
| `tick_label_policy_eff()` | `tick_label_policy_eff(self)` | `tick_label_policy` or `label_policy`. |
| `abs_ticks_eff(axis_key)` | `abs_ticks_eff(self, axis_key)` | `x_abs_ticks`/`y_abs_ticks` or shared `abs_ticks`. |
| `tick_labels_eff(axis_key)` | `tick_labels_eff(self, axis_key)` | `x_tick_labels`/`y_tick_labels` or shared `tick_labels`. |

### `parse_axis_settings(settings, coord=None)`

Reads flat, top-level `settings` keys into a validated `AxisFormat`.

| Param | Type | Description |
| --- | --- | --- |
| `settings` | `Mapping \| None` | A spec's `settings` dict. |
| `coord` | `Coord \| None` | Informational context for coord-specific defaults. |

**Returns:** validated `AxisFormat`. **Raises:** `ValueError` for malformed
limits, non-positive `grid_step`/`tick_step`, invalid policies/formats.

### Flat settings key reference

All of these are accepted directly under `FigureSpec.settings` (the legacy
flat style); `AxisFormat` fields are populated in the table above. Coord
extension keys: polar toggles `hide_spine`, `hide_angular_ticks`,
`hide_angular_labels`, `hide_radial_labels`, `hide_radial_ticks`,
`polar_tick_labels` are surfaced through `AxisFormat.options`.

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `figsize` | `(float, float)` | template-dependent | Figure size in inches. |
| `title` (or `figname`) | `str` | `""` | Title. |
| `xlabel` / `ylabel` | `str` | `None` | Axis labels. |
| `xlim` / `ylim` | `(float, float)` | `None` | Axis limits. Must be set as a pair. |
| `grid` | `bool` | template-dependent | Grid on/off. |
| `grid_step` | `float` | `0.2` | Grid spacing. |
| `tick_step` | `float` | grid_step → `0.2` | Tick spacing. |
| `axis_arrows` | `bool` | `False` | Draw direction arrows. |
| `x_reversed` / `y_reversed` | `bool` | `False` | Reverse axis. |
| `label_policy` | `"upright" \| "parallel"` | `"upright"` | Label rotation policy. |
| `axis_label_policy` / `tick_label_policy` | `"upright" \| "parallel" \| None` | `None` | Independent label/tick rotation. |
| `xscale` / `yscale` | `str` | `None` | Scale names (`"linear"`, …). |
| `time_format` | `str` | `None` | Datetime tick format. |
| `tick_format` | `str` | `":g"` | Numeric tick format-spec. |
| `abs_ticks` | `bool` | `False` | Absolute tick labels. |
| `tick_labels`, `x_tick_labels`, `y_tick_labels` | `dict` | `{}` | Named tick labels. |
| `fontsize` and `*_fontsize` knobs | `float` | `None` | Font sizes (see `AxisFormat`). |
| `label_offset` | `float` | `None` | Axis-label offset. |
| `axis_arrow_offset` | `float` | `None` | Arrow offset. |
| `majortick_length` / `majortick_offset` / `majortick_width` / `majortick_color` | — | `None` | Major-tick styling. |
| `hide_spine`, `hide_angular_ticks`, `hide_angular_labels`, `hide_radial_labels`, `hide_radial_ticks`, `polar_tick_labels` | `bool` | template-dependent | Polar toggles (surfaced via `options`). |
| `secondary_x` / `secondary_y` | `dict` | `None` | Secondary-axis declarations (see below). |

---

## Secondary axes

Secondary axes add extra scales along a child frame's upper/right (x) or
right/left (y) edges, drawn as structured entries under `secondary_x` /
`secondary_y` in `FigureSpec.settings`:

```python
settings = {
    "xlim": (0, 100), "ylim": (0, 100),
    "secondary_x": {
        "range": [100, 0],        # secondary data scale
        "tick_step": 20,          # default = primary tick_step
        "label_policy": "upright",# default = primary label_policy
        "position": "top",        # default "top"; alt "bottom"
        "label": "Anions (%)",    # optional axis title
    },
    "secondary_y": {"range": [100, 0], "position": "right", ...},
}
```

A secondary value maps **linearly** onto the child's primary local-frame
range (`xlim`/`ylim`), so `[100, 0]` on a `[0, 100]` primary yields the
reversed/complement scale.

### `SecondaryAxis` (frozen dataclass)

```python
@dataclass(frozen=True)
class SecondaryAxis:
    orientation: str            # "x" (top/bottom edge) or "y" (right/left edge)
    range: tuple[float, float]
    tick_step: float
    label_policy: str
    position: str
    label: str
    primary_range: tuple[float, float]
    axis_label_policy: str | None = None
    tick_label_policy: str | None = None
    abs_ticks: bool = False
    tick_labels: dict[float, str] = {}
    majortick_length: float | None = None
    majortick_offset: float | None = None
    majortick_width: float | None = None
    majortick_color: str | None = None
```

Validated in `__post_init__` (non-degenerate ranges, positive `tick_step`,
valid policies/positions, `majortick` ranges).

**Methods:**

| Method | Signature | Returns |
| --- | --- | --- |
| `fwd` | property | Map a primary (local) value to secondary units. |
| `inv` | property | Map a secondary value to the primary (local) coordinate. |
| `tick_values` | `tick_values(self)` | Secondary tick positions; uses `tick_labels` positions when set, else interior numeric ticks at `tick_step`. |
| `tick_coordinates` | `tick_coordinates(self)` | `[(tick_value, local_coord), …]`. |
| `axis_label_policy_eff` | `axis_label_policy_eff(self)` | `axis_label_policy` or `label_policy`. |
| `tick_label_policy_eff` | `tick_label_policy_eff(self)` | `tick_label_policy` or `label_policy`. |

### `parse_secondary_settings(settings, *, xlim=None, ylim=None, defaults=None)`

Reads `secondary_x`/`secondary_y` declarations into validated
`SecondaryAxis` instances.

| Param | Type | Description |
| --- | --- | --- |
| `settings` | `Mapping \| None` | The child spec's `settings`. |
| `xlim`, `ylim` | `tuple[float, float] \| None` | Local-frame ranges; else read from `settings` (`xlim`/`ylim`) or default to `(0, 1)`. |
| `defaults` | `Mapping \| None` | Fallback dict for inherited values (`tick_step`, `label_policy`, `axis_label_policy`, `tick_label_policy`, `abs_ticks`, `tick_labels`, majortick knobs). Per-axis primaries may pass `x_abs_ticks`/`y_abs_ticks` and `x_tick_labels`/`y_tick_labels`. |

**Returns:** `dict[str, SecondaryAxis]` keyed by orientation. Absent
declarations are skipped; malformed ones raise `ValueError`.

### `linear_mapping(primary, secondary)`

Returns `(fwd, inv)` affine maps between *primary* and *secondary* ranges.
Requires invertible (non-degenerate) ranges; `fwd` maps primary → secondary,
`inv` maps secondary → primary.

---

*Next: [Engine](engine.md) · [Templates](templates.md) · [Renderers](renderers.md) · [Serialization](serialize.md) · [Data](data.md) · [IO](io.md)*