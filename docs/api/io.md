# API Reference — IO

`geofig_engine.io` provides geo/distance helpers, deterministic marker-palette
generation, EQuIS flat/cross-tab conversion, SI-prefix unit normalization,
column-level parsing/binning utilities, and a small preprocessing pipeline.

```python
from geofig_engine.io import (
    haversine, path_distance,
    gen_markers, gen_markers_series,
    Pipeline, PipelineStep,
    equisflat_to_sample_df, sample_df_to_equisflat, equis_crosstab_to_flat,
    equisflat_normalize_units, SI_PREFIXES,
    ecesis_to_sample_df, create_bins,
)
from geofig_engine.io.markers import gen_markers_cross_grouping, DEFAULT_MARKERS, DEFAULT_PALETTE
```

## Contents

- [Geo helpers](#geo-helpers)
- [Geo web sources](#geo-web-sources)
- [Markers](#markers)
- [Preprocessing pipeline](#preprocessing-pipeline)
- [EQuIS conversion](#equis-conversion)
- [Unit normalization](#unit-normalization)
- [Column utilities](#column-utilities)

---

## Geo helpers

### `haversine(lon1, lat1, lon2, lat2)`

```python
def haversine(
    lon1: float | pd.Series,
    lat1: float | pd.Series,
    lon2: float | pd.Series,
    lat2: float | pd.Series,
) -> float | pd.Series:
```

Great-circle distance in **kilometers** (Earth radius 6371.0 km) between two
points or, when passed series, element-wise between two coordinate lists.

### `path_distance(lon, lat, cumulative=True)`

```python
def path_distance(lon: pd.Series, lat: pd.Series, cumulative: bool = True) -> pd.Series:
```

Distance along a lon/lat path.

| Param | Type | Description |
| --- | --- | --- |
| `lon`, `lat` | `pd.Series` | Coordinates in path order. |
| `cumulative` | `bool` | `True`: cumulative distance from the start (first entry is 0). `False`: per-segment distance (first entry 0). |

**Returns:** a `pd.Series` in kilometers with the same index. A path of fewer
than 2 points returns all zeros.

---

## Geo web sources

The `site_map` overlay stack uses two standalone io modules that fetch web
data without geospatial stack dependencies:

- [DEM access](dem.md) — terrarium elevation tiles for default-on contours.
- [Stream access](streams.md) — USGS `NHDPlus_HR` polylines for default-on
  surface-water streams.

Both are lazily imported by their `site_map` stats and expose callable seams
(`dem_source` / `streams_source`) so tests and downstream callers stay
network-free.

---

## Markers

### `DEFAULT_MARKERS`

`("o", "s", "D", "^", "v", "<", ">", "p", "*", "h", "x", "+")`

### `DEFAULT_PALETTE`

`("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
"#e377c2", "#7f7f7f", "#bcbd22", "#17becf")`

### `gen_markers(values, markers=DEFAULT_MARKERS, palette=DEFAULT_PALETTE)`

```python
def gen_markers(
    values: list[str],
    markers: tuple[str, ...] = DEFAULT_MARKERS,
    palette: tuple[str, ...] = DEFAULT_PALETTE,
) -> dict[str, dict[str, str]]:
```

Assigns each value a `{"marker": m, "color": c}` in deterministic order (the
cartesian product of `markers × palette` cycled in order).

### `gen_markers_series(values, markers=DEFAULT_MARKERS, palette=DEFAULT_PALETTE)`

```python
def gen_markers_series(values: pd.Series, ...) -> pd.Series:
```

Returns a `pd.Series` of marker names for the unique values of `values`
(deterministic order), named after `values.name`.

### `gen_markers_cross_grouping(group1, group2, markers=DEFAULT_MARKERS, palette=DEFAULT_PALETTE)`

```python
def gen_markers_cross_grouping(
    group1: list[str],
    group2: list[str],
    markers: tuple[str, ...] = DEFAULT_MARKERS,
    palette: tuple[str, ...] = DEFAULT_PALETTE,
) -> dict[str, dict[str, dict[str, str]]]:
```

Assigns unique `{"marker": m, "color": c}` combos per `(g1, g2)` cross
grouping, returned as `{g1: {g2: {"marker": …, "color": …}}}`.

> `gen_markers_cross_grouping` is defined in `geofig_engine.io.markers` and is
> not re-exported from `geofig_engine.io`.

---

## Preprocessing pipeline

### `PipelineStep` (frozen dataclass)

```python
@dataclass(frozen=True)
class PipelineStep:
    name: str
    func: Callable[[pd.DataFrame], pd.DataFrame]
    kwargs: dict[str, Any] = {}
```

### `Pipeline`

```python
class Pipeline:
    def __init__(self, steps: list[PipelineStep] | None = None): ...
```

| Method | Signature | Description |
| --- | --- | --- |
| `add` | `add(name, func, **kwargs)` | Appends a `PipelineStep` and returns `self` (fluent). |
| `run` | `run(data: pd.DataFrame) -> pd.DataFrame` | Applies each step in order, passing `kwargs` through to each `func`. |
| `steps` | property | `list[PipelineStep]` copy. |

```python
pipeline = Pipeline().add("dedupe", lambda d, **k: d.drop_duplicates(**k), keep="first")
result = pipeline.run(df)
```

---

## EQuIS conversion

Pure-pandas conversions between the EQuIS **flat** long format (one row per
parameter result per sample), a wide per-sample frame, and the EQuIS cross-tab
Excel layout. All contracts are deterministic and never mutate the input.

### `equisflat_to_sample_df(flat, sample_keys=("Location",), parameter_col="Parameter", value_col="Result", extra_cols=(), drop_na=True)`

Pivots a long EQuIS flat frame to a wide per-sample frame.

| Param | Type | Description |
| --- | --- | --- |
| `flat` | `pd.DataFrame` | Long-form frame, one row per parameter result per sample. |
| `sample_keys` | `Sequence[str] \| str` | Column(s) identifying each sample; kept as the wide frame's leading columns. |
| `parameter_col` | `str` | Column naming the parameter/analyte. |
| `value_col` | `str` | Column holding the numeric result. |
| `extra_cols` | `Sequence[str] \| str` | Additional sample-level columns to carry into the wide frame; each must be constant per sample, else `ValueError`. |
| `drop_na` | `bool` | Drop rows whose `value_col` is NaN before pivoting. |

**Returns:** one row per sample, one column per parameter (first-appearance
order), cells = results. Columns outside the keys/parameter/value/extra set
are dropped.

**Raises:** `ValueError` — a `(sample, parameter)` pair appears more than once,
an `extra_cols` value varies within a sample, or a required column is missing.

### `sample_df_to_equisflat(sample_df, sample_keys=("Location",), parameter_col="Parameter", value_col="Result", extra_cols=(), drop_na=True)`

Inverse of `equisflat_to_sample_df`: melts wide parameter columns back to one
`(sample, parameter)` row each. `sample_keys` / `extra_cols` are id vars; the
output lists them first, then `parameter_col` and `value_col`.

### `equis_crosstab_to_flat(path_or_df, sample_keys=("Location",), parameter_col="Parameter", value_col="Result", unit_col="Result_Unit")`

Parses an EQuIS cross-tab (wide, rows = samples) into the long flat form.

| Param | Type | Description |
| --- | --- | --- |
| `path_or_df` | `str \| Path \| pd.DataFrame` | A frame already read from a cross-tab, or an Excel file path (read via `pd.read_excel`; `openpyxl` is only needed by callers/tests that exercise Excel files). |
| `sample_keys` | `Sequence[str] \| str` | Sample-identifying columns, kept on every output row. |
| `parameter_col` / `value_col` / `unit_col` | `str` | Output column names for the parameter, the numeric result, and the parsed unit. |

Column-name parsing follows two documented forms: underscore-separated
`"NO3_mg/L"` and parenthesized `"Ca (mg/L)"` (regular expressions
`UNIT_SUFFIX_RE` / `UNIT_PAREN_RE` over a fixed unit-alternation set).
Unit-suffixed columns become parameter rows (cells coerced with
`pd.to_numeric(errors="coerce")` — non-numeric → NaN); columns with neither a
unit suffix nor a sample key are treated as row metadata and broadcast onto
every output row; non-string column names are always metadata.

**Raises:** `ValueError` — a sample-key column is missing, or no unit-suffixed
analyte column was found.

---

## Unit normalization

### `SI_PREFIXES`

`dict[str, int]` — SI prefix → power-of-ten exponent, used by
`equisflat_normalize_units`:

| Prefix | Exponent |
| --- | --- |
| `"n"` | −9 |
| `"u"`, `"µ"`, `"μ"` | −6 (both the micro sign and Greek mu are accepted) |
| `"m"` | −3 |
| `"c"` | −2 |
| `"d"` | −1 |
| `"k"` | 3 |
| `"M"` | 6 |
| `"G"` | 9 |

### `equisflat_normalize_units(flat, parameter_col="Parameter", value_col="Result", unit_col="Result_Unit", inplace=False)`

Normalizes SI prefixes **within each parameter group** so all results for one
parameter share a single unit string.

```python
def equisflat_normalize_units(
    flat: pd.DataFrame,
    parameter_col: str = "Parameter",
    value_col: str = "Result",
    unit_col: str = "Result_Unit",
    inplace: bool = False,
) -> pd.DataFrame:
```

Per group, the **canonical unit** is the most frequent *recognized* unit
(ties → lexicographically smallest unit string), and every value is rescaled
by:

```
value * 10 ** (prefix_exponent(row_unit) - prefix_exponent(canonical))
```

Recognized units are a bare allowed base (`g`, `L`, `mol`, `eq`, `N`,
`g/L`, `g/kg`/`g_kg`, `mol/L`, `mol/kg`, `eq/L`, `cc`, `cm3`, `m3` — exponent
0) or a single `SI_PREFIXES` prefix followed by an allowed base. Unrecognized
unit strings pass through untouched (value and unit unchanged), as do groups
without any recognized unit and rows whose value is not numeric.

Returns a new frame by default; `inplace=True` mutates and returns the input
frame. **Raises:** `ValueError` — a required column is missing.

---

## Column utilities

### `ecesis_to_sample_df(frame, unit_pattern=None, drop_na=True)`

Parses Ecesis-style column names into a wide frame with a **two-level
`(analyte, unit)` column index**. Ecesis forms are the same suffix styles as
EQuIS cross-tabs — `"NO3_mg/L"` (underscore) or `"Ca (mg/L)"` (parenthesized),
governed by `DEFAULT_UNIT_ALTERNATION`. Plain columns (`"Sample_ID"`, `"pH"`)
are kept as-is with an empty unit level.

| Param | Type | Description |
| --- | --- | --- |
| `frame` | `pd.DataFrame` | Wide frame whose column names may embed units. |
| `unit_pattern` | `compiled regex \| str \| None` | Optional override of the default unit-suffix set. A matching regex must define named groups `param` and `unit` (else `ValueError`); only that regex is consulted. |
| `drop_na` | `bool` | Drop rows where *every* parsed numeric cell is NaN. Rows with at least one parsed value (or only plain columns) are kept. |

**Returns:** a new frame (input never mutated) with the same index and column
order, parsed columns coerced with `pd.to_numeric(errors="coerce")`.

**Raises:** `ValueError` — two input columns parse to the same
`(analyte, unit)` key, or `unit_pattern` matches without the required groups.

### `create_bins(series, bins, strategy="range", labels=None, include_lowest=True, right=True)`

Bins a numeric or datetime series into a deterministic categorical series.

| Param | Type | Description |
| --- | --- | --- |
| `series` | `pd.Series` | Numeric or datetime series to bin. |
| `bins` | `int \| sequence` | `strategy="range"`: an `int` (that many equal-width bins across the observed min–max) or an explicit sorted sequence of edges. `strategy="quantile"`: the number of equal-frequency bins. |
| `strategy` | `"range" \| "quantile"` | `"range"` → `pd.cut` (equal-width); `"quantile"` → `pd.qcut(..., duplicates="drop")` (equal-frequency). |
| `labels` | `Sequence[Any] \| None` | Optional bin labels (as accepted by cut/qcut). |
| `include_lowest` | `bool` | First interval closed on the left (range strategy only). |
| `right` | `bool` | Intervals closed on the right (range strategy only). |

**Returns:** a categorical series with the same index and name as `series`.
NaN input values map to NaN categories; identical input produces identical
category dtype and ordering.

**Raises:** `ValueError` — unknown `strategy`, or an invalid bin specification
surfaced by cut/qcut (e.g. wrong label count, non-unique quantile edges).

---

*Next: [core.md](core.md) · [engine.md](engine.md) · [provider.md](provider.md) · [templates.md](templates.md) · [renderers.md](renderers.md) · [serialize.md](serialize.md) · [data.md](data.md)*