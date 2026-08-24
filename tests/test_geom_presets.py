"""
Tests for the geom_presets package: models, validation, loader,
registry (queries/merge/hydration), isotope integration, and the
legacy MathFunction shim.
"""

import json

import pytest

from geofig_engine.core.geom import GeomAbline, GeomFunctionLine, GeomHSpan
from geofig_engine.core.layer import Layer
from geofig_engine.data.geom_presets import (
    GEOM_KINDS,
    GeomPreset,
    GeomPresetItem,
    GeomPresetLoader,
    GeomPresetLoadError,
    GeomPresetRegistry,
    get_geom_preset_registry,
    reset_geom_preset_registry,
)
from geofig_engine.data.geom_presets.validation import validate_preset_data
from geofig_engine.templates.isotope import _load_functions, isotope


def _preset_dict(**overrides):
    """Minimal valid preset dict with per-test overrides."""
    entry = {
        "id": "TEST_PRESET",
        "category": "water_isotope",
        "items": [
            {
                "geom": {"type": "function_line", "func": "8*x + 10"},
                "mapping": {"color": "black", "style": "--", "label": "Test"},
            }
        ],
    }
    entry.update(overrides)
    return entry


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestGeomPresetItem:
    def test_valid_item(self):
        item = GeomPresetItem(
            geom_type="function_line",
            params={"func": "8*x + 10"},
            mapping={"color": "black"},
        )
        assert item.geom_type == "function_line"
        assert item.zorder is None
        assert item.func_type is None

    def test_invalid_kind_rejected(self):
        with pytest.raises(ValueError, match="not in"):
            GeomPresetItem(geom_type="scatter", params={}, mapping={})

    def test_frozen(self):
        item = GeomPresetItem(geom_type="hspan", params={}, mapping={})
        with pytest.raises(Exception):  # noqa: B017 - FrozenInstanceError
            item.zorder = 1

    def test_bad_params_type_rejected(self):
        with pytest.raises(TypeError, match="params"):
            GeomPresetItem(geom_type="hspan", params=[], mapping={})

    def test_bool_zorder_rejected(self):
        with pytest.raises(TypeError, match="zorder"):
            GeomPresetItem(geom_type="hspan", params={}, mapping={}, zorder=True)


