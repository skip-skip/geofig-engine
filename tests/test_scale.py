import pandas as pd
import pytest

from geofig_engine.core.scale import (
    Scale,
    ScaleContinuous,
    ScaleOrdinal,
    ScaleConstant,
    ScaleDateTime,
)


class TestScaleBase:
    def test_requires_non_empty_name(self):
        with pytest.raises(ValueError, match="non-empty string"):
            Scale(name="")

    def test_transform_not_implemented(self):
        scale = Scale(name="abstract")
        with pytest.raises(NotImplementedError):
            scale.transform(pd.Series([1, 2]))


class TestScaleContinuous:
    def test_default_trans_is_identity(self):
        s = ScaleContinuous()
        assert s.params["trans"] == "identity"

    def test_invalid_trans_raises(self):
        with pytest.raises(ValueError, match="Invalid trans"):
            ScaleContinuous(trans="cubic")

    def test_valid_trans_are_accepted(self):
        for trans in ("identity", "log", "sqrt", "reverse"):
            s = ScaleContinuous(trans=trans)
            assert s.params["trans"] == trans

    def test_identity_transform(self):
        s = ScaleContinuous(trans="identity")
        values = pd.Series([1.0, 2.0, 3.0])
        result = s.transform(values)
        assert list(result) == [1.0, 2.0, 3.0]

    def test_reverse_transform(self):
        s = ScaleContinuous(trans="reverse")
        values = pd.Series([1.0, 2.0, 3.0])
        result = s.transform(values)
        assert list(result) == [-1.0, -2.0, -3.0]

    def test_identity_invert(self):
        s = ScaleContinuous(trans="identity")
        values = pd.Series([1.0, 2.0])
        result = s.invert(values)
        assert list(result) == [1.0, 2.0]


class TestScaleOrdinal:
    def test_default_palette_empty(self):
        s = ScaleOrdinal()
        assert s.params["palette"] == ()

    def test_with_palette(self):
        s = ScaleOrdinal(palette=["red", "blue", "green"])
        assert s.params["palette"] == ("red", "blue", "green")

    def test_transform_with_palette(self):
        s = ScaleOrdinal(palette=["red", "blue"])
        values = pd.Series(["A", "B", "A", "C"])
        result = s.transform(values)
        assert list(result) == ["red", "blue", "red", "red"]

    def test_transform_without_palette(self):
        s = ScaleOrdinal()
        values = pd.Series(["A", "B"])
        result = s.transform(values)
        assert list(result) == ["A", "B"]


class TestScaleConstant:
    def test_default_value_is_none(self):
        s = ScaleConstant()
        assert s.params["value"] is None

    def test_with_value(self):
        s = ScaleConstant(value="blue")
        assert s.params["value"] == "blue"

    def test_transform_returns_constant(self):
        s = ScaleConstant(value="red")
        values = pd.Series([1, 2, 3])
        result = s.transform(values)
        assert list(result) == ["red", "red", "red"]


class TestScaleDateTime:
    def test_default_format(self):
        s = ScaleDateTime()
        assert s.params["format"] == "%Y-%m-%d"

    def test_custom_format(self):
        s = ScaleDateTime(fmt="%d/%m/%Y")
        assert s.params["format"] == "%d/%m/%Y"

    def test_transform_returns_input(self):
        s = ScaleDateTime()
        values = pd.Series([1, 2])
        result = s.transform(values)
        assert list(result) == [1, 2]
