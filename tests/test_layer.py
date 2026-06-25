import pytest

from geofig_engine.core.layer import Layer, LayerSpec
from geofig_engine.core.geom import GeomPoint, GeomLine, Geom
from geofig_engine.core.stat import StatIdentity, Stat
from geofig_engine.core.scale import ScaleContinuous, ScaleOrdinal
from geofig_engine.utils.typing import DimensionSelector


class TestLayer:
    def test_defaults(self):
        layer = Layer(geom=GeomPoint())
        assert isinstance(layer.geom, GeomPoint)
        assert isinstance(layer.stat, StatIdentity)
        assert layer.mapping == {}
        assert layer.scales is None
        assert layer.data_override is None

    def test_with_mapping_and_scales(self):
        layer = Layer(
            geom=GeomPoint(),
            stat=StatIdentity(),
            mapping={"x": "chem1", "y": "chem2", "color": "blue"},
            scales={"x": ScaleContinuous(), "color": ScaleOrdinal(palette=["red", "blue"])},
        )
        assert layer.mapping["x"] == "chem1"
        assert layer.scales["x"].name == "continuous"

    def test_requires_geom(self):
        with pytest.raises(TypeError, match="Geom instance"):
            Layer(geom="not_a_geom")

    def test_requires_stat(self):
        with pytest.raises(TypeError, match="Stat instance"):
            Layer(geom=GeomPoint(), stat="not_a_stat")

    def test_mapping_must_be_dict(self):
        with pytest.raises(TypeError, match="mapping must be a dict"):
            Layer(geom=GeomPoint(), mapping="not_a_dict")

    def test_scales_must_be_dict_or_none(self):
        with pytest.raises(TypeError, match="scales must be a dict or None"):
            Layer(geom=GeomPoint(), scales="not_a_dict")

    def test_data_override_string(self):
        layer = Layer(geom=GeomPoint(), data_override="other_dataset")
        assert layer.data_override == "other_dataset"

    def test_data_override_must_be_string(self):
        with pytest.raises(TypeError, match="data_override must be a string or None"):
            Layer(geom=GeomPoint(), data_override=123)

    def test_is_frozen(self):
        layer = Layer(geom=GeomPoint())
        with pytest.raises(AttributeError):
            layer.mapping = {"x": "col"}


class TestLayerSpec:
    def test_minimal(self):
        spec = LayerSpec(
            geom=GeomPoint(),
            stat=StatIdentity(),
            visual_mapping={"x": [1, 2], "y": [3, 4]},
        )
        assert spec.geom.name == "point"
        assert spec.visual_mapping["x"] == [1, 2]

    def test_with_override(self):
        spec = LayerSpec(
            geom=GeomPoint(),
            stat=StatIdentity(),
            visual_mapping={},
            data_override="other",
        )
        assert spec.data_override == "other"
