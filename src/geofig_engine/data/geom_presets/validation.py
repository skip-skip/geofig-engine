"""
Validation for geometry preset entries.

Converts raw JSON dicts into validated GeomPreset objects. Each supported
geometry kind has its own parameter and mapping rules:

    function_line  - params: func (expression using x)
                     optional item key: func_type (FunctionType value)
    abline         - params: slope+intercept OR x1/y1/x2/y2 (exactly one mode)
    hspan          - mapping: ymin < ymax required
    vspan          - mapping: xmin < xmax required
    rect           - mapping: xmin<xmax and ymin<ymax required
    text           - mapping: x, y (numeric) + label (non-empty string)

Mapping values must be JSON scalars; only text's "bbox" may be a dict.
Unknown mapping keys or unknown params are rejected.
"""

from typing import Any

from geofig_engine.data.functions import FunctionType
from geofig_engine.data.validator import FunctionValidator
from geofig_engine.data.geom_presets.models import GEOM_KINDS, GeomPreset, GeomPresetItem


# Per-kind rules: allowed geom parameter keys, allowed/required mapping keys.
_KIND_RULES: dict[str, dict[str, set[str]]] = {
    "function_line": {
        "params": {"func"},
        "required_mapping": set(),
        "allowed_mapping": {"x", "color", "style", "width", "alpha", "label"},
    },
    "abline": {
        "params": {"slope", "intercept", "x1", "y1", "x2", "y2"},
        "required_mapping": set(),
        "allowed_mapping": {"color", "style", "width", "alpha"},
    },
    "hspan": {
        "params": set(),
        "required_mapping": {"ymin", "ymax"},
        "allowed_mapping": {"ymin", "ymax", "color", "alpha"},
    },
    "vspan": {
        "params": set(),
        "required_mapping": {"xmin", "xmax"},
        "allowed_mapping": {"xmin", "xmax", "color", "alpha"},
    },
    "rect": {
        "params": set(),
        "required_mapping": {"xmin", "xmax", "ymin", "ymax"},
        "allowed_mapping": {"xmin", "xmax", "ymin", "ymax", "color", "alpha"},
    },
    "text": {
        "params": set(),
        "required_mapping": {"x", "y", "label"},
        "allowed_mapping": {"x", "y", "label", "color", "size", "alpha", "angle", "bbox"},
    },
}


def _is_scalar(value: Any) -> bool:
    """JSON scalar (bool excluded)."""
    if isinstance(value, bool):
        return False
    return value is None or isinstance(value, (str, int, float))


