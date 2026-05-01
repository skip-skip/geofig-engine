"""
Tests for FigEngine template classes.
"""

import pytest
import pandas as pd

from geofig_engine.templates import BivariateTemplate, FigureTemplate
from geofig_engine.core.spec import FigureSpec


class TestFigureTemplateBase:
    def test_validate_mappings_rejects_missing_required(self):
        template = FigureTemplate(
            name="test",
            required_mappings=("x", "y"),
            optional_mappings=("color",),
        )

        with pytest.raises(ValueError, match="requires mapping 'x'"):
            template.validate_mappings({"y": ["y"]})

    def test_validate_mappings_rejects_unsupported_mapping(self):
        template = FigureTemplate(
            name="test",
            required_mappings=("x",),
            optional_mappings=("color",),
        )

        with pytest.raises(ValueError, match="Unsupported mapping 'z'"):
            template.validate_mappings({"x": ["x"], "z": ["z"]})

    def test_supported_mappings_combines_required_and_optional(self):
        template = FigureTemplate(
            name="test",
            required_mappings=("x",),
            optional_mappings=("color", "marker"),
        )

        assert template.supported_mappings == ("color", "marker", "x")


class TestBivariateTemplate:
    @pytest.fixture
    def data(self) -> pd.DataFrame:
        return pd.DataFrame({"x": [1, 2], "y": [3, 4], "group": ["A", "B"]})

    def test_default_settings_are_applied(self, data):
        template = BivariateTemplate()
        spec = template.build_spec(
            data=data,
            mappings={"x": ["x"], "y": ["y"]},
            settings={"title": "Plot"},
            context={"group": "A"},
        )

        assert isinstance(spec, FigureSpec)
        assert spec.template_name == "bivariate"
        assert spec.settings["figsize"] == (10, 6)
        assert spec.settings["title"] == "Plot"

    def test_build_spec_requires_x_and_y(self, data):
        template = BivariateTemplate()

        with pytest.raises(ValueError, match="requires mapping 'x'"):
            template.build_spec(
                data=data,
                mappings={"y": ["y"]},
                settings={},
                context={},
            )

    def test_build_spec_rejects_unsupported_mapping(self, data):
        template = BivariateTemplate()

        with pytest.raises(ValueError, match="Unsupported mapping 'z'"):
            template.build_spec(
                data=data,
                mappings={"x": ["x"], "y": ["y"], "z": ["group"]},
                settings={},
                context={},
            )

    def test_build_spec_accepts_optional_color(self, data):
        template = BivariateTemplate()
        spec = template.build_spec(
            data=data,
            mappings={"x": ["x"], "y": ["y"], "color": ["group"]},
            settings={},
            context={},
        )

        assert spec.mappings["color"] == ["group"]
