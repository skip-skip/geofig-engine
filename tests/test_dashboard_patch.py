"""
Phase 19 wp3 — transport-agnostic dashboard patch protocol.

Covers data/definition/settings/removal diffs, exact snapshot reproduction,
revision guards, validation errors, and input immutability.
"""

from __future__ import annotations

import copy
import dataclasses

import pandas as pd
import pytest

import geofig_engine
from geofig_engine import build_template_specs
from geofig_engine.core.coord import CoordPolar
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.serialize import (
    DASHBOARD_PATCH_SCHEMA,
    DASHBOARD_PATCH_SCHEMA_VERSION,
    apply_dashboard_patch,
    diff_dashboard_payload,
    specs_to_dashboard_dict,
    validate_dashboard_patch,
)
from test_pipeline_templates import make_df


def _bivariate(frame=None, **settings):
    if frame is None:
        frame = make_df()
    return build_template_specs(
        frame,
        "bivariate",
        mapping={"x": "x", "y": "y"},
        settings=settings,
    )


def _snapshot(specs):
    return specs_to_dashboard_dict(specs)


def _patch_ops(patch):
    assert "payload" not in patch
    return patch["operations"]


def _valid_envelope(operations, revision=99, base_revision=None):
    patch = {
        "schema": DASHBOARD_PATCH_SCHEMA,
        "schema_version": DASHBOARD_PATCH_SCHEMA_VERSION,
        "revision": revision,
        "operations": operations,
    }
    if base_revision is not None:
        patch["base_revision"] = base_revision
    return patch


class TestDataPatches:
    def test_data_only_update_keeps_template_hash(self):
        old = _snapshot(_bivariate())
        frame = make_df()
        frame["x"] = frame["x"] * 2
        new = _snapshot(_bivariate(frame))

        patch = diff_dashboard_payload(old, new)
        operations = _patch_ops(patch)
        result = apply_dashboard_patch(old, patch)

        assert {op["op"] for op in operations} <= {"replace_data", "append_data"}
        assert all("definition" not in op for op in operations)
        assert old["figures"][0]["template_hash"] == new["figures"][0]["template_hash"]
        assert result == new
        assert old["figures"][0]["data"] != new["figures"][0]["data"]

    def test_append_rows_reproduces_fresh_snapshot(self):
        old = _snapshot(_bivariate())
        frame = make_df()
        extra = pd.DataFrame({
            "id": [5, 6],
            "x": [9.0, 10.0],
            "y": [11.0, 12.0],
            "group": ["C", "C"],
            "cat": ["e", "f"],
            "val": [8.0, 9.0],
            "x_label": ["e", "f"],
            "y_label": ["E", "F"],
        }, index=[4, 5])
        new = _snapshot(_bivariate(pd.concat([frame, extra])))

        patch = diff_dashboard_payload(old, new)
        result = apply_dashboard_patch(old, patch)

        assert [op["op"] for op in _patch_ops(patch)] == ["append_data"]
        assert _patch_ops(patch)[0]["index"] == [4, 5]
        assert result == new


class TestDefinitionPatches:
    def test_definition_update_carries_new_hash(self):
        old = _snapshot(_bivariate())
        specs = _bivariate()
        changed = dataclasses.replace(specs[0], coord=CoordPolar())
        new = _snapshot([changed])

        patch = diff_dashboard_payload(old, new)
        result = apply_dashboard_patch(old, patch)
        operations = _patch_ops(patch)

        assert [op["op"] for op in operations] == ["replace_definition"]
        assert operations[0]["template_hash"] == new["figures"][0]["template_hash"]
        assert operations[0]["definition"]["coord"] == new["figures"][0]["definition"]["coord"]
        assert result == new

    def test_settings_update_only_changes_settings_and_layout(self):
        specs = _bivariate(title="Original")
        old = _snapshot(specs)
        changed = dataclasses.replace(
            specs[0], settings={**specs[0].settings, "title": "Patched"}
        )
        new = _snapshot([changed])

        patch = diff_dashboard_payload(old, new)
        operations = _patch_ops(patch)
        result = apply_dashboard_patch(old, patch)

        assert [op["op"] for op in operations] == ["update_settings"]
        assert operations[0]["settings"]["title"] == "Patched"
        assert result == new
        assert result["figures"][0]["data"] == old["figures"][0]["data"]
        old_def = old["figures"][0]["definition"]
        new_def = result["figures"][0]["definition"]
        stripped_old = {k: v for k, v in old_def.items() if k not in {"settings", "layout"}}
        stripped_new = {k: v for k, v in new_def.items() if k not in {"settings", "layout"}}
        assert stripped_old == stripped_new