def _require_number(value: Any, name: str) -> float:
    """Coerce to float, raising ValueError with a clear message."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"'{name}' must be a number, got {value!r}")
    return float(value)


def _validate_function_line_params(geom: dict) -> dict[str, Any]:
    expr = geom.get("func")
    if not expr or not isinstance(expr, str):
        raise ValueError("function_line requires non-empty 'func' expression")

    func_type_str = geom.get("func_type", "linear")
    try:
        func_type = FunctionType(func_type_str)
    except ValueError as e:
        raise ValueError(f"invalid func_type '{func_type_str}': {e}") from e

    is_valid, error = FunctionValidator.validate_expression(
        expression=expr,
        variables=("x",),
        func_type=func_type,
    )
    if not is_valid:
        raise ValueError(f"invalid expression: {error}")

    return {"func": expr}


def _validate_abline_params(geom: dict) -> dict[str, Any]:
    has_slope = "slope" in geom
    point_keys = ("x1", "y1", "x2", "y2")
    has_points = all(k in geom for k in point_keys)

    if has_slope and has_points:
        raise ValueError("abline: provide slope+intercept OR x1/y1/x2/y2, not both")
    if not has_slope and not has_points:
        raise ValueError("abline: requires slope (+ optional intercept) or all of x1/y1/x2/y2")

    if has_slope:
        params = {
            "slope": _require_number(geom["slope"], "slope"),
            "intercept": _require_number(geom.get("intercept", 0.0), "intercept"),
        }
        extra = set(geom.keys()) - {"type", "func_type", "slope", "intercept"}
        if extra:
            raise ValueError(f"abline: unexpected keys {sorted(extra)}")
        return params

    extra = set(geom.keys()) - {"type", "func_type", *point_keys}
    if extra:
        raise ValueError(f"abline: unexpected keys {sorted(extra)}")
    return {k: _require_number(geom[k], k) for k in point_keys}


def _validate_ordered_bounds(mapping: dict, pairs: list[tuple[str, str]]) -> None:
    for lo_key, hi_key in pairs:
        lo = _require_number(mapping[lo_key], lo_key)
        hi = _require_number(mapping[hi_key], hi_key)
        if lo >= hi:
            raise ValueError(f"mapping bounds must satisfy {lo_key} < {hi_key}, got {lo} >= {hi}")


def _validate_item(item_data: dict) -> GeomPresetItem:
    if not isinstance(item_data, dict):
        raise TypeError("item must be a dictionary")

    geom = item_data.get("geom")
    if not isinstance(geom, dict):
        raise TypeError("item requires a 'geom' dictionary")

    kind = geom.get("type")
    if kind not in GEOM_KINDS:
        raise ValueError(f"geom type '{kind}' not supported; must be one of {GEOM_KINDS}")

    rules = _KIND_RULES[kind]

    # --- Params (kind-specific) ---
    if kind == "function_line":
        params = _validate_function_line_params(geom)
    elif kind == "abline":
        params = _validate_abline_params(geom)
    else:
        params = {}

    # --- Mapping ---
    mapping_raw = item_data.get("mapping", {})
    if not isinstance(mapping_raw, dict):
        raise TypeError("'mapping' must be a dictionary")

    missing_required = rules["required_mapping"] - set(mapping_raw.keys())
    if missing_required:
        raise ValueError(f"{kind} mapping missing required keys: {sorted(missing_required)}")

    unknown_keys = set(mapping_raw.keys()) - rules["allowed_mapping"]
    if unknown_keys:
        raise ValueError(
            f"{kind} mapping has unsupported keys {sorted(unknown_keys)}; "
            f"allowed: {sorted(rules['allowed_mapping'])}"
        )

    for key, value in mapping_raw.items():
        if key == "bbox":
            if not isinstance(value, dict):
                raise ValueError("text 'bbox' must be a dictionary of style properties")
        elif not _is_scalar(value):
            raise ValueError(f"mapping['{key}'] must be a scalar, got {type(value).__name__}")

    if kind == "hspan":
        _validate_ordered_bounds(mapping_raw, [("ymin", "ymax")])
    elif kind == "vspan":
        _validate_ordered_bounds(mapping_raw, [("xmin", "xmax")])
    elif kind == "rect":
        _validate_ordered_bounds(mapping_raw, [("xmin", "xmax"), ("ymin", "ymax")])
    elif kind == "text":
        _require_number(mapping_raw["x"], "x")
        _require_number(mapping_raw["y"], "y")
        label = mapping_raw["label"]
        if not label or not isinstance(label, str):
            raise ValueError("text mapping 'label' must be a non-empty string")

    # --- Optional fields ---
    zorder = item_data.get("zorder")
    if zorder is not None and (not isinstance(zorder, int) or isinstance(zorder, bool)):
        raise ValueError("'zorder' must be an int or None")

    func_type_value = None
    if kind == "function_line":
        func_type_value = geom.get("func_type", "linear")

    return GeomPresetItem(
        geom_type=kind,
        params=params,
        mapping=dict(mapping_raw),
        zorder=zorder,
        func_type=func_type_value,
    )


def validate_preset_data(data: dict) -> GeomPreset:
    """
    Validate a single preset entry and hydrate it into a GeomPreset.

    Args:
        data: Raw preset dictionary from JSON

    Returns:
        Validated GeomPreset instance

    Raises:
        TypeError/ValueError: With descriptive messages on any violation
    """
    if not isinstance(data, dict):
        raise TypeError("preset entry must be a dictionary")

    preset_id = data.get("id")
    if not preset_id or not isinstance(preset_id, str):
        raise ValueError("'id' must be a non-empty string")

    category = data.get("category")
    if not category or not isinstance(category, str):
        raise ValueError("'category' must be a non-empty string")

    items_raw = data.get("items")
    if not isinstance(items_raw, list) or len(items_raw) == 0:
        raise ValueError("'items' must be a non-empty array")

    items = tuple(_validate_item(item_data) for item_data in items_raw)

    tags_raw = data.get("tags", [])
    if not isinstance(tags_raw, list) or not all(isinstance(t, str) and t for t in tags_raw):
        raise ValueError("'tags' must be an array of non-empty strings")

    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        raise TypeError("'metadata' must be a dictionary")

    reference = metadata.get("reference")
    description = metadata.get("description")
    valid_domain = metadata.get("valid_domain")
    for name, value in (("reference", reference), ("description", description), ("valid_domain", valid_domain)):
        if value is not None and not isinstance(value, str):
            raise ValueError(f"metadata.{name} must be a string or null")

    geospatial = metadata.get("geospatial", {})
    if not isinstance(geospatial, dict):
        raise TypeError("metadata.geospatial must be a dictionary")

    return GeomPreset(
        id=preset_id,
        category=category,
        items=items,
        tags=tuple(tags_raw),
        reference=reference,
        description=description,
        valid_domain=valid_domain,
        geospatial=dict(geospatial),
    )
