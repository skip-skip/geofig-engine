"""Transport-agnostic patches for versioned dashboard snapshots.

A patch is derived from two dashboard payloads and is applied to the older
payload to reproduce the newer one exactly. Only plain data is exchanged: this
module adds no WebSocket/SSE/HTTP transport and no frontend code.

Operation patches carry ``schema``, ``schema_version``, ``revision`` and an
optional ``base_revision`` alongside an ``operations`` list. Changes that cannot
be expressed by the five supported operations (for example, an added figure)
fall back to a self-contained full-payload patch under ``payload``. Bare lists
of operations are also accepted by :func:`apply_dashboard_patch` for callers
that wrap metadata themselves.
"""

from __future__ import annotations

from copy import deepcopy
from numbers import Integral
from typing import Any

from geofig_engine.serialize.dashboard import (
    _LAYOUT_KEYS,
    _revision,
    validate_dashboard_payload,
)


DASHBOARD_PATCH_SCHEMA = "geofig-engine/dashboard-patch"
DASHBOARD_PATCH_SCHEMA_VERSION = 1

_OPERATION_NAMES = frozenset({
    "replace_data",
    "append_data",
    "replace_definition",
    "update_settings",
    "remove_figure",
})
_REQUIRED_FIELDS = {
    "replace_data": ("figure_id", "columns"),
    "append_data": ("figure_id", "columns"),
    "replace_definition": ("figure_id", "definition", "template_hash"),
    "update_settings": ("figure_id", "settings"),
    "remove_figure": ("figure_id",),
}


def _is_int(value: Any) -> bool:
    return isinstance(value, Integral) and not isinstance(value, bool)


def _figure_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    figures: dict[str, dict[str, Any]] = {}
    for index, figure in enumerate(payload.get("figures", [])):
        figure_id = figure.get("figure_id")
        if not isinstance(figure_id, str) or not figure_id:
            raise ValueError(f"dashboard figures[{index}].figure_id must be a string")
        if figure_id in figures:
            raise ValueError(f"duplicate dashboard figure_id: {figure_id!r}")
        figures[figure_id] = figure
    return figures


def _operations(patch: Any, seam: str = "patch") -> list[Any]:
    """Return the operation list from a patch envelope or bare list."""
    if isinstance(patch, list):
        return patch
    if not isinstance(patch, dict):
        raise ValueError(f"{seam} must be a dict or a list of operations")
    for key in ("operations", "ops"):
        if key in patch:
            operations = patch[key]
            if not isinstance(operations, list):
                raise ValueError(f"{seam}.{key} must be a list")
            return operations
    raise ValueError(f"{seam} is missing required field 'operations'")


def _patch_metadata(patch: Any) -> dict[str, Any]:
    return patch if isinstance(patch, dict) else {}


def _validate_operation(operation: Any, seam: str) -> None:
    if not isinstance(operation, dict):
        raise ValueError(f"{seam} must be a dict")
    name = operation.get("op")
    if not isinstance(name, str) or not name:
        raise ValueError(f"{seam}.op must be a non-empty string")
    if name not in _OPERATION_NAMES:
        raise ValueError(f"unknown dashboard patch operation at {seam}: {name!r}")
    for field in _REQUIRED_FIELDS[name]:
        if field not in operation:
            raise ValueError(f"{seam} is missing required field {field!r} for {name}")

    figure_id = operation["figure_id"]
    if not isinstance(figure_id, str) or not figure_id:
        raise ValueError(f"{seam}.figure_id must be a non-empty string")

    if name in {"replace_data", "append_data"}:
        columns = operation["columns"]
        if not isinstance(columns, dict):
            raise ValueError(f"{seam}.columns must be a dict")
        for column, values in columns.items():
            if not isinstance(values, list):
                raise ValueError(f"{seam}.columns[{column!r}] must be a list")
        if "index" in operation and not isinstance(operation["index"], list):
            raise ValueError(f"{seam}.index must be a list")
        if "legend" in operation and operation["legend"] is not None:
            if not isinstance(operation["legend"], list):
                raise ValueError(f"{seam}.legend must be a list or null")
    elif name == "replace_definition":
        if not isinstance(operation["definition"], dict):
            raise ValueError(f"{seam}.definition must be a dict")
        if not isinstance(operation["template_hash"], str):
            raise ValueError(f"{seam}.template_hash must be a string")
        if "children" in operation and not isinstance(operation["children"], list):
            raise ValueError(f"{seam}.children must be a list")
    elif name == "update_settings":
        if not isinstance(operation["settings"], dict):
            raise ValueError(f"{seam}.settings must be a dict")
        if "template_hash" in operation and not isinstance(
            operation["template_hash"], str
        ):
            raise ValueError(f"{seam}.template_hash must be a string")


