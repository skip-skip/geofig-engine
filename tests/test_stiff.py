from geofig_engine.core.coord import StiffCoord
from geofig_engine.core.geom import GeomArea
from geofig_engine.renderers.matplotlib.renderer import _nice_tick_max
from geofig_engine.templates import plot_stiff
from geofig_engine.serialize import coord_to_dict, coord_from_dict


class TestNiceTickMax:
    def test_typical_meq(self):
        assert _nice_tick_max(15) == 20

    def test_large_saline(self):
        assert _nice_tick_max(580) == 1000

    def test_small_fresh(self):
        assert _nice_tick_max(3) == 5

    def test_minimum_value(self):
        assert _nice_tick_max(1) == 1


class TestStiffCoord:
    def test_defaults(self):
        c = StiffCoord(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3)
        assert c.name == "stiff"
        assert c.params["ca"] == 10
        assert c.params["mg"] == 5
        assert c.params["max_val"] == 15

    def test_sample_title(self):
        c = StiffCoord(ca=1, mg=1, na_k=1, cl=1, hco3=1, so4=1, sample_title="Sample A")
        assert c.params["sample_title"] == "Sample A"

    def test_serialization_roundtrip(self):
        c = StiffCoord(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3, sample_title="Well 1")
        d = coord_to_dict(c)
        restored = coord_from_dict(d)
        assert isinstance(restored, StiffCoord)
        assert restored.params["ca"] == 10
        assert restored.params["sample_title"] == "Well 1"


class TestPlotStiff:
    def test_returns_figure_spec(self):
        spec = plot_stiff(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3, title="Well 1")
        assert spec.template_name == "stiff"

    def test_stiff_coord(self):
        spec = plot_stiff(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3)
        assert isinstance(spec.coord, StiffCoord)

    def test_custom_figsize(self):
        spec = plot_stiff(ca=1, mg=1, na_k=1, cl=1, hco3=1, so4=1, figsize=(8, 8))
        assert spec.settings["figsize"] == (8, 8)

    def test_title(self):
        spec = plot_stiff(ca=1, mg=1, na_k=1, cl=1, hco3=1, so4=1, title="Test")
        assert spec.settings.get("title") is None

    def test_polygon_layer(self):
        spec = plot_stiff(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3)
        assert len(spec.layers) == 1
        layer = spec.layers[0]
        assert isinstance(layer.geom, GeomArea)
        assert "x" in layer.visual_mapping
        assert "y" in layer.visual_mapping
        assert layer.visual_mapping["color"] == "lightblue"

    def test_polygon_vertices(self):
        spec = plot_stiff(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3)
        x = spec.data["x"]
        y = spec.data["y"]
        assert len(x) == len(y) == 7
        # Correct Stiff polygon trace (no origin): top-left → mid-left → bottom-left → bottom-right → mid-right → top-right → close
        assert y.iloc[0] == 2.0                           # Na+K at top-left
        assert y.iloc[1] == 1.0                           # Ca at mid-left
        assert y.iloc[2] == 0.0                           # Mg at bottom-left
        assert y.iloc[3] == 0.0                           # SO4 at bottom-right
        assert y.iloc[4] == 1.0                           # HCO3 at mid-right
        assert y.iloc[5] == 2.0                           # Cl at top-right
        assert y.iloc[6] == 2.0                           # close back to Na+K

    def test_polygon_trace_left_to_right(self):
        spec = plot_stiff(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3)
        x = spec.data["x"]
        # Left side: all negative x (cations)
        assert x.iloc[0] < 0 and x.iloc[1] < 0 and x.iloc[2] < 0
        # Right side: all positive x (anions)
        assert x.iloc[3] > 0 and x.iloc[4] > 0 and x.iloc[5] > 0

    def test_render_stiff(self):
        from geofig_engine.renderers import MatplotlibRenderer
        renderer = MatplotlibRenderer()
        spec = plot_stiff(ca=10, mg=5, na_k=8, cl=12, hco3=15, so4=3)
        assert renderer.supports(spec) is True
        fig = renderer.render(spec)
        assert fig is not None
        assert len(fig.axes) == 1
