import importlib.util

import pandas as pd
import pytest

from geofig_engine.core.coord import (
    Coord,
    CoordCartesian,
    CoordFlipped,
    CoordPolar,
    CoordFixed,
    CoordGeo,
    WGS84,
)


class TestCoordBase:
    def test_requires_non_empty_name(self):
        with pytest.raises(ValueError, match="non-empty string"):
            Coord(name="")

    def test_default_aspect_is_none(self):
        c = Coord(name="test")
        assert c.aspect_ratio() is None


class TestCoordCartesian:
    def test_name(self):
        assert CoordCartesian().name == "cartesian"

    def test_aspect_is_none(self):
        assert CoordCartesian().aspect_ratio() is None


class TestCoordFlipped:
    def test_name(self):
        assert CoordFlipped().name == "flipped"


class TestCoordPolar:
    def test_defaults(self):
        c = CoordPolar()
        assert c.name == "polar"
        assert c.params["theta"] == "x"
        assert c.params["start"] == 0.0
        assert c.params["end"] == 360.0

    def test_aspect_is_one(self):
        assert CoordPolar().aspect_ratio() == 1.0


class TestCoordFixed:
    def test_default_ratio_is_one(self):
        c = CoordFixed()
        assert c.params["ratio"] == 1.0

    def test_custom_ratio(self):
        c = CoordFixed(ratio=1.618)
        assert c.params["ratio"] == 1.618

    def test_aspect_returns_ratio(self):
        c = CoordFixed(ratio=2.0)
        assert c.aspect_ratio() == 2.0

    def test_negative_ratio_raises(self):
        with pytest.raises(ValueError, match="positive"):
            CoordFixed(ratio=-1.0)


GEO_INSTALLED = importlib.util.find_spec("pyproj") is not None


class TestCoordGeo:
    def test_defaults(self):
        c = CoordGeo()
        assert c.name == "geo"
        assert c.crs == WGS84
        assert c.bounds is None
        assert c.bounds_crs is None
        assert c.aspect is None
        assert c.aspect_ratio() is None
        assert c.params == {"crs": WGS84}

    def test_custom_params(self):
        c = CoordGeo(
            crs="EPSG:3857",
            bounds=(-123.0, 45.0, -122.0, 46.0),
            aspect=1.4,
        )
        assert c.crs == "EPSG:3857"
        assert c.bounds == (-123.0, 45.0, -122.0, 46.0)
        assert c.bounds_crs == "EPSG:3857"
        assert c.aspect == 1.4
        assert c.aspect_ratio() == 1.4
        assert c.params["bounds"] == [-123.0, 45.0, -122.0, 46.0]

    def test_bounds_can_be_in_another_crs(self):
        c = CoordGeo(crs="EPSG:3857", bounds=(0, 0, 1, 1), bounds_crs="EPSG:4326")
        assert c.bounds_crs == "EPSG:4326"

    def test_rejects_empty_crs(self):
        with pytest.raises(ValueError, match="crs"):
            CoordGeo(crs="")

    def test_rejects_malformed_bounds(self):
        with pytest.raises(ValueError, match="4-tuple"):
            CoordGeo(bounds=(1, 2, 3))  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="real numbers"):
            CoordGeo(bounds=(1, "a", 3, 4))  # type: ignore[list-item]
        with pytest.raises(ValueError, match="min_lon"):
            CoordGeo(bounds=(1, 2, 1, 4))

    def test_rejects_non_positive_aspect(self):
        with pytest.raises(ValueError, match="aspect"):
            CoordGeo(aspect=0.0)

    def test_identity_transform_default_wgs84(self):
        c = CoordGeo()
        vm = {"x": pd.Series([-122.4, -121.9]), "y": pd.Series([37.8, 37.3])}
        out = c.transform_visual_mapping(vm, None)
        assert out["x"].tolist() == [-122.4, -121.9]
        assert out["y"].tolist() == [37.8, 37.3]

    def test_identity_passthrough_when_channels_missing(self):
        c = CoordGeo(crs="EPSG:3857")
        x = pd.Series([1.0, 2.0])
        out = c.transform_visual_mapping({"x": x}, None)
        assert out["x"].tolist() == [1.0, 2.0]

    @pytest.mark.skipif(not GEO_INSTALLED, reason="[geo] extra not installed")
    def test_projects_to_target_crs_with_pyproj(self):
        c = CoordGeo(crs="EPSG:3857")
        out = c.transform_visual_mapping(
            {"x": pd.Series([0.0]), "y": pd.Series([0.0])}, None
        )
        assert out["x"].tolist() == pytest.approx([0.0], abs=1e-6)
        out2 = c.transform_visual_mapping(
            {"x": pd.Series([10.0]), "y": pd.Series([0.0])}, None
        )
        assert out2["x"].tolist() == pytest.approx([1113194.9079], abs=0.5)

    @pytest.mark.skipif(GEO_INSTALLED, reason="covers the pyproj-less fallback only")
    def test_identity_fallback_without_pyproj(self):
        c = CoordGeo(crs="EPSG:3857")
        vm = {"x": pd.Series([10.0]), "y": pd.Series([0.0])}
        with pytest.warns(UserWarning, match="pyproj"):
            out = c.transform_visual_mapping(vm, None)
        assert out["x"].tolist() == [10.0]
        assert out["y"].tolist() == [0.0]

    def test_serialization_roundtrip(self):
        from geofig_engine.serialize.converters import coord_from_dict, coord_to_dict

        c = CoordGeo(crs="EPSG:3857", bounds=(-10.0, -10.0, 10.0, 10.0), aspect=1.2)
        restored = coord_from_dict(coord_to_dict(c))
        assert restored == c
        assert coord_from_dict(coord_to_dict(CoordGeo())) == CoordGeo()