def validate_dashboard_patch(patch: Any) -> None:
    """Validate a patch envelope, a full-snapshot patch, or a bare op list."""
    metadata = _patch_metadata(patch)

    if isinstance(patch, dict) and "payload" in patch:
        if patch.get("schema") != DASHBOARD_PATCH_SCHEMA:
            raise ValueError(
                f"unsupported dashboard patch schema: {patch.get('schema')!r}"
            )
        version = patch.get("schema_version")
        if version != DASHBOARD_PATCH_SCHEMA_VERSION or isinstance(version, bool):
            raise ValueError(
                f"unsupported dashboard patch schema_version: {version!r}"
            )
        if not _is_int(patch.get("revision")):
            raise ValueError("dashboard patch revision must be an integer")
        if "base_revision" in patch and not _is_int(patch["base_revision"]):
            raise ValueError("dashboard patch base_revision must be an integer")
        validate_dashboard_payload(patch["payload"])
        return

    if metadata:
        if metadata.get("schema") != DASHBOARD_PATCH_SCHEMA:
            raise ValueError(
                f"unsupported dashboard patch schema: {metadata.get('schema')!r}"
            )
        version = metadata.get("schema_version")
        if version != DASHBOARD_PATCH_SCHEMA_VERSION or isinstance(version, bool):
            raise ValueError(
                f"unsupported dashboard patch schema_version: {version!r}"
            )
        if not _is_int(metadata.get("revision")):
            raise ValueError("dashboard patch revision must be an integer")
        if "base_revision" in metadata and not _is_int(metadata["base_revision"]):
            raise ValueError("dashboard patch base_revision must be an integer")

    operations = _operations(patch)
    for index, operation in enumerate(operations):
        _validate_operation(operation, f"operations[{index}]")


def _is_append_only(
    old_data: dict[str, Any], new_data: dict[str, Any]
) -> dict[str, Any] | None:
    """Return appended values when new data extends old data at the tail."""
    old_columns = old_data.get("columns", {})
    new_columns = new_data.get("columns", {})
    old_index = old_data.get("index", [])
    new_index = new_data.get("index", [])
    if not isinstance(old_columns, dict) or not isinstance(new_columns, dict):
        return None
    if list(old_columns) != list(new_columns):
        return None
    if not isinstance(old_index, list) or not isinstance(new_index, list):
        return None

    offset = len(old_index)
    if offset == 0 or offset >= len(new_index):
        return None
    if new_index[:offset] != old_index:
        return None

    appended: dict[str, list[Any]] = {}
    for name, values in new_columns.items():
        previous = old_columns.get(name)
        if not isinstance(values, list) or not isinstance(previous, list):
            return None
        if len(values) != len(new_index) or len(previous) != offset:
            return None
        if values[:offset] != previous:
            return None
        appended[name] = deepcopy(values[offset:])
    return {"columns": appended, "index": deepcopy(new_index[offset:])}


def _without_settings(definition: dict[str, Any]) -> dict[str, Any]:
    structural = deepcopy(definition)
    structural.pop("settings", None)
    structural.pop("layout", None)
    return structural


