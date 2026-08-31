import pandas as pd

from geofig_engine.core.geom import GeomAbline, GeomHSpan, GeomPoint, GeomText, GeomVSpan
from geofig_engine.templates import npr_nnp, anp_agp, nagph_nag
from geofig_engine.templates.base import FigureTemplate


class TestNprNnp:
    def test_returns_template(self):
        t = npr_nnp()
        assert isinstance(t, FigureTemplate)
        assert t.name == "npr_nnp"

    def test_has_point_layer(self):
        t = npr_nnp()
        assert any(isinstance(l.geom, GeomPoint) for l in t.layers)

    def test_has_abline_layers(self):
        t = npr_nnp()
        ablines = [l for l in t.layers if isinstance(l.geom, GeomAbline)]
        assert len(ablines) == 2

    def test_has_gray_bands(self):
        t = npr_nnp()
        vspans = [l for l in t.layers if isinstance(l.geom, GeomVSpan)]
        hspans = [l for l in t.layers if isinstance(l.geom, GeomHSpan)]
        assert len(vspans) == 1
        assert len(hspans) == 1

    def test_has_text_layers(self):
        t = npr_nnp()
        texts = [l for l in t.layers if isinstance(l.geom, GeomText)]
        assert len(texts) == 3

    def test_default_settings(self):
        t = npr_nnp()
        assert t.default_settings["figsize"] == (8, 8)
        assert "title" in t.default_settings

    def test_mapping_preserved(self):
        mapping = {"x": "npr", "y": "nnp", "color": "group"}
        t = npr_nnp(mapping=mapping)
        point_layer = [l for l in t.layers if isinstance(l.geom, GeomPoint)][0]
        assert point_layer.mapping["x"] == "npr"


class TestAnpAgp:
    def test_returns_template(self):
        t = anp_agp()
        assert isinstance(t, FigureTemplate)
        assert t.name == "anp_agp"

    def test_has_point_layer(self):
        t = anp_agp()
        assert any(isinstance(l.geom, GeomPoint) for l in t.layers)

    def test_has_four_abline_layers(self):
        t = anp_agp()
        ablines = [l for l in t.layers if isinstance(l.geom, GeomAbline)]
        assert len(ablines) == 4

    def test_has_text_labels(self):
        t = anp_agp()
        texts = [l for l in t.layers if isinstance(l.geom, GeomText)]
        assert len(texts) >= 7

    def test_ablines_have_different_slopes(self):
        t = anp_agp()
        ablines = [l for l in t.layers if isinstance(l.geom, GeomAbline)]
        slopes = {l.geom.slope for l in ablines}
        assert slopes == {1, 2, 3, 4}

    def test_default_settings(self):
        t = anp_agp()
        assert "figsize" in t.default_settings
        assert "xlabel" in t.default_settings["axis"]

    def test_mapping_preserved(self):
        mapping = {"x": "agp", "y": "anp", "color": "type"}
        t = anp_agp(mapping=mapping)
        point_layer = [l for l in t.layers if isinstance(l.geom, GeomPoint)][0]
        assert point_layer.mapping["x"] == "agp"


class TestNagphNag:
    def test_returns_template(self):
        t = nagph_nag()
        assert isinstance(t, FigureTemplate)
        assert t.name == "nagph_nag"

    def test_has_point_layer(self):
        t = nagph_nag()
        assert any(isinstance(l.geom, GeomPoint) for l in t.layers)

    def test_has_threshold_lines(self):
        t = nagph_nag()
        ablines = [l for l in t.layers if isinstance(l.geom, GeomAbline)]
        assert len(ablines) == 2

    def test_has_text_labels(self):
        t = nagph_nag()
        texts = [l for l in t.layers if isinstance(l.geom, GeomText)]
        assert len(texts) >= 6

    def test_default_settings(self):
        t = nagph_nag()
        assert "figsize" in t.default_settings
        assert "xlabel" in t.default_settings["axis"]

    def test_mapping_preserved(self):
        mapping = {"x": "nag_ph", "y": "nag", "color": "type"}
        t = nagph_nag(mapping=mapping)
        point_layer = [l for l in t.layers if isinstance(l.geom, GeomPoint)][0]
        assert point_layer.mapping["y"] == "nag"
