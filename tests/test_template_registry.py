"""
Tests for the Phase 15 template registry + recipe shape (engine/api.py).

Covers:
- TEMPLATES registry (plain dict, exporter-visible)
- register_template (add, override, rejects invalid args)
- get_template (returns builder, KeyError listing keys)
- recipe_from (FigureTemplate adaptation, recipe pass-through)
- No geodata / geochemmodel imports in engine/api.py
"""

import sys

import pytest

import geofig_engine
from geofig_engine.engine.api import (
    TEMPLATES,
    TemplateRecipe,
    get_template,
    recipe_from,
    register_template,
)
from geofig_engine.core.coord import CoordCartesian
from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatIdentity
from geofig_engine.templates.base import FigureTemplate


def sample_layer() -> Layer:
    return Layer(geom=GeomPoint(), stat=StatIdentity(), mapping={})


def make_builder(name: str = "x"):
    """A builder returning a TemplateRecipe (canonical registry shape)."""

    def builder(mapping=None, settings=None, **_):
        return TemplateRecipe(
            name=name,
            layers=[sample_layer()],
            coord=CoordCartesian(),
            default_settings={"figsize": (10, 6)},
        )

    return builder


@pytest.fixture(autouse=True)
def _isolate_registry():
    """Preserve/restore the global registry around each test."""
    saved = dict(TEMPLATES)
    TEMPLATES.clear()
    yield
    TEMPLATES.clear()
    TEMPLATES.update(saved)


# ---------------------------------------------------------------------------
# TEMPLATES registry — plain dict, exporter-visible
# ---------------------------------------------------------------------------

class TestTemplatesRegistry:
    def test_templates_is_plain_dict(self):
        assert isinstance(TEMPLATES, dict)

    def test_top_level_exports_registry(self):
        assert geofig_engine.TEMPLATES is TEMPLATES
        assert geofig_engine.register_template is register_template
        assert geofig_engine.get_template is get_template

    def test_registry_maps_keys_to_callables(self):
        builder = make_builder()
        register_template("x", builder)
        assert TEMPLATES["x"] is builder
        assert callable(TEMPLATES["x"])


# ---------------------------------------------------------------------------
# register_template — add / override
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_adds(self):
        builder = make_builder()
        register_template("x", builder)
        assert TEMPLATES["x"] is builder

    def test_reregister_overrides_without_error(self):
        b1 = make_builder("one")
        b2 = make_builder("two")
        register_template("x", b1)
        register_template("x", b2)
        assert TEMPLATES["x"] is b2
        assert get_template("x") is b2

    def test_rejects_non_string_name(self):
        with pytest.raises(ValueError):
            register_template(123, make_builder())

    def test_rejects_none_name(self):
        with pytest.raises(ValueError):
            register_template(None, make_builder())

    def test_rejects_non_callable_builder(self):
        with pytest.raises(ValueError):
            register_template("x", "not a callable")

    def test_rejects_none_builder(self):
        with pytest.raises(ValueError):
            register_template("x", None)


# ---------------------------------------------------------------------------
# get_template — builder lookup
# ---------------------------------------------------------------------------

class TestGetTemplate:
    def test_get_returns_builder(self):
        builder = make_builder()
        register_template("x", builder)
        assert get_template("x") is builder

    def test_get_unknown_raises_keyerror_listing_keys(self):
        register_template("known", make_builder())
        with pytest.raises(KeyError) as excinfo:
            get_template("nope")
        message = str(excinfo.value)
        assert "nope" in message
        assert "known" in message

    def test_get_unknown_with_empty_registry(self):
        with pytest.raises(KeyError):
            get_template("anything")


# ---------------------------------------------------------------------------
# recipe_from — FigureTemplate adaptation + recipe pass-through
# ---------------------------------------------------------------------------

class TestRecipeFrom:
    def test_figure_template_adapted_to_recipe(self):
        layer = sample_layer()
        template = FigureTemplate(
            name="my_template",
            layers=[layer],
            coord=CoordCartesian(),
            default_settings={"figsize": (10, 6), "grid": True},
        )
        recipe = recipe_from(template)
        assert isinstance(recipe, TemplateRecipe)
        assert recipe.name == "my_template"
        assert recipe.layers == [layer]
        assert recipe.coord is template.coord
        assert recipe.default_settings == {"figsize": (10, 6), "grid": True}

    def test_figure_template_defaults_adapted(self):
        template = FigureTemplate(name="legacy", layers=[sample_layer()])
        recipe = recipe_from(template)
        assert recipe.name == "legacy"
        assert isinstance(recipe.coord, CoordCartesian)
        assert recipe.default_settings == {}

    def test_template_recipe_passes_through_unchanged(self):
        recipe = TemplateRecipe(
            name="t",
            layers=[sample_layer()],
            coord=CoordCartesian(),
            default_settings={"grid": True},
        )
        assert recipe_from(recipe) is recipe

    def test_dict_recipe_passes_through_unchanged(self):
        recipe_dict = {
            "name": "t",
            "layers": [sample_layer()],
            "coord": CoordCartesian(),
            "default_settings": {"grid": True},
        }
        assert recipe_from(recipe_dict) is recipe_dict

    def test_duck_object_recipe_passes_through(self):
        class DuckRecipe:
            name = "t"
            layers = [sample_layer()]
            coord = CoordCartesian()
            default_settings = {}

        duck = DuckRecipe()
        assert recipe_from(duck) is duck

    def test_rejects_non_recipe(self):
        with pytest.raises(TypeError):
            recipe_from("not a recipe")

    def test_registered_builder_returning_figure_template_is_adaptable(self):
        def legacy_builder(mapping=None, settings=None, **_):
            return FigureTemplate(name="legacy", layers=[sample_layer()])

        register_template("legacy", legacy_builder)
        assert isinstance(recipe_from(get_template("legacy")()), TemplateRecipe)


# ---------------------------------------------------------------------------
# No upstream imports
# ---------------------------------------------------------------------------

class TestNoUpstreamImports:
    def test_engine_api_has_no_geodata_import(self):
        mod = sys.modules.get("geofig_engine.engine.api")
        if mod is None:
            pytest.skip("engine.api module not loaded")
        source_file = mod.__file__
        assert source_file is not None
        with open(source_file) as f:
            source = f.read()
        assert "import geodata" not in source
        assert "from geodata" not in source
        assert "import geochemmodel" not in source
        assert "from geochemmodel" not in source