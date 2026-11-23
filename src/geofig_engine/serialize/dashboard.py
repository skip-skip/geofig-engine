"""Versioned browser-safe dashboard snapshots projected from ``FigureSpec``.

This is a parallel projection of resolved specs, not a replacement for the
Python round-trip serializer in :mod:`geofig_engine.serialize.converters`:
the existing ``figure_spec_to_dict`` / ``spec_to_json`` behavior is untouched.
Definitions hold structure and column references only; all values live in a
columnar payload. Non-finite numbers and ``NaT`` are normalized to ``null``
(and that normalization is deliberate in both strict and non-strict modes),
datetimes become ISO-8601 strings, numpy scalars become Python scalars, and
tuples become arrays. Callables are rejected with the seam that contained
them. ``strict=True`` additionally validates the finished envelope.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time
from typing import Any, Iterable

import numpy as np
import pandas as pd

from geofig_engine.core.spec import FigureSpec
from geofig_engine.serialize._legend import extract_legend
from geofig_engine.serialize.converters import (
    coord_to_dict,
    facet_to_dict,
    geom_to_dict,
    scale_to_dict,
    stat_to_dict,
)


DASHBOARD_SCHEMA = "geofig-engine/dashboard"
DASHBOARD_SCHEMA_VERSION = 1
# Target version for Phase 19; pyproject.toml is bumped in the separate release.
ENGINE_VERSION = "0.5.0"

_LAYOUT_KEYS = (
    "figsize",
    "xlim",
    "ylim",
    "grid",
    "xlabel",
    "ylabel",
    "title",
    "tick_step",
    "secondary_x",
    "secondary_y",
)
_IDENTITY_KEYS = frozenset({
    "figure_id",
    "template_hash",
    "layer_id",
    "context",
    "iterator_key",
    "data_ref",
    "revision",
})


# ---------------------------------------------------------------------------
# Browser-safe value normalization
# ---------------------------------------------------------------------------

def _is_missing(value: Any) -> bool:
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return isinstance(result, (bool, np.bool_)) and bool(result)


def _normalize(value: Any, seam: str = "value") -> Any:
    """Convert one value into strict-JSON-compatible Python data."""
    if callable(value):
        source = getattr(value, "__name__", repr(value))
        raise TypeError(
            f"Unsupported callable in dashboard payload at {seam}: {source}"
        )
    if value is None or _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.datetime64):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    if isinstance(value, np.generic):
        return _normalize(value.item(), seam)
    if isinstance(value, dict):
        return {
            str(key): _normalize(item, f"{seam}.{key}")
            for key, item in value.items()
        }
    if isinstance(value, (pd.Series, pd.Index)):
        return [
            _normalize(item, f"{seam}[{index}]")
            for index, item in enumerate(value.tolist())
        ]
    if isinstance(value, (list, tuple, np.ndarray)):
        return [
            _normalize(item, f"{seam}[{index}]")
            for index, item in enumerate(value)
        ]
    if is_dataclass(value) and not isinstance(value, type):
        return _normalize(asdict(value), seam)
    return str(value)


def _canonical(value: Any) -> str:
    return json.dumps(
        _normalize(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _make_id(prefix: str, parts: Iterable[Any]) -> str:
    digest = hashlib.sha256(_canonical(list(parts)).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:16]}"


def _template_hash(definition: dict[str, Any]) -> str:
    """Hash the structural definition, stripping instance/data identity."""
    structural = _strip_identity(definition)
    digest = hashlib.sha256(_canonical(structural).encode("utf-8")).hexdigest()
    return digest[:16]


def _strip_identity(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_identity(item)
            for key, item in value.items()
            if key not in _IDENTITY_KEYS
        }
    if isinstance(value, list):
        return [_strip_identity(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# Columnar payload assembly
# ---------------------------------------------------------------------------

def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sanitize_hint(hint: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in hint)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "series"


class _ColumnStore:
    """Collect every column referenced by a figure into one JSON payload."""

    def __init__(self, frame: pd.DataFrame, seam: str) -> None:
        self.index_values = [
            _normalize(value, f"{seam}.index[{index}]")
            for index, value in enumerate(frame.index)
        ]
        self.index_keys = [_json_key(value) for value in self.index_values]
        self.columns: dict[str, list[Any]] = {}
        self._signatures: dict[str, str] = {}

        for position, column in enumerate(frame.columns):
            name = self._unique_name(str(column), f"{seam}.columns[{position}]")
            values = [
                _normalize(value, f"{seam}.columns[{name}][{index}]")
                for index, value in enumerate(frame.iloc[:, position].tolist())
            ]
            self.columns[name] = values
            self._signatures[
                self._signature(values, self.index_keys)
            ] = name

    @staticmethod
    def _signature(values: list[Any], keys: list[str]) -> str:
        return _json_key({"index": keys, "values": values})

    def _unique_name(self, base: str, hint: str) -> str:
        if base not in self.columns:
            return base
        candidate = f"{base}__{_sanitize_hint(hint)}"
        if candidate in self.columns:
            candidate = base
            suffix = 2
            while f"{candidate}__{suffix}" in self.columns:
                suffix += 1
            candidate = f"{candidate}__{suffix}"
        return candidate

    def _align(self, values: list[Any], keys: list[str], normalized_keys: list[Any]) -> list[Any]:
        positions = {key: index for index, key in enumerate(self.index_keys)}
        for key, normalized in zip(keys, normalized_keys):
            if key not in positions:
                positions[key] = len(self.index_keys)
                self.index_keys.append(key)
                self.index_values.append(normalized)
        for existing in self.columns.values():
            existing.extend([None] * (len(self.index_keys) - len(existing)))
        aligned = [None] * len(self.index_keys)
        for key, value in zip(keys, values):
            aligned[positions[key]] = value
        return aligned

    def register_series(
        self,
        series: pd.Series,
        hint: str,
        seam: str,
    ) -> str | None:
        """Register a resolved series and return its column name, if usable."""
        values = [
            _normalize(value, f"{seam}[{index}]")
            for index, value in enumerate(series.tolist())
        ]
        keys = [
            _json_key(_normalize(value, f"{seam}.index[{index}]"))
            for index, value in enumerate(series.index)
        ]
        signature = self._signature(values, keys)
        existing = self._signatures.get(signature)
        if existing is not None:
            return existing

        name = series.name if isinstance(series.name, str) and series.name else None
        if name is None:
            return None
        name = self._unique_name(name, hint)
        self.columns[name] = self._align(values, keys, [
            _normalize(value, f"{seam}.index[{index}]")
            for index, value in enumerate(series.index)
        ])
        self._signatures[signature] = name
        return name

    def to_payload(self) -> dict[str, Any]:
        columns = {name: list(values) for name, values in self.columns.items()}
        return {"columns": columns, "index": list(self.index_values)}


def _project_value(value: Any, store: _ColumnStore, seam: str) -> Any:
    """Project a spec value into refs/constants without duplicating values."""
    if isinstance(value, pd.Series):
        column = store.register_series(value, seam, seam)
        if column is not None:
            return {"$column": column}
        return {"$inline": _normalize(value.tolist(), f"{seam}.values")}
    if isinstance(value, dict):
        return {
            str(key): _project_value(item, store, f"{seam}.{key}")
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, np.ndarray, pd.Index)):
        return [
            _project_value(item, store, f"{seam}[{index}]")
            for index, item in enumerate(value)
        ]
    return _normalize(value, seam)


def _register_spec(spec: FigureSpec, store: _ColumnStore, prefix: str) -> None:
    """Pre-register all named series so refs are settled before definitions."""
    _project_value(spec.mappings, store, f"{prefix}.mappings")
    for layer_index, layer in enumerate(spec.layers):
        for channel, value in layer.visual_mapping.items():
            _project_value(
                value,
                store,
                f"{prefix}.layers[{layer_index}].visual_mapping.{channel}",
            )
    for child_index, child in enumerate(spec.children):
        child_prefix = f"{prefix}.children[{child_index}]"
        for position, column in enumerate(child.data.columns):
            store.register_series(
                child.data.iloc[:, position],
                f"{child_prefix}.data.columns[{position}]",
                f"{child_prefix}.data.columns[{column}]",
            )
        _register_spec(child, store, child_prefix)


# ---------------------------------------------------------------------------
# Definition assembly
# ---------------------------------------------------------------------------

def _layer_definition(
    layer: Any,
    index: int,
    prefix: str,
    store: _ColumnStore,
    figure_id: str,
) -> dict[str, Any]:
    seam = f"{prefix}.layers[{index}]"
    visual_mapping = {
        str(channel): _project_value(value, store, f"{seam}.visual_mapping.{channel}")
        for channel, value in layer.visual_mapping.items()
    }
    scales = {
        str(channel): _normalize(scale_to_dict(scale), f"{seam}.scales.{channel}")
        for channel, scale in (getattr(layer, "scales", None) or {}).items()
    }
    definition: dict[str, Any] = {
        "geom": _normalize(geom_to_dict(layer.geom), f"{seam}.geom"),
        "stat": _normalize(stat_to_dict(layer.stat), f"{seam}.stat"),
        "visual_mapping": visual_mapping,
        "scales": scales,
        "data_override": layer.data_override,
    }
    if layer.zorder is not None:
        definition["zorder"] = layer.zorder
    if layer.xlim is not None:
        definition["xlim"] = _normalize(layer.xlim, f"{seam}.xlim")
    if layer.ylim is not None:
        definition["ylim"] = _normalize(layer.ylim, f"{seam}.ylim")
    definition["layer_id"] = _make_id(
        "layer", [figure_id, index, _strip_identity(definition)]
    )
    return definition


def _definition(
    spec: FigureSpec,
    prefix: str,
    store: _ColumnStore,
    figure_id: str,
    child_definitions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    settings = _project_value(spec.settings, store, f"{prefix}.settings")
    definition = {
        "template_name": spec.template_name,
        "context": _project_value(spec.context, store, f"{prefix}.context"),
        "iterator_key": list(spec.iterator_key),
        "layers": [
            _layer_definition(layer, index, prefix, store, figure_id)
            for index, layer in enumerate(spec.layers)
        ],
        "mappings": _project_value(spec.mappings, store, f"{prefix}.mappings"),
        "coord": _normalize(coord_to_dict(spec.coord), f"{prefix}.coord"),
        "facet": _normalize(facet_to_dict(spec.facet), f"{prefix}.facet"),
        "settings": settings,
        "layout": {
            key: settings[key] for key in _LAYOUT_KEYS if key in settings
        },
        "transform": _normalize(
            spec.transform.to_dict() if spec.transform is not None else {},
            f"{prefix}.transform",
        ),
        "children": child_definitions or [],
    }
    return definition


def _child_records(
    spec: FigureSpec,
    figure_id: str,
    store: _ColumnStore,
    prefix: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, child in enumerate(spec.children):
        child_prefix = f"{prefix}.children[{index}]"
        child_id = _make_id(
            "child",
            [
                figure_id,
                index,
                child.template_name,
                _normalize(child.context, f"{child_prefix}.context"),
            ],
        )
        child_definition = _definition(child, child_prefix, store, child_id)
        records.append({
            "figure_id": child_id,
            "template_hash": _template_hash(child_definition),
            "definition": child_definition,
            "data_ref": "$parent",
        })
    return records


def _figure_payload(
    spec: FigureSpec,
    position: int,
    legend_groups: list[Any],
    *,
    legend: bool,
) -> dict[str, Any]:
    prefix = f"figures[{position}]"
    figure_id = _make_id(
        "figure",
        [
            spec.template_name,
            position,
            _normalize(spec.context, f"{prefix}.context"),
            list(spec.iterator_key),
        ],
    )
    store = _ColumnStore(spec.data, f"{prefix}.data")
    _register_spec(spec, store, prefix)

    children = _child_records(spec, figure_id, store, prefix)
    definition = _definition(
        spec, prefix, store, figure_id,
        child_definitions=[record["definition"] for record in children],
    )
    payload: dict[str, Any] = {
        "figure_id": figure_id,
        "template_hash": _template_hash(definition),
        "definition": definition,
        "data": store.to_payload(),
        "children": children,
    }
    if legend:
        payload["legend"] = _normalize(
            [asdict(group) for group in legend_groups], f"{prefix}.legend"
        )
    return payload


def _revision(figures: list[dict[str, Any]]) -> int:
    digest = hashlib.sha256(_canonical(figures).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 10_000_000


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def specs_to_dashboard_dict(
    specs: Iterable[FigureSpec],
    *,
    legend: bool = True,
    strict: bool = True,
) -> dict[str, Any]:
    """Project resolved specs into a versioned browser-safe snapshot dict."""
    spec_list = list(specs)
    legend_groups = extract_legend(spec_list) if legend else []
    figures = [
        _figure_payload(spec, position, legend_groups, legend=legend)
        for position, spec in enumerate(spec_list)
    ]
    payload = {
        "schema": DASHBOARD_SCHEMA,
        "schema_version": DASHBOARD_SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "revision": _revision(figures),
        "figures": figures,
    }
    if strict:
        validate_dashboard_payload(payload)
    return payload


def specs_to_dashboard_json(
    specs: Iterable[FigureSpec],
    *,
    legend: bool = True,
    strict: bool = True,
) -> str:
    """Serialize a dashboard snapshot with deterministic compact JSON."""
    payload = specs_to_dashboard_dict(specs, legend=legend, strict=strict)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate_dashboard_payload(payload: dict[str, Any]) -> None:
    """Validate the dashboard envelope shape and strict-JSON compatibility."""
    if not isinstance(payload, dict):
        raise ValueError("dashboard payload must be a dict")
    if payload.get("schema") != DASHBOARD_SCHEMA:
        raise ValueError(
            f"unsupported dashboard schema: {payload.get('schema')!r}"
        )
    version = payload.get("schema_version")
    if version != DASHBOARD_SCHEMA_VERSION or isinstance(version, bool):
        raise ValueError(
            f"unsupported dashboard schema_version: {version!r}"
        )
    if not isinstance(payload.get("engine_version"), str):
        raise ValueError("dashboard engine_version must be a string")
    revision = payload.get("revision")
    if not isinstance(revision, (int, np.integer)) or isinstance(revision, bool):
        raise ValueError("dashboard revision must be an integer")
    figures = payload.get("figures")
    if not isinstance(figures, list):
        raise ValueError("dashboard figures must be a list")

    for index, figure in enumerate(figures):
        _validate_figure(figure, f"figures[{index}]")

    try:
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"dashboard payload is not strict JSON: {exc}") from exc


def _validate_figure(figure: Any, seam: str) -> None:
    if not isinstance(figure, dict):
        raise ValueError(f"{seam} must be a dict")
    for key in ("figure_id", "template_hash"):
        if not isinstance(figure.get(key), str):
            raise ValueError(f"{seam}.{key} must be a string")
    definition = figure.get("definition")
    if not isinstance(definition, dict):
        raise ValueError(f"{seam}.definition must be a dict")
    data = figure.get("data")
    if not isinstance(data, dict):
        raise ValueError(f"{seam}.data must be a dict")
    columns = data.get("columns")
    if not isinstance(columns, dict):
        raise ValueError(f"{seam}.data.columns must be a dict")
    for name, values in columns.items():
        if not isinstance(values, list):
            raise ValueError(f"{seam}.data.columns[{name!r}] must be a list")
    if not isinstance(data.get("index"), list):
        raise ValueError(f"{seam}.data.index must be a list")
    children = figure.get("children", [])
    if not isinstance(children, list):
        raise ValueError(f"{seam}.children must be a list")
    for index, child in enumerate(children):
        if not isinstance(child, dict):
            raise ValueError(f"{seam}.children[{index}] must be a dict")
        if not isinstance(child.get("figure_id"), str):
            raise ValueError(f"{seam}.children[{index}].figure_id must be a string")
        if not isinstance(child.get("definition"), dict):
            raise ValueError(f"{seam}.children[{index}].definition must be a dict")


__all__ = [
    "DASHBOARD_SCHEMA",
    "DASHBOARD_SCHEMA_VERSION",
    "specs_to_dashboard_dict",
    "specs_to_dashboard_json",
    "validate_dashboard_payload",
]