class TestGeomPreset:
    def _item(self):
        return GeomPresetItem(
            geom_type="function_line",
            params={"func": "x"},
            mapping={"label": "L"},
        )

    def test_valid_preset_and_properties(self):
        preset = GeomPreset(
            id="P1",
            category="water_isotope",
            items=(self._item(),),
            tags=("a", "b"),
            geospatial={"state": "ID"},
        )
        assert preset.state == "ID"
        assert preset.geom_kinds == {"function_line"}

    def test_empty_items_rejected(self):
        with pytest.raises(ValueError, match="items"):
            GeomPreset(id="P1", category="c", items=())

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError, match="id"):
            GeomPreset(id="", category="c", items=(self._item(),))

    def test_tags_must_be_tuple_of_str(self):
        with pytest.raises(TypeError, match="tags"):
            GeomPreset(id="P1", category="c", items=(self._item(),), tags=["x"])


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidatePresetData:
    def test_function_line_valid(self):
        preset = validate_preset_data(_preset_dict())
        assert preset.id == "TEST_PRESET"
        assert preset.items[0].func_type == "linear"

    def test_function_line_missing_func_rejected(self):
        entry = _preset_dict()
        entry["items"][0]["geom"] = {"type": "function_line"}
        with pytest.raises(ValueError, match="func"):
            validate_preset_data(entry)

    def test_function_line_undeclared_variable_rejected(self):
        entry = _preset_dict()
        entry["items"][0]["geom"]["func"] = "8*y + 10"
        with pytest.raises(ValueError, match="invalid expression"):
            validate_preset_data(entry)

    def test_function_line_bad_func_type_rejected(self):
        entry = _preset_dict()
        entry["items"][0]["geom"]["func_type"] = "quantum"
        with pytest.raises(ValueError, match="func_type"):
            validate_preset_data(entry)

    def test_unknown_geom_kind_rejected(self):
        entry = _preset_dict()
        entry["items"][0]["geom"] = {"type": "violin"}
        with pytest.raises(ValueError, match="not supported"):
            validate_preset_data(entry)

    def test_abline_slope_mode_valid(self):
        entry = _preset_dict()
        entry["items"][0] = {
            "geom": {"type": "abline", "slope": 2.5},
            "mapping": {"color": "gray"},
        }
        preset = validate_preset_data(entry)
        assert preset.items[0].params == {"slope": 2.5, "intercept": 0.0}

    def test_abline_two_point_mode_valid(self):
        entry = _preset_dict()
        entry["items"][0] = {
            "geom": {"type": "abline", "x1": 0, "y1": 0, "x2": 1, "y2": 3},
            "mapping": {"color": "gray"},
        }
        preset = validate_preset_data(entry)
        assert set(preset.items[0].params) == {"x1", "y1", "x2", "y2"}

    def test_abline_both_modes_rejected(self):
        entry = _preset_dict()
        entry["items"][0]["geom"] = {
            "type": "abline", "slope": 1, "intercept": 0, "x1": 0, "y1": 0, "x2": 1, "y2": 1,
        }
        with pytest.raises(ValueError, match="not both"):
            validate_preset_data(entry)

    def test_abline_no_mode_rejected(self):
        entry = _preset_dict()
        entry["items"][0]["geom"] = {"type": "abline"}
        with pytest.raises(ValueError, match="requires slope"):
            validate_preset_data(entry)

    @pytest.mark.parametrize("kind,bounds", [
        ("hspan", {"ymin": 5, "ymax": 1}),
        ("vspan", {"xmin": 5, "xmax": 1}),
        ("rect", {"xmin": 5, "xmax": 1, "ymin": 0, "ymax": 2}),
        ("rect", {"xmin": 0, "xmax": 1, "ymin": 2, "ymax": 2}),
    ])
    def test_reversed_or_equal_bounds_rejected(self, kind, bounds):
        entry = _preset_dict()
        entry["items"][0] = {"geom": {"type": kind}, "mapping": {**bounds, "color": "red"}}
        with pytest.raises(ValueError, match="must satisfy"):
            validate_preset_data(entry)

    def test_span_missing_required_mapping_rejected(self):
        entry = _preset_dict()
        entry["items"][0] = {"geom": {"type": "hspan"}, "mapping": {"ymin": 0}}
        with pytest.raises(ValueError, match="missing required keys"):
            validate_preset_data(entry)

    def test_unknown_mapping_key_rejected(self):
        entry = _preset_dict()
        entry["items"][0]["mapping"]["marker"] = "o"
        with pytest.raises(ValueError, match="unsupported keys"):
            validate_preset_data(entry)

    def test_non_scalar_mapping_value_rejected(self):
        entry = _preset_dict()
        entry["items"][0]["mapping"]["color"] = ["black"]
        with pytest.raises(ValueError, match="must be a scalar"):
            validate_preset_data(entry)

    def test_text_requires_position_and_label(self):
        entry = _preset_dict()
        entry["items"][0] = {
            "geom": {"type": "text"},
            "mapping": {"x": 1, "y": 2},
        }
        with pytest.raises(ValueError, match="missing required keys"):
            validate_preset_data(entry)

    def test_text_bbox_dict_allowed(self):
        entry = _preset_dict()
        entry["items"][0] = {
            "geom": {"type": "text"},
            "mapping": {
                "x": 1, "y": 2, "label": "note",
                "bbox": {"facecolor": "white"},
            },
        }
        preset = validate_preset_data(entry)
        assert preset.items[0].mapping["bbox"] == {"facecolor": "white"}

    def test_zorder_preserved(self):
        entry = _preset_dict()
        entry["items"][0]["zorder"] = 2
        assert validate_preset_data(entry).items[0].zorder == 2

    def test_metadata_extraction(self):
        entry = _preset_dict(
            tags=["t1"],
            metadata={
                "reference": "Ref",
                "description": "Desc",
                "valid_domain": "x > 0",
                "geospatial": {"state": "WA", "water_type": "meteoric"},
            },
        )
        preset = validate_preset_data(entry)
        assert preset.reference == "Ref"
        assert preset.valid_domain == "x > 0"
        assert preset.tags == ("t1",)
        assert preset.geospatial["water_type"] == "meteoric"


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class TestLoader:
    def test_bundled_water_isotope_loads_15(self):
        presets = GeomPresetLoader.load_file(
            GeomPresetLoader.bundled_dir() / "water_isotope.json"
        )
        assert len(presets) == 15
        assert all(isinstance(p, GeomPreset) for p in presets)
        ids = {p.id for p in presets}
        assert "GMWL" in ids and "ID_PRIESTRIVER" in ids

    def test_bundled_dir_glob_multi_category(self, tmp_path):
        (tmp_path / "a.json").write_text(json.dumps({"presets": [_preset_dict(id="A1")]}))
        (tmp_path / "b.json").write_text(json.dumps({"presets": [_preset_dict(id="B1")]}))
        presets = GeomPresetLoader.load_dir(tmp_path)
        assert [p.id for p in sorted(presets, key=lambda p: p.id)] == ["A1", "B1"]

    def test_load_dir_empty_raises(self, tmp_path):
        with pytest.raises(GeomPresetLoadError, match="No preset JSON files"):
            GeomPresetLoader.load_dir(tmp_path)

    def test_load_dir_missing_raises(self, tmp_path):
        with pytest.raises(GeomPresetLoadError, match="not found"):
            GeomPresetLoader.load_dir(tmp_path / "nope")

    def test_invalid_json_raises_with_path(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        with pytest.raises(GeomPresetLoadError, match="Invalid JSON"):
            GeomPresetLoader.load_file(bad)

    def test_root_schema_error(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"functions": []}))
        with pytest.raises(GeomPresetLoadError, match="'presets' key"):
            GeomPresetLoader.load_file(bad)

    def test_entry_error_annotates_index_and_id(self, tmp_path):
        entry = _preset_dict(id="BAD_ENTRY")
        entry["items"][0]["mapping"]["color"] = ["oops"]
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"presets": [entry]}))
        with pytest.raises(GeomPresetLoadError, match=r"index 0 \(id: BAD_ENTRY\)"):
            GeomPresetLoader.load_file(path)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def _make_registry():
    entries = [
        _preset_dict(id="W1", category="water_isotope"),
        _preset_dict(
            id="R1",
            category="reference",
            items=[{
                "geom": {"type": "abline", "slope": 1},
                "mapping": {"color": "gray"},
            }],
        ),
    ]
    return GeomPresetRegistry(validate_preset_data(e) for e in entries)