def _diff_figure(
    figure_id: str,
    old_figure: dict[str, Any],
    new_figure: dict[str, Any],
) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []

    old_data = old_figure.get("data", {})
    new_data = new_figure.get("data", {})
    old_legend = old_figure.get("legend")
    new_legend = new_figure.get("legend")
    legend_changed = old_legend != new_legend
    if old_data != new_data or legend_changed:
        appended = None if old_data == new_data else _is_append_only(old_data, new_data)
        if appended is not None:
            data_op: dict[str, Any] = {
                "op": "append_data",
                "figure_id": figure_id,
                **appended,
            }
        else:
            data_op = {
                "op": "replace_data",
                "figure_id": figure_id,
                "columns": deepcopy(new_data.get("columns", {})),
                "index": deepcopy(new_data.get("index", [])),
            }
        if legend_changed:
            data_op["legend"] = deepcopy(new_legend)
        operations.append(data_op)

    old_definition = old_figure.get("definition", {})
    new_definition = new_figure.get("definition", {})
    old_children = old_figure.get("children", [])
    new_children = new_figure.get("children", [])
    children_changed = old_children != new_children
    definition_changed = old_definition != new_definition
    hash_changed = old_figure.get("template_hash") != new_figure.get("template_hash")

    if definition_changed or children_changed or hash_changed:
        settings_only = (
            not children_changed
            and definition_changed
            and _without_settings(old_definition) == _without_settings(new_definition)
        )
        if settings_only and isinstance(new_definition.get("settings"), dict):
            settings_op: dict[str, Any] = {
                "op": "update_settings",
                "figure_id": figure_id,
                "settings": deepcopy(new_definition["settings"]),
            }
            if hash_changed:
                settings_op["template_hash"] = new_figure["template_hash"]
            operations.append(settings_op)
        else:
            definition_op: dict[str, Any] = {
                "op": "replace_definition",
                "figure_id": figure_id,
                "definition": deepcopy(new_definition),
                "template_hash": new_figure["template_hash"],
            }
            if children_changed:
                definition_op["children"] = deepcopy(new_children)
            operations.append(definition_op)

    return operations


def _envelope(
    old_payload: dict[str, Any],
    new_payload: dict[str, Any],
    *,
    operations: list[dict[str, Any]] | None = None,
    full: bool = False,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "schema": DASHBOARD_PATCH_SCHEMA,
        "schema_version": DASHBOARD_PATCH_SCHEMA_VERSION,
        "revision": new_payload["revision"],
        "base_revision": old_payload["revision"],
    }
    if full:
        envelope["payload"] = deepcopy(new_payload)
    else:
        envelope["operations"] = operations or []
    return envelope


def diff_dashboard_payload(
    old_payload: dict[str, Any], new_payload: dict[str, Any]
) -> dict[str, Any]:
    """Derive a patch that transforms ``old_payload`` into ``new_payload``."""
    validate_dashboard_payload(old_payload)
    validate_dashboard_payload(new_payload)

    full = _envelope(old_payload, new_payload, full=True)
    old_envelope = {
        key: value
        for key, value in old_payload.items()
        if key not in {"revision", "figures"}
    }
    new_envelope = {
        key: value
        for key, value in new_payload.items()
        if key not in {"revision", "figures"}
    }
    if old_envelope != new_envelope:
        return full

    old_figures = _figure_map(old_payload)
    new_figures = _figure_map(new_payload)
    if set(new_figures) - set(old_figures):
        return full

    operations: list[dict[str, Any]] = []
    for figure_id, old_figure in old_figures.items():
        if figure_id not in new_figures:
            operations.append({"op": "remove_figure", "figure_id": figure_id})
        else:
            operations.extend(
                _diff_figure(figure_id, old_figure, new_figures[figure_id])
            )

    patch = _envelope(old_payload, new_payload, operations=operations)
    if apply_dashboard_patch(old_payload, patch) != new_payload:
        return full
    return patch


def _figure_target(
    figures: list[dict[str, Any]],
    by_id: dict[str, int],
    figure_id: str,
    index: int,
) -> dict[str, Any]:
    if figure_id not in by_id:
        raise ValueError(
            f"dashboard patch operations[{index}] references unknown "
            f"figure_id {figure_id!r}"
        )
    return figures[by_id[figure_id]]


