"""
Phase 19 wp2 — versioned browser-safe dashboard snapshots.

Covers envelope/determinism, spec-only definitions, stable identities, strict
JSON normalization, renderer-free legend extraction, and validation.
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import geofig_engine
from geofig_engine import build_template_specs
from geofig_engine import specs_to_dashboard_dict as root_specs_to_dict
from geofig_engine import specs_to_dashboard_json as root_specs_to_json
from geofig_engine.core.coord import CoordPolar
from geofig_engine.core.facet import FacetWrap
from geofig_engine.core.geom import GeomLine
from geofig_engine.core.iterator import DimensionIterator
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.spec import FigureSpec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.renderers.matplotlib.legend import LegendAccumulator
from geofig_engine.serialize import (
    DASHBOARD_SCHEMA,
    DASHBOARD_SCHEMA_VERSION,
    apply_dashboard_patch,
    diff_dashboard_payload,
    specs_to_dashboard_dict,
    specs_to_dashboard_json,
    validate_dashboard_patch,
    validate_dashboard_payload,
)
from geofig_engine.serialize import _legend as legend_module
from geofig_engine.serialize import dashboard as dashboard_module
from geofig_engine.templates import bivariate
from test_pipeline_templates import ALL_RENDER_CASES, make_df


def _iter_dicts(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _iter_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_dicts(item)


def _assert_definition_is_structural(definition, data):
    for node in _iter_dicts(definition):
        assert "$inline" not in node
        for channel, reference in node.get("visual_mapping", {}).items():
            if isinstance(reference, dict) and "$column" in reference:
                assert reference["$column"] in data["columns"], channel
    for values in data["columns"].values():
        assert len(values) == len(data["index"])


def _make_legend_spec():
    frame = pd.DataFrame({
        "group": ["A", "B", "A", "B"],
        "x": [1.0, 2.0, 3.0, 4.0],
        "y": [1.0, 2.0, 3.0, 4.0],
    })
    return FigureSpec(
        data=frame,
        mappings={},
        settings={},
        context={},
        template_name="legend",
        layers=[
            LayerSpec(
                geom=GeomLine(),
                stat=StatIdentity(),
                visual_mapping={
                    "x": pd.Series([1.0, 2.0, 3.0, 4.0], name="x"),
                    "y": pd.Series([1.0, 2.0, 3.0, 4.0], name="y"),
                    "color": pd.Series(["red", "blue", "red", "blue"], name="group"),
                    "marker": pd.Series(["o", "s", "o", "s"], name="group"),
                },
            )
        ],
    )


class TestDashboardEnvelope:
    def test_reexports_match_serialize_helpers(self):
        assert root_specs_to_dict is specs_to_dashboard_dict
        assert root_specs_to_json is specs_to_dashboard_json
        assert geofig_engine.specs_to_dashboard_dict is specs_to_dashboard_dict

    def test_envelope_has_schema_version_revision_and_figures(self):
        specs = build_template_specs(make_df(), bivariate(mapping={"x": "x", "y": "y"}))

        payload = specs_to_dashboard_dict(specs)
        text = specs_to_dashboard_json(specs)

        assert payload["schema"] == DASHBOARD_SCHEMA
        assert payload["schema_version"] == DASHBOARD_SCHEMA_VERSION
        assert payload["engine_version"] == "0.5.0"
        assert isinstance(payload["revision"], int)
        assert payload["revision"] >= 0
        assert len(payload["figures"]) == len(specs)
        assert json.loads(text) == payload
        validate_dashboard_payload(payload)

    def test_legend_false_omits_legend_key(self):
        specs = build_template_specs(make_df(), bivariate(mapping={"x": "x", "y": "y"}))

        payload = specs_to_dashboard_dict(specs, legend=False)

        assert "legend" not in payload["figures"][0]
        assert "legend" in specs_to_dashboard_dict(specs)["figures"][0]

    def test_validator_rejects_bad_envelopes(self):
        specs = build_template_specs(make_df(), bivariate(mapping={"x": "x", "y": "y"}))
        base = specs_to_dashboard_dict(specs)

        changed = dict(base, schema="other/dashboard")
        with pytest.raises(ValueError, match="unsupported dashboard schema"):
            validate_dashboard_payload(changed)

        changed = dict(base, schema_version=2)
        with pytest.raises(ValueError, match="schema_version"):
            validate_dashboard_payload(changed)

        changed = dict(base, figures="not-a-list")
        with pytest.raises(ValueError, match="figures must be a list"):
            validate_dashboard_payload(changed)


class TestSeededKeySnapshots:
    @pytest.mark.parametrize("key,data_factory,mapping", ALL_RENDER_CASES)
    def test_full_snapshot_for_every_seeded_key(self, key, data_factory, mapping):
        specs = build_template_specs(data_factory(), key, mapping=mapping)

        payload = specs_to_dashboard_dict(specs)
        text = specs_to_dashboard_json(specs)

        assert len(payload["figures"]) == len(specs)
        for figure, spec in zip(payload["figures"], specs):
            assert isinstance(figure["figure_id"], str)
            assert isinstance(figure["template_hash"], str)
            assert figure["definition"]["template_name"] == spec.template_name
            assert len(figure["definition"]["layers"]) == len(spec.layers)
            assert len(figure["children"]) == len(spec.children)
            _assert_definition_is_structural(
                figure["definition"], figure["data"]
            )
        assert json.loads(text) == payload

    def test_piper_children_are_included(self):
        key, factory, mapping = next(
            case for case in ALL_RENDER_CASES if case[0] == "piper"
        )
        specs = build_template_specs(factory(), key, mapping=mapping)

        figure = specs_to_dashboard_dict(specs)["figures"][0]

        assert len(figure["children"]) == 3
        assert len(figure["definition"]["children"]) == 3
        assert all(child["definition"]["layers"] for child in figure["children"])
        assert all(child["data_ref"] == "$parent" for child in figure["children"])

    def test_facet_and_iterator_specs_snapshot(self):
        iterator = DimensionIterator(
            channel="group",
            dimensions=["group"],
            mode=DimensionIterator.Mode.VALUE,
        )
        specs = build_template_specs(
            make_df(),
            bivariate(mapping={"x": "x", "y": "y"}),
            iterators=[iterator],
            facet=FacetWrap(by="group"),
        )

        payload = specs_to_dashboard_dict(specs)

        assert len(payload["figures"]) == 2
        assert [figure["definition"]["context"]["group"] for figure in payload["figures"]] == ["A", "B"]
        for figure in payload["figures"]:
            assert figure["definition"]["facet"]["type"] == "wrap"
            _assert_definition_is_structural(figure["definition"], figure["data"])
        validate_dashboard_payload(payload)

    def test_byte_identical_for_same_specs(self):
        specs = build_template_specs(make_df(), bivariate(mapping={"x": "x", "y": "y"}))

        assert specs_to_dashboard_json(specs) == specs_to_dashboard_json(specs)
        assert specs_to_dashboard_dict(specs) == specs_to_dashboard_dict(specs)


class TestStableIdentities:
    @staticmethod
    def _hash_for(specs):
        return specs_to_dashboard_dict(specs, legend=False)["figures"][0]["template_hash"]

    @staticmethod
    def _revision_for(specs):
        return specs_to_dashboard_dict(specs, legend=False)["revision"]

    def test_data_only_change_keeps_hash_but_changes_revision(self):
        template = bivariate(mapping={"x": "x", "y": "y"})
        before = build_template_specs(make_df(), template)
        frame = make_df()
        frame["x"] = frame["x"] * 2
        after = build_template_specs(frame, template)

        assert self._hash_for(before) == self._hash_for(after)
        assert self._revision_for(before) != self._revision_for(after)

    def test_layer_settings_and_coord_changes_change_hash(self):
        spec = build_template_specs(
            make_df(), bivariate(mapping={"x": "x", "y": "y"})
        )[0]
        baseline = self._hash_for([spec])

        changed_settings = dataclasses.replace(spec, settings={"title": "other"})
        changed_coord = dataclasses.replace(spec, coord=CoordPolar())
        changed_layers = dataclasses.replace(spec, layers=list(spec.layers)[:-1])

        assert self._hash_for([changed_settings]) != baseline
        assert self._hash_for([changed_coord]) != baseline
        assert self._hash_for([changed_layers]) != baseline

    def test_figure_and_layer_ids_are_stable_and_context_sensitive(self):
        template = bivariate(mapping={"x": "x", "y": "y"})
        iterator = DimensionIterator(
            channel="group",
            dimensions=["group"],
            mode=DimensionIterator.Mode.VALUE,
        )
        specs = build_template_specs(make_df(), template, iterators=[iterator])
        again = build_template_specs(make_df(), template, iterators=[iterator])

        payload = specs_to_dashboard_dict(specs, legend=False)
        repeated = specs_to_dashboard_dict(again, legend=False)
        figure_ids = [figure["figure_id"] for figure in payload["figures"]]
        layer_ids = [
            layer["layer_id"]
            for figure in payload["figures"]
            for layer in figure["definition"]["layers"]
        ]

        assert len(set(figure_ids)) == len(specs)
        assert len(set(layer_ids)) == len(layer_ids)
        assert figure_ids == [
            figure["figure_id"] for figure in repeated["figures"]
        ]
        assert layer_ids == [
            layer["layer_id"]
            for figure in repeated["figures"]
            for layer in figure["definition"]["layers"]
        ]


class TestStrictBrowserJson:
    def test_non_native_values_are_normalized(self):
        spec = FigureSpec(
            data=pd.DataFrame({"x": [1.0, 2.0]}),
            mappings={},
            settings={},
            context={
                "nan": float("nan"),
                "inf": float("inf"),
                "nat": pd.NaT,
                "when": pd.Timestamp("2024-01-02T03:04:05"),
                "scalar": np.int64(7),
                "pair": (1, 2),
            },
            template_name="strict-values",
        )

        payload = specs_to_dashboard_dict([spec])
        context = payload["figures"][0]["definition"]["context"]
        text = specs_to_dashboard_json([spec])

        assert context["nan"] is None
        assert context["inf"] is None
        assert context["nat"] is None
        assert context["when"] == "2024-01-02T03:04:05"
        assert context["scalar"] == 7
        assert isinstance(context["scalar"], int)
        assert context["pair"] == [1, 2]
        assert "NaN" not in text and "Infinity" not in text

    def test_callable_is_rejected_with_seam_and_source(self):
        def forbidden():
            return 1

        spec = FigureSpec(
            data=pd.DataFrame({"x": [1.0]}),
            mappings={},
            settings={},
            context={"bad": forbidden},
            template_name="callable",
        )

        with pytest.raises(TypeError, match=r"context\.bad.*forbidden"):
            specs_to_dashboard_dict([spec])


class TestRendererFreeLegend:
    def test_legend_matches_accumulator_groups(self):
        spec = _make_legend_spec()

        ours = [
            dataclasses.asdict(group)
            for group in legend_module.extract_legend([spec])
        ]
        accumulator = LegendAccumulator()
        accumulator.add_from_spec(spec)
        expected = [dataclasses.asdict(group) for group in accumulator.groups]

        assert ours == expected

        payload = specs_to_dashboard_dict([spec])
        assert payload["figures"][0]["legend"] == ours

    def test_legend_path_has_no_pyplot_or_renderer_import(self):
        sources = (
            Path(dashboard_module.__file__).read_text(encoding="utf-8")
            + Path(legend_module.__file__).read_text(encoding="utf-8")
        )

        imports = [
            line.strip()
            for line in sources.splitlines()
            if re.match(r"^\s*(from|import)\s", line)
        ]
        assert not any("pyplot" in line for line in imports)
        assert not any("geofig_engine.renderers" in line for line in imports)


class TestPatchEndToEnd:
    def test_build_snapshot_mutate_diff_apply_compare(self):
        template = bivariate(mapping={"x": "x", "y": "y"})
        old_specs = build_template_specs(make_df(), template)
        old_payload = specs_to_dashboard_dict(old_specs)

        frame = make_df()
        frame["y"] = frame["y"] * 4
        new_specs = build_template_specs(frame, template)
        new_payload = specs_to_dashboard_dict(new_specs)

        patch = diff_dashboard_payload(old_payload, new_payload)
        validate_dashboard_patch(patch)
        result = apply_dashboard_patch(old_payload, patch)

        assert result == new_payload
        assert all(
            op["op"] in {"replace_data", "append_data"}
            for op in patch["operations"]
        )
        assert result["figures"][0]["template_hash"] == (
            new_payload["figures"][0]["template_hash"]
        )