class TestRegistryQueries:
    def test_get_and_exists(self):
        reg = _make_registry()
        assert reg.exists("W1")
        assert not reg.exists("ZZZ")
        assert reg.get("W1").id == "W1"
        with pytest.raises(KeyError, match="not found in registry"):
            reg.get("ZZZ")

    def test_filter_by_category_tags_state(self):
        reg = _make_registry()
        assert [p.id for p in reg.filter(category="water_isotope")] == ["W1"]
        assert reg.filter(tags=["nope"]) == []

    def test_list_ids_and_metadata(self):
        reg = _make_registry()
        assert set(reg.list_ids()) == {"W1", "R1"}
        meta = reg.get_metadata()
        assert meta["total_presets"] == 2
        assert meta["by_category"] == {"water_isotope": 1, "reference": 1}


class TestRegistryMerge:
    def _write(self, tmp_path, name, *entries):
        path = tmp_path / name
        path.write_text(json.dumps({"presets": list(entries)}))
        return path

    def test_merge_new_ids(self, tmp_path):
        reg = _make_registry()
        path = self._write(tmp_path, "new.json", _preset_dict(id="NEW1"))
        assert reg.merge_path(path) == ["NEW1"]
        assert reg.exists("NEW1")

    def test_merge_conflict_raises_without_overwrite(self, tmp_path):
        reg = _make_registry()
        path = self._write(tmp_path, "conflict.json", _preset_dict(id="W1"))
        with pytest.raises(GeomPresetLoadError, match="already exist.*overwrite=True"):
            reg.merge_path(path)

    def test_merge_overwrite_replaces_in_place(self, tmp_path):
        reg = _make_registry()
        path = self._write(tmp_path, "conflict.json", _preset_dict(id="W1"))
        merged = reg.merge_path(path, overwrite=True)
        assert merged == ["W1"]
        assert reg.get_all()[0].id == "W1"          # order preserved
        assert reg.get_all()[-1].id == "R1"         # nothing appended
        assert reg.get_metadata()["total_presets"] == 2

    def test_duplicate_ids_at_construction_rejected(self):
        with pytest.raises(ValueError, match="Duplicate"):
            GeomPresetRegistry([validate_preset_data(_preset_dict())] * 2)