def _apply_data(
    figure: dict[str, Any], operation: dict[str, Any], index: int
) -> None:
    name = operation["op"]
    figure_id = operation["figure_id"]
    columns = operation["columns"]
    column_count = len(next(iter(columns.values()), []))
    if "index" in operation:
        new_index = deepcopy(operation["index"])
    elif name == "replace_data":
        new_index = list(range(column_count))
    else:
        offset = len(figure["data"]["index"])
        new_index = list(range(offset, offset + column_count))
    if any(len(values) != len(new_index) for values in columns.values()):
        raise ValueError(
            f"dashboard patch operations[{index}] for {figure_id!r} has "
            "column lengths that do not match its index"
        )

    data = figure.setdefault("data", {"columns": {}, "index": []})
    if name == "replace_data":
        data["columns"] = deepcopy(columns)
        data["index"] = new_index
        return

    if any(column not in data["columns"] for column in columns):
        unknown = next(column for column in columns if column not in data["columns"])
        raise ValueError(
            f"dashboard patch operations[{index}] for {figure_id!r} references "
            f"unknown column {unknown!r}"
        )
    width = len(new_index)
    for column, values in data["columns"].items():
        additions = columns.get(column, [None] * width)
        values.extend(deepcopy(additions))
    data["index"].extend(new_index)


def _apply_operation(
    figures: list[dict[str, Any]],
    by_id: dict[str, int],
    operation: dict[str, Any],
    index: int,
) -> None:
    figure_id = operation["figure_id"]
    figure = _figure_target(figures, by_id, figure_id, index)
    name = operation["op"]

    if name in {"replace_data", "append_data"}:
        _apply_data(figure, operation, index)
        if "legend" in operation:
            if operation["legend"] is None:
                figure.pop("legend", None)
            else:
                figure["legend"] = deepcopy(operation["legend"])
        return

    if name == "replace_definition":
        figure["definition"] = deepcopy(operation["definition"])
        figure["template_hash"] = operation["template_hash"]
        if "children" in operation:
            figure["children"] = deepcopy(operation["children"])
        return

    if name == "update_settings":
        settings = deepcopy(operation["settings"])
        definition = figure["definition"]
        definition["settings"] = settings
        definition["layout"] = {
            key: settings[key] for key in _LAYOUT_KEYS if key in settings
        }
        if "template_hash" in operation:
            figure["template_hash"] = operation["template_hash"]
        return

    position = by_id.pop(figure_id)
    figures.pop(position)
    for moved_id, moved_position in list(by_id.items()):
        if moved_position > position:
            by_id[moved_id] = moved_position - 1


def apply_dashboard_patch(payload: dict[str, Any], patch: Any) -> dict[str, Any]:
    """Apply ``patch`` to ``payload`` and return a new dashboard payload."""
    validate_dashboard_patch(patch)
    validate_dashboard_payload(payload)

    metadata = _patch_metadata(patch)
    base_revision = metadata.get("base_revision")
    if base_revision is not None and base_revision != payload["revision"]:
        raise ValueError(
            "stale or out-of-order dashboard patch: base_revision "
            f"{base_revision} does not match payload revision {payload['revision']}"
        )

    if isinstance(patch, dict) and "payload" in patch:
        result = deepcopy(patch["payload"])
        validate_dashboard_payload(result)
        return result

    result = deepcopy(payload)
    figures = result["figures"]
    by_id = {
        figure["figure_id"]: position
        for position, figure in enumerate(figures)
    }
    for index, operation in enumerate(_operations(patch)):
        _apply_operation(figures, by_id, operation, index)

    revision = metadata.get("revision")
    result["revision"] = _revision(figures) if revision is None else int(revision)
    validate_dashboard_payload(result)
    return result


__all__ = [
    "DASHBOARD_PATCH_SCHEMA",
    "DASHBOARD_PATCH_SCHEMA_VERSION",
    "diff_dashboard_payload",
    "apply_dashboard_patch",
    "validate_dashboard_patch",
]
