import pytest

from geofig_engine.core.coord import (
    Coord,
    CoordCartesian,
    CoordFlipped,
    CoordPolar,
    CoordFixed,
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