class TestHydration:
    def test_layers_for_function_line(self):
        reg = _make_registry()
        layers = reg.layers_for(["W1"])
        assert len(layers) == 1
        layer = layers[0]
        assert isinstance(layer, Layer)
        assert isinstance(layer.geom, GeomFunctionLine)
        assert layer.geom.func == "8*x + 10"
        assert layer.mapping == {"color": "black", "style": "--", "label": "Test"}

    def test_layers_for_abline_two_point(self):
        entry = _preset_dict(
            id="TP",
            items=[{
                "geom": {"type": "abline", "x1": 0, "y1": 1, "x2": 2, "y2": 5},
                "mapping": {"color": "gray"},
            }],
        )
        reg = GeomPresetRegistry([validate_preset_data(entry)])
        geom = reg.layers_for(["TP"])[0].geom
        assert isinstance(geom, GeomAbline)
        assert (geom.x1, geom.y1, geom.x2, geom.y2) == (0, 1, 2, 5)

    def test_item_zorder_flows_into_layer(self):
        entry = _preset_dict()
        entry["items"][0]["zorder"] = 3
        entry["items"][0]["geom"] = {"type": "hspan"}
        entry["items"][0]["mapping"] = {"ymin": 0, "ymax": 1}
        reg = GeomPresetRegistry([validate_preset_data(entry)])
        layer = reg.layers_for(["TEST_PRESET"])[0]
        assert isinstance(layer.geom, GeomHSpan)
        assert layer.zorder == 3

    def test_auto_layers_respects_kind_whitelist(self):
        reg = _make_registry()
        assert len(reg.auto_layers(category="water_isotope", geom_kinds=["function_line"])) == 1
        assert reg.auto_layers(category="water_isotope", geom_kinds=["hspan"]) == []


class TestGlobalSingleton:
    def setup_method(self):
        reset_geom_preset_registry()

    def teardown_method(self):
        reset_geom_preset_registry()

    def test_lazy_singleton_identity(self):
        reg1 = get_geom_preset_registry()
        reg2 = get_geom_preset_registry()
        assert reg1 is reg2

    def test_reset_forces_reload(self):
        reg1 = get_geom_preset_registry()
        reset_geom_preset_registry()
        reg2 = get_geom_preset_registry()
        assert reg1 is not reg2

    def test_bundled_contents_available(self):
        registry = get_geom_preset_registry()
        assert registry.exists("GMWL")
        assert len(registry.filter(category="water_isotope")) == 15


# ---------------------------------------------------------------------------
# Isotope integration
# ---------------------------------------------------------------------------


