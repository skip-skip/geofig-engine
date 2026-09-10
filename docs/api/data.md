# API Reference — Data

`geofig_engine.data` provides the **geom preset registry** (categorized,
data-only geometry catalog that hydrates into [`Layer`](core.md#layers--specs)s)
plus expression validation and a **legacy function-registry view** over that
same catalog.

```python
from geofig_engine.data.geom_presets import (
    GEOM_KINDS, GeomPreset, GeomPresetItem,
    GeomPresetLoader, GeomPresetLoadError,
    GeomPresetRegistry,
    get_geom_preset_registry, reset_geom_preset_registry,
    item_to_layer, preset_to_layers,
)
from geofig_engine.data import (
    FunctionType, FunctionCategory, GeospatialMetadata, MathFunction,
    FunctionValidator, FunctionRegistry, FunctionLoader, FunctionLoadError,
    get_function_registry,
)
```

## Contents

- [Geom preset models](#geom-preset-models)
- [Loader](#loader)
- [Registry](#registry)
- [Layer hydration](#layer-hydration)
- [Bundled catalog](#bundled-catalog)
- [Legacy function API](#legacy-function-api)

---

## Geom preset models

### `GEOM_KINDS`

`("function_line", "abline", "hspan", "vspan", "rect", "text")` — the supported
geometry kinds a preset item may be.

### `GeomPresetItem` (frozen dataclass)

```python
@dataclass(frozen=True)
class GeomPresetItem:
    geom_type: str             # one of GEOM_KINDS
    params: dict[str, Any]     # kind-specific params, e.g. {"func": "8*x + 10"}
    mapping: dict[str, Any]    # constant visual mapping (scalars only)
    zorder: int | None = None
    func_type: str | None = None  # legacy FunctionType value, for MathFunction shim
```

Validates `geom_type`, param/mapping dicts, and `zorder` (`TypeError`/`ValueError`).

### `GeomPreset` (frozen dataclass)

```python
@dataclass(frozen=True)
class GeomPreset:
    id: str
    category: str
    items: tuple[GeomPresetItem, ...]
    tags: tuple[str, ...] = ()
    reference: str | None = None
    description: str | None = None
    valid_domain: str | None = None
    geospatial: dict[str, Any] = {}
```

**Properties:**

| Property | Type | Description |
| --- | --- | --- |
| `state` | `str \| None` | `geospatial.get("state")`. |
| `geom_kinds` | `set[str]` | The set of `geom_type`s across its items. |

---

## Loader

### `GeomPresetLoadError(Exception)`

Raised when preset JSON loading or validation fails.

### `GeomPresetLoader`

| Method | Signature | Description |
| --- | --- | --- |
| `bundled_dir` | `bundled_dir()` (staticmethod) | Directory containing the package's bundled preset JSON files. |
| `load_dir` | `load_dir(dir_path)` (classmethod) | Loads every `*.json` in a directory (sorted), returning `list[GeomPreset]`. Raises `GeomPresetLoadError` if the directory is missing or contains no JSON. |
| `load_file` | `load_file(file_path)` (classmethod) | Loads one file. Expected schema: `{"presets": [ {preset entry}, … ]}`. Raises `GeomPresetLoadError` for missing files, invalid JSON, a missing/non-list `presets` key, or a failing entry (each failure reports the index and id). |

---

## Registry

### `GeomPresetRegistry`

```python
class GeomPresetRegistry:
    def __init__(self, presets: Iterable[GeomPreset]): ...
```

Raises `ValueError` on duplicate preset ids.

**Queries:**

| Method | Signature | Description |
| --- | --- | --- |
| `get` | `get(preset_id)` | Preset by id; `KeyError` if unknown. |
| `get_all` | `get_all()` | `list[GeomPreset]` in insertion order. |
| `exists` | `exists(preset_id)` | Whether the id exists. |
| `filter` | `filter(category=None, tags=None, state=None)` | Exact `category`, ALL-of `tags`, exact `state` match. |
| `list_ids` | `list_ids(category=None)` | Preset ids, optionally by category. |
| `get_metadata` | `get_metadata()` | Statistics dict: `total_presets`, `by_category`, `by_tag`, `by_kind`. |

**Mutation:**

| Method | Signature | Description |
| --- | --- | --- |
| `merge_path` | `merge_path(path, overwrite=False)` | Loads a preset JSON file and merges it in. `overwrite=True` replaces conflicting ids; otherwise conflicts raise `GeomPresetLoadError`. Returns the list of merged ids in file order. |

**Hydration:**

| Method | Signature | Description |
| --- | --- | --- |
| `layers_for` | `layers_for(preset_ids)` | Hydrates explicit preset ids into `list[Layer]` (in id order); `KeyError` for unknown ids. |
| `auto_layers` | `auto_layers(category, geom_kinds=None)` | Hydrates every preset of `category` whose `geom_kinds` are a subset of `geom_kinds` (default: all `GEOM_KINDS`). Returns `list[Layer]` in registry order. |

### `get_geom_preset_registry()`

Returns the lazily-loaded global registry (single instance, loaded from the
bundled preset directory on first access). Raises `GeomPresetLoadError` if the
bundled loading fails.

### `reset_geom_preset_registry()`

Resets the global singleton; the next access reloads the bundled data.

---

## Layer hydration

| Function | Signature | Description |
| --- | --- | --- |
| `_build_geom(item)` *(private)* | `_build_geom(item: GeomPresetItem)` | Maps a preset item to its core `Geom` (`function_line` → `GeomFunctionLine(func, label=…)`; `abline` → slope/intercept or two-point `GeomAbline`; `hspan`/`vspan`/`rect`/`text` → the corresponding geom). |
| `item_to_layer` | `item_to_layer(item: GeomPresetItem) -> Layer` | Hydrates one item into a `Layer` with `StatIdentity` and the item's constant `mapping` (+ `zorder`). |
| `preset_to_layers` | `preset_to_layers(preset: GeomPreset) -> list[Layer]` | Hydrates a preset into its layers (one per item). |

---

## Bundled catalog

The bundled registry ships with `water_isotope.json` (category
`"water_isotope"`, all `function_line` geoms). Preset ids:

| Id | Line (δD = slope·δ18O + intercept) | Reference |
| --- | --- | --- |
| `GMWL` | `8*x + 10` | Craig, 1961 |
| `ID_FALLS` | `7.5*x + 5` | Rightmire and Lewis, 1987 |
| `ID_SOUTHEAST` | `7.4*x - 2.17` | Tappa et al., 2016 |
| `ID_SNAKERIVER` | `6.4*x - 21` | Wood and Low, 1986 |
| `REGIONAL_PNW` | `7.42*x + 0.88` | Sánchez-Murillo et al., 2015 |
| `ID_MOSCOW` | — | Idaho LMWL |
| `WA_PULLMAN` | — | Pullman, WA |
| `ID_CRUMARINE` | — | Crumarine Creek, ID |
| `WA_PALOUSE` | — | Palouse River, WA |
| `WA_PALOUSE_SF` | — | Palouse River SF, WA |
| `WA_NF_PALOUSE` | — | Palouse River NF, WA |
| `ID_CANYON` | — | Canyon, ID |
| `ID_PINE` | — | Pine, ID |
| `ID_PRIESTRIVER_BENTONCREEK` | — | Benton Creek, ID |
| `ID_PRIESTRIVER` | — | Priest River, ID |

Each entry carries `color`/`style`/`label` constants in its item mapping plus
`reference`, `description`, and `geospatial` metadata (region/state/city/
water body/water type). All 15 presets are consumed by the
[`isotope`](templates.md#isotope-mappingnone-scalessnone-functionsnone-autofiltertrue)
template.

---

## Legacy function API

Deprecated as a data source: the underlying catalog now lives in the geom
presets package. This API adapts `function_line`-type presets into legacy
`MathFunction` views so existing call sites keep working. New code should use
`get_geom_preset_registry()`.

### Enums & dataclasses

- `FunctionType` (`Enum`): `LINEAR`, `POLYNOMIAL`, `EXPONENTIAL`, `LOGARITHMIC`,
  `POWER`, `RATIONAL`, `CUSTOM`.
- `FunctionCategory` (`Enum`): `WATER_ISOTOPE`, `CALIBRATION`, `EMPIRICAL`,
  `REFERENCE`, `CUSTOM`.
- `GeospatialMetadata` (frozen dataclass): `region`, `state`, `city`,
  `water_body`, `water_type` (all `str | None`).
- `MathFunction` (frozen dataclass): `id`, `category`, `func_type`,
  `expression`, `variables`, `color`, `linestyle`, `label`, plus optional
  `reference`, `description`, `valid_domain`, `geospatial`,
  `custom_metadata`. Validates required fields (`ValueError`).

### `FunctionValidator`

| Method | Signature | Description |
| --- | --- | --- |
| `validate_expression` | `validate_expression(expression, variables, func_type=None)` | Returns `(is_valid, error_message)`. Parses the expression via `ast`; verifies declared variables are used, no unexpected variables appear (constants `pi`/`e` allowed), and that the structure matches `func_type` (e.g. LINEAR must not exponentiate, EXPONENTIAL must contain `exp`/`^`/`**`, LOGARITHMIC must contain `log`/`ln`/`log10`, POWER must contain exponentiation). |
| `extract_variables` | `extract_variables(expression)` | Returns the `set` of variable names (falls back to regex when parsing fails). |
| `validate_variables` | `validate_variables(variables)` | Returns `(is_valid, error_message)`; variables must be non-empty, valid identifiers, not reserved function names, and unique. |

Constants: `ALLOWED_FUNCTIONS` (sin, cos, tan, asin, acos, atan, sinh, cosh,
tanh, sqrt, exp, log, log10, ln, abs, ceil, floor, round, pi, e) and
`ALLOWED_OPERATORS` (`+ - * / // % ** ^`).

### Loading

`FunctionLoader.load()` loads all function-line presets as `MathFunction`
instances (cached). Presets whose items are not exclusively `function_line`
are skipped. Raises `FunctionLoadError` on conversion failure.

`FunctionLoadError(Exception)` — raised for load/validation failures.

### `FunctionRegistry`

```python
class FunctionRegistry:
    def __init__(self, functions: list[MathFunction]): ...
```

| Method | Signature | Description |
| --- | --- | --- |
| `get` | `get(func_id)` | Function by id; `KeyError` if unknown. |
| `get_all` | `get_all()` | `list[MathFunction]`. |
| `exists` | `exists(func_id)` | Whether the id exists. |
| `get_by_category` | `get_by_category(category)` | Functions in a `FunctionCategory`. |
| `get_by_type` | `get_by_type(func_type)` | Functions of a `FunctionType`. |
| `get_by_variable` | `get_by_variable(variable_name)` | Functions using a variable (e.g. `"x"`). |
| `get_by_state` | `get_by_state(state_code)` | Functions whose geospatial state matches (e.g. `"ID"`). |
| `filter` | `filter(category=None, func_type=None, variables=None, require_all_variables=False, state=None)` | Combined filtering; with `require_all_variables=True` a function must have ALL listed variables, else ANY. |
| `list_ids` | `list_ids(...)` | Ids matching a filter. |
| `get_metadata` | `get_metadata()` | Statistics over the registry. |

### `get_function_registry()`

Returns a `FunctionRegistry` built lazily from `FunctionLoader.load()`.

---

*Next: [core.md](core.md) · [engine.md](engine.md) · [templates.md](templates.md) · [renderers.md](renderers.md) · [serialize.md](serialize.md) · [io.md](io.md)*