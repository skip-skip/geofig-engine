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
    GeomBox,
    GeomViolin,
    GeomStepLine,
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
        assert g.jitter == 0.0
        assert g.dodge == 0.0

    def test_custom_params(self):
        g = GeomPoint(jitter=0.1, dodge=0.8)
        assert g.jitter == 0.1
        assert g.dodge == 0.8

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


class TestGeomBox:
    def test_defaults(self):
        g = GeomBox()
        assert g.name == "box"
        assert "x" in g.required_channels
        assert "y" in g.required_channels
        assert g.showfliers is True
        assert g.showmeans is False
        assert g.show_n is False
        assert g.box_width == 0.8
        assert g.sort_mode == "none"

    def test_custom_params(self):
        g = GeomBox(showfliers=False, showmeans=True, box_width=0.5, sort_mode="forward")
        assert g.showfliers is False
        assert g.showmeans is True
        assert g.box_width == 0.5
        assert g.sort_mode == "forward"

    def test_is_frozen(self):
        g = GeomBox()
        with pytest.raises(AttributeError):
            g.box_width = 0.5


class TestGeomViolin:
    def test_defaults(self):
        g = GeomViolin()
        assert g.name == "violin"
        assert "x" in g.required_channels
        assert "y" in g.required_channels
        assert g.show_medians is True
        assert g.sort_mode == "none"

    def test_custom_params(self):
        g = GeomViolin(show_medians=False, sort_mode="reverse")
        assert g.show_medians is False
        assert g.sort_mode == "reverse"


class TestGeomStepLine:
    def test_defaults(self):
        g = GeomStepLine()
        assert g.name == "step_line"
        assert g.where == "pre"

    def test_custom_where(self):
        g = GeomStepLine(where="mid")
        assert g.where == "mid"


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


class TestGeomBarPosition:
    def test_default_position_is_identity(self):
        assert GeomBar().position == "identity"

    def test_accepts_stack(self):
        assert GeomBar(position="stack").position == "stack"

    def test_accepts_fill(self):
        assert GeomBar(position="fill").position == "fill"

    def test_rejects_invalid_position(self):
        with pytest.raises(ValueError, match="position must be"):
            GeomBar(position="dodge")