class TestIsotopeIntegration:
    def setup_method(self):
        reset_geom_preset_registry()

    def teardown_method(self):
        reset_geom_preset_registry()

    def test_load_functions_empty(self):
        assert _load_functions(functions=[]) == []

    def test_load_functions_auto_filter_matches_registry(self):
        registry = get_geom_preset_registry()
        n = len(registry.filter(category="water_isotope"))
        layers = _load_functions(auto_filter=True)
        assert len(layers) == n
        assert all(isinstance(l, Layer) for l in layers)

    def test_load_functions_specific(self):
        layers = _load_functions(functions=["GMWL", "ID_FALLS"])
        assert len(layers) == 2
        assert layers[0].geom.label == "GMWL"

    def test_load_functions_invalid_id(self):
        with pytest.raises(KeyError, match="not found in registry"):
            _load_functions(functions=["NONEXISTENT"])

    def test_load_functions_wrong_category_rejected(self, tmp_path):
        get_geom_preset_registry().merge_path(
            _write_tmp(tmp_path, _preset_dict(id="REF_LINE", category="reference"))
        )
        with pytest.raises(ValueError, match="not accepted"):
            _load_functions(functions=["REF_LINE"])

    def test_isotope_template_layer_count(self):
        registry = get_geom_preset_registry()
        n_funcs = len(registry.filter(category="water_isotope"))
        template = isotope()
        assert len(template.layers) == n_funcs + 1  # func layers + data layer
        assert template.layers[-1].geom.__class__.__name__ == "GeomPoint"

    def test_isotope_no_functions(self):
        template = isotope(functions=[], auto_filter=False)
        assert len(template.layers) == 1


def _write_tmp(tmp_path, entry):
    path = tmp_path / "extra.json"
    path.write_text(json.dumps({"presets": [entry]}))
    return path


# ---------------------------------------------------------------------------
# Legacy shim parity
# ---------------------------------------------------------------------------


class TestLegacyShim:
    def setup_method(self):
        reset_geom_preset_registry()
        from geofig_engine.data.registry import FunctionLoader
        FunctionLoader._cache = None

    def teardown_method(self):
        from geofig_engine.data.registry import FunctionLoader
        FunctionLoader._cache = None
        reset_geom_preset_registry()

    def test_loader_returns_mathfunctions(self):
        from geofig_engine.data.functions import MathFunction
        from geofig_engine.data.registry import FunctionLoader

        functions = FunctionLoader.load()
        assert len(functions) == 15
        assert all(isinstance(f, MathFunction) for f in functions)

    def test_gmwl_roundtrip_content(self):
        from geofig_engine.data.registry import FunctionLoader

        gmwl = next(f for f in FunctionLoader.load() if f.id == "GMWL")
        assert gmwl.expression == "8*x + 10"
        assert str(gmwl.category.value) == "water_isotope"
        assert str(gmwl.func_type.value) == "linear"
        assert gmwl.variables == ("x",)
        assert gmwl.color == "black"
        assert gmwl.linestyle == "--"
        assert gmwl.label == "GMWL"
        assert gmwl.reference == "Craig, 1961"
        assert gmwl.geospatial.water_type == "meteoric"

    def test_state_filtering_preserved(self):
        from geofig_engine.data.registry import get_function_registry

        registry = get_function_registry()
        assert len(registry.get_by_state("ID")) == 9
        assert len(registry.get_by_state("WA")) == 4

    def test_singleton_identity_after_reset(self):
        from geofig_engine.data.registry import (
            FunctionLoader,
            get_function_registry,
        )

        FunctionLoader.load()
        assert get_function_registry() is get_function_registry()


# ---------------------------------------------------------------------------
# Package sanity
# ---------------------------------------------------------------------------


def test_geom_kinds_whitelist():
    assert GEOM_KINDS == (
        "function_line", "abline", "hspan", "vspan", "rect", "text",
    )
