import pytest

from geofig_engine.core.geom import (
    Geom,
    GeomPoint,
    GeomLine,
    GeomFunctionLine,
    GeomBar,
    GeomArea,
    GeomRibbon,
    GeomText,
    GeomErrorbar,
    Channel,
)


class TestGeomBase:
    def test_requires_non_empty_name(self):
        with pytest.raises(ValueError, match="non-empty string"):
            Geom(name="", required_channels=("x", "y"))

    def test_requires_valid_channels(self):
        with pytest.raises(ValueError, match="Invalid channel"):
            Geom(name="test", required_channels=("invalid_channel",))

    def test_accepts_concrete_geom(self):
        geom = Geom(name="test", required_channels=("x", "y"), optional_channels=("color",))
        assert geom.name == "test"
        assert geom.required_channels == ("x", "y")
        assert geom.optional_channels == ("color",)


class TestGeomPoint:
    def test_defaults(self):
        g = GeomPoint()
        assert g.name == "point"
        assert "x" in g.required_channels
        assert "y" in g.required_channels
        assert "color" in g.optional_channels
        assert "marker" in g.optional_channels

    def test_is_frozen(self):
        g = GeomPoint()
        with pytest.raises(AttributeError):
            g.name = "bar"

    def test_has_no_func_param(self):
        g = GeomPoint()
        assert not hasattr(g, "func")


class TestGeomLine:
    def test_defaults(self):
        g = GeomLine()
        assert g.name == "line"
        assert "x" in g.required_channels
        assert "y" in g.required_channels
        assert "style" in g.optional_channels
        assert "width" in g.optional_channels


class TestGeomFunctionLine:
    def test_defaults(self):
        g = GeomFunctionLine()
        assert g.name == "function_line"
        assert g.func == ""
        assert g.label is None

    def test_with_func_and_label(self):
        g = GeomFunctionLine(func="2*x + 1", label="GMWL")
        assert g.func == "2*x + 1"
        assert g.label == "GMWL"

    def test_required_channels_include_x(self):
        g = GeomFunctionLine()
        assert "x" in g.required_channels
        assert "y" not in g.required_channels


class TestGeomBar:
    def test_defaults(self):
        g = GeomBar()
        assert g.name == "bar"
        assert "x" in g.required_channels
        assert "y" in g.required_channels


class TestGeomRibbon:
    def test_defaults(self):
        g = GeomRibbon()
        assert g.name == "ribbon"
        assert "ymin" in g.required_channels
        assert "ymax" in g.required_channels


class TestGeomText:
    def test_defaults(self):
        g = GeomText()
        assert g.name == "text"
        assert "label" in g.required_channels


class TestGeomErrorbar:
    def test_defaults(self):
        g = GeomErrorbar()
        assert g.name == "errorbar"
        assert "ymin" in g.required_channels
        assert "ymax" in g.required_channels


class TestChannel:
    def test_enum_values(self):
        assert Channel.X.value == "x"
        assert Channel.COLOR.value == "color"
        assert Channel.LABEL.value == "label"
        assert Channel.FUNC.value == "func"

    def test_all_channels_covered(self):
        names = {c.value for c in Channel}
        assert "x" in names
        assert "y" in names
        assert "color" in names