class TestFigureLifecyclePatches:
    @staticmethod
    def _iterated_specs():
        iterator = DimensionIterator(
            channel="group",
            dimensions=["group"],
            mode=DimensionIterator.Mode.VALUE,
        )
        return build_template_specs(
            make_df(), "bivariate", mapping={"x": "x", "y": "y"}, iterators=[iterator]
        )

    def test_remove_figure_reproduces_fresh_snapshot(self):
        specs = self._iterated_specs()
        old = _snapshot(specs)
        new = _snapshot(specs[:1])

        patch = diff_dashboard_payload(old, new)
        result = apply_dashboard_patch(old, patch)

        assert [op["op"] for op in _patch_ops(patch)] == ["remove_figure"]
        assert len(result["figures"]) == 1
        assert result == new

    def test_added_figure_uses_full_snapshot_fallback(self):
        specs = self._iterated_specs()
        old = _snapshot(specs[:1])
        new = _snapshot(specs)

        patch = diff_dashboard_payload(old, new)
        result = apply_dashboard_patch(old, patch)

        assert "payload" in patch
        assert "operations" not in patch
        assert result == new


class TestPatchValidation:
    def test_stale_base_revision_is_rejected(self):
        old = _snapshot(_bivariate())
        new = _snapshot(_bivariate(make_df().assign(x=lambda frame: frame["x"] * 2)))
        patch = diff_dashboard_payload(old, new)
        stale = dict(patch, base_revision=old["revision"] + 12345)
        before = copy.deepcopy(old)

        with pytest.raises(ValueError, match="stale or out-of-order dashboard patch"):
            apply_dashboard_patch(old, stale)
        assert old == before

    def test_unknown_figure_id_is_rejected_on_apply(self):
        old = _snapshot(_bivariate())
        patch = _valid_envelope([
            {"op": "remove_figure", "figure_id": "figure-does-not-exist"}
        ])

        with pytest.raises(ValueError, match="unknown figure_id"):
            apply_dashboard_patch(old, patch)

    def test_unknown_operation_is_rejected_on_validation(self):
        patch = _valid_envelope([
            {"op": "teleport_figure", "figure_id": "figure-1"}
        ])

        with pytest.raises(ValueError, match="unknown dashboard patch operation"):
            validate_dashboard_patch(patch)

    def test_unknown_schema_version_is_rejected(self):
        patch = _valid_envelope([])
        patch["schema_version"] = 2

        with pytest.raises(ValueError, match="schema_version"):
            validate_dashboard_patch(patch)

    def test_unknown_schema_is_rejected(self):
        patch = _valid_envelope([])
        patch["schema"] = "other/patch"

        with pytest.raises(ValueError, match="unsupported dashboard patch schema"):
            validate_dashboard_patch(patch)

    def test_revision_fields_must_be_integers(self):
        patch = _valid_envelope([])
        patch["revision"] = "99"
        with pytest.raises(ValueError, match="revision must be an integer"):
            validate_dashboard_patch(patch)

        patch = _valid_envelope([], base_revision=0)
        patch["base_revision"] = "0"
        with pytest.raises(ValueError, match="base_revision must be an integer"):
            validate_dashboard_patch(patch)

    def test_matching_base_revision_is_accepted(self):
        old = _snapshot(_bivariate())
        new = _snapshot(_bivariate(make_df().assign(y=lambda frame: frame["y"] * 2)))
        patch = diff_dashboard_payload(old, new)
        assert patch["base_revision"] == old["revision"]
        assert patch["revision"] == new["revision"]

        assert apply_dashboard_patch(old, patch) == new

    def test_missing_required_field_is_rejected(self):
        patch = _valid_envelope([{"op": "replace_data", "figure_id": "f"}])

        with pytest.raises(ValueError, match="missing required field 'columns'"):
            validate_dashboard_patch(patch)

    def test_apply_does_not_mutate_inputs(self):
        old = _snapshot(_bivariate())
        new = _snapshot(_bivariate(make_df().assign(y=lambda frame: frame["y"] * 3)))
        patch = diff_dashboard_payload(old, new)
        old_before = copy.deepcopy(old)
        patch_before = copy.deepcopy(patch)

        result = apply_dashboard_patch(old, patch)

        assert old == old_before
        assert patch == patch_before
        assert result == new
        assert result is not old


class TestPatchExports:
    def test_root_and_serialize_exports_match(self):
        assert geofig_engine.diff_dashboard_payload is diff_dashboard_payload
        assert geofig_engine.apply_dashboard_patch is apply_dashboard_patch
        assert geofig_engine.validate_dashboard_patch is validate_dashboard_patch
