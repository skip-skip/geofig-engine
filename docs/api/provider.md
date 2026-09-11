# API Reference — Providers

The **single input abstraction** the engine consumes: a structural
`DataProvider` protocol plus two concrete implementations. Provider views from
`geodata` (and result tables from `geochemmodel`) satisfy the protocol
duck-typed — this module never imports those packages.

```python
from geofig_engine import DataProvider, DataFrameProvider, DatasetProvider
```

## Contents

- [DataProvider protocol](#dataprovider-protocol)
- [Selector forms](#selector-forms)
- [DataFrameProvider](#dataframeprovider)
- [DatasetProvider](#datasetprovider)

---

## DataProvider protocol

`@runtime_checkable` structural contract (`geofig_engine.provider.DataProvider`).
Every input the engine consumes must expose these members; implementers are
duck-typed and the engine never imports the provider's package.

| Member | Signature | Semantics |
| --- | --- | --- |
| `columns` | property → `list[str]` | The concrete column names available on the provider. |
| `resolve` | `resolve(selector) -> list[str]` | Maps a selector (or plain column name / list of names) to the concrete column strings it denotes. |
| `expand` | `expand(iterators: list \| None = None) -> list[tuple[pd.DataFrame, dict]]` | Multi-figure expansion: yields one `(frame, context)` pair per iterator combination; `iterators=None` yields the single `(frame, {})` pair. The engine calls this and never re-implements iterator expansion. |
| `subset` | `subset(*, columns=None, **filters) -> DataProvider` | Returns a **new** provider (never mutates the input), row-filtered by column values (exact match; `in`-list) and optionally restricted to `columns`. |
| `unique_values` | `unique_values(column: str) -> list` | Sorted unique values for a column. |
| `dimensions` | `dimensions(column: str) -> dict` | Column metadata labels (`{}` when the provider has no metadata plane). |

```python
from geofig_engine.provider import DataFrameProvider

provider = DataFrameProvider(df)

provider.resolve("Ca")                     # ["Ca"]
provider.resolve(["Ca", "Mg"])             # ["Ca", "Mg"]
provider.expand(iterators)                 # [(subset_df, {"Well": "A"}), ...]
provider.subset(Location=["A", "B"])       # new provider, rows filtered only
provider.unique_values("Well")             # sorted unique values
provider.dimensions("Ca")                  # {} for a raw frame
```

---

## Selector forms

`provider.resolve` accepts the same selector forms the legacy
`DimensionSelector` covered, resolved against the provider's frame (and, where
available, its `dimensions` metadata):

- a column name — `"chem1"`;
- a `(kind, column)` tuple — `("column", "chem1")`;
- a `DimensionSelector`-like object (anything exposing a `selector`
  attribute, e.g. `geofig_engine.core.dimension_selector.DimensionSelector`);
- an explicit list of names — `["chem1", "chem2"]`;
- an attribute-based dict — `{"analyte": True}` (requires metadata via
  `dimensions`; `KeyError`/`ValueError` otherwise).

Unknown columns raise `KeyError` with a descriptive message.

---

## DataFrameProvider

```python
class DataFrameProvider:
    def __init__(self, dataframe: pd.DataFrame) -> None: ...
```

Wraps a raw `pandas.DataFrame` for standalone engine use. `resolve` is
identity-only (column names), `dimensions` returns `{}` — there is no metadata
plane at this layer — and `expand` starts from a single context. The wrapped
frame is **copied** on construction, so provider views never mutate (or
observe mutation of) the caller's frame. Responsible for "a raw `DataFrame`
works out of the box" (`render_template` wraps frames here automatically).

```python
from geofig_engine import DataFrameProvider

provider = DataFrameProvider(df)   # copies df; frame mutations are invisible
```

---

## DatasetProvider

```python
class DatasetProvider(DataFrameProvider):
    def __init__(self, dataset: Dataset) -> None: ...
```

Adapts a legacy `Dataset` to the `DataProvider` contract. The dataset's
dataframe powers the standard provider members (mirroring `DataFrameProvider`);
`dimensions(column)` reports the dataset's dimension labels for that column,
and attribute-based selectors resolve against them. Used by the legacy
engine-adaptation path and deprecated code only — new code should pass raw
frames or duck-typed providers.

---

*Next: [core.md](core.md) · [engine.md](engine.md) · [templates.md](templates.md) · [renderers.md](renderers.md) · [serialize.md](serialize.md) · [data.md](data.md) · [io.md](io.md)*