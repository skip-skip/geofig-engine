# API Reference — IO

`geofig_engine.io` provides geo/distance helpers, deterministic marker-palette
generation, and a small preprocessing pipeline.

```python
from geofig_engine.io import (
    haversine, path_distance,
    gen_markers, gen_markers_series,
    Pipeline, PipelineStep,
)
from geofig_engine.io.markers import gen_markers_cross_grouping, DEFAULT_MARKERS, DEFAULT_PALETTE
```

## Contents

- [Geo helpers](#geo-helpers)
- [Markers](#markers)
- [Preprocessing pipeline](#preprocessing-pipeline)

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

*Next: [core.md](core.md) · [engine.md](engine.md) · [templates.md](templates.md) · [renderers.md](renderers.md) · [serialize.md](serialize.md) · [data.md](data.md)*