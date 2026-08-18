import pandas as pd

from geofig_engine.core.coord import PiperCoord
from geofig_engine.core.geom import GeomPoint
from geofig_engine.templates import build_piper_specs, piper_overlay_diamond
from geofig_engine.serialize import coord_to_dict, coord_from_dict


class TestPiperCoord:
    def test_defaults(self):
        c = PiperCoord()
        assert c.name == "piper"
        assert c.params["left_tri"] == ["Ca", "Mg", "Na+K"]
        assert c.params["right_tri"] == ["HCO3", "SO4", "Cl"]

    def test_custom_columns(self):
        c = PiperCoord(
            left_tri=("Na", "K", "Ca"),
            right_tri=("Cl", "SO4", "HCO3"),
        )
        assert c.params["left_tri"] == ["Na", "K", "Ca"]
        assert c.params["right_tri"] == ["Cl", "SO4", "HCO3"]

    def test_serialization_roundtrip(self):
        c = PiperCoord(
            left_tri=("Ca", "Mg", "Na+K"),
            right_tri=("HCO3", "SO4", "Cl"),
        )
        d = coord_to_dict(c)
        restored = coord_from_dict(d)
        assert isinstance(restored, PiperCoord)
        assert restored.params["left_tri"] == ["Ca", "Mg", "Na+K"]
        assert restored.params["right_tri"] == ["HCO3", "SO4", "Cl"]


class TestBuildPiperSpecs:
    def test_returns_list_of_specs(self):
        data = pd.DataFrame({
            "Ca": [1.0, 2.0], "Mg": [0.5, 1.0], "Na+K": [0.3, 0.5],
            "HCO3": [2.0, 3.0], "SO4": [0.2, 0.4], "Cl": [0.1, 0.2],
        })
        specs = build_piper_specs(data)
        assert len(specs) == 1

    def test_piper_coord_in_spec(self):
        data = pd.DataFrame({
            "Ca": [1.0], "Mg": [0.5], "Na+K": [0.3],
            "HCO3": [2.0], "SO4": [0.2], "Cl": [0.1],
        })
        specs = build_piper_specs(data)
        assert isinstance(specs[0].coord, PiperCoord)

    def test_layers_have_subplot_tags(self):
        data = pd.DataFrame({
            "Ca": [1.0], "Mg": [0.5], "Na+K": [0.3],
            "HCO3": [2.0], "SO4": [0.2], "Cl": [0.1],
        })
        specs = build_piper_specs(data)
        subplots = {l.subplot for l in specs[0].layers}
        assert subplots == {"left_tri", "right_tri", "diamond"}

    def test_layers_are_geom_point(self):
        data = pd.DataFrame({
            "Ca": [1.0], "Mg": [0.5], "Na+K": [0.3],
            "HCO3": [2.0], "SO4": [0.2], "Cl": [0.1],
        })
        specs = build_piper_specs(data)
        for layer in specs[0].layers:
            assert isinstance(layer.geom, GeomPoint)
            assert "x" in layer.visual_mapping
            assert "y" in layer.visual_mapping

    def test_custom_title(self):
        data = pd.DataFrame({
            "Ca": [1.0], "Mg": [0.5], "Na+K": [0.3],
            "HCO3": [2.0], "SO4": [0.2], "Cl": [0.1],
        })
        specs = build_piper_specs(data, title="My Piper")
        assert specs[0].settings["title"] == "My Piper"

    def test_mapping_adds_color_channel(self):
        data = pd.DataFrame({
            "Ca": [1.0], "Mg": [0.5], "Na+K": [0.3],
            "HCO3": [2.0], "SO4": [0.2], "Cl": [0.1],
            "group": ["A"],
        })
        specs = build_piper_specs(data, mapping={"color": "group"})
        for layer in specs[0].layers:
            assert "color" in layer.visual_mapping

    def test_mapping_adds_marker_channel(self):
        data = pd.DataFrame({
            "Ca": [1.0], "Mg": [0.5], "Na+K": [0.3],
            "HCO3": [2.0], "SO4": [0.2], "Cl": [0.1],
            "group": ["A"],
        })
        specs = build_piper_specs(data, mapping={"color": "group", "marker": "group"})
        for layer in specs[0].layers:
            assert "color" in layer.visual_mapping
            assert "marker" in layer.visual_mapping


class TestPiperOverlay:
    def test_appends_layer(self):
        data = pd.DataFrame({
            "Ca": [1.0], "Mg": [0.5], "Na+K": [0.3],
            "HCO3": [2.0], "SO4": [0.2], "Cl": [0.1],
        })
        specs = build_piper_specs(data)
        n_before = len(specs[0].layers)
        overlaid = piper_overlay_diamond(specs[0], data)
        assert len(overlaid.layers) == n_before + 1
        assert overlaid.layers[-1].subplot == "diamond"

    def test_overlay_setting(self):
        data = pd.DataFrame({
            "Ca": [1.0], "Mg": [0.5], "Na+K": [0.3],
            "HCO3": [2.0], "SO4": [0.2], "Cl": [0.1],
        })
        specs = build_piper_specs(data)
        overlaid = piper_overlay_diamond(specs[0], data)
        assert overlaid.settings.get("piper_overlay") is True


class TestPiperRenderer:
    def test_render_piper(self):
        from geofig_engine.renderers import MatplotlibRenderer
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({
            "Ca": [1.0, 2.0], "Mg": [0.5, 1.0], "Na+K": [0.3, 0.5],
            "HCO3": [2.0, 3.0], "SO4": [0.2, 0.4], "Cl": [0.1, 0.2],
        })
        specs = build_piper_specs(data)
        assert renderer.supports(specs[0]) is True
        fig = renderer.render(specs[0])
        assert fig is not None
        assert len(fig.axes) >= 3

    def test_render_with_mapping(self):
        from geofig_engine.renderers import MatplotlibRenderer
        renderer = MatplotlibRenderer()
        data = pd.DataFrame({
            "Ca": [1.0, 2.0], "Mg": [0.5, 1.0], "Na+K": [0.3, 0.5],
            "HCO3": [2.0, 3.0], "SO4": [0.2, 0.4], "Cl": [0.1, 0.2],
            "group": ["A", "B"],
        })
        specs = build_piper_specs(data, mapping={"color": "group"})
        fig = renderer.render(specs[0])
        assert fig is not None


class TestPiperGeomCompatibility:
    """Validate standard GoG geometries in Piper subplot coordinate spaces.

    After build_piper_specs pre-computes ternary/diamond positions into
    standard (x, y) cartesian coordinates, all geometries work naturally:
    - Left triangle:   x in [0,1],  y in [0,sqrt(3)/2]
    - Right triangle:  same bounds
    - Diamond:          x in [-1,1], y in [-1,1]  -- |x|+|y|<=1 defines the diamond

    GeomRect: axis-aligned rects work in all subplots (will be clipped by frame).
    GeomAbline: infinite lines via ax.axline -- clipped by axes limits.
    GeomPoint: standard scatter -- used as primary data layer.
    GeomText: standard text annotations -- fully compatible.
    """

    def _make_data(self):
        return pd.DataFrame({
            "Ca": [1.0, 2.0], "Mg": [0.5, 1.0], "Na+K": [0.3, 0.5],
            "HCO3": [2.0, 3.0], "SO4": [0.2, 0.4], "Cl": [0.1, 0.2],
        })

    def test_abline_in_diamond(self):
        """GeomAbline draws a reference line across the diamond."""
        from geofig_engine.renderers import MatplotlibRenderer
        from geofig_engine.core.layer import LayerSpec
        from geofig_engine.core.geom import GeomAbline
        from geofig_engine.core.stat import StatIdentity
        renderer = MatplotlibRenderer()
        data = self._make_data()
        specs = build_piper_specs(data)
        spec = specs[0]
        abline_layer = LayerSpec(
            geom=GeomAbline(slope=0, intercept=0),
            stat=StatIdentity(),
            visual_mapping={"color": "red", "style": "dashed", "width": 0.5},
            subplot="diamond",
            zorder=1,
        )
        spec = spec.__class__(
            data=spec.data, mappings=spec.mappings, settings=spec.settings,
            context=spec.context, template_name=spec.template_name,
            layers=list(spec.layers) + [abline_layer],
            coord=spec.coord, facet=spec.facet,
        )
        fig = renderer.render(spec)
        assert fig is not None

    def test_rect_in_left_triangle(self):
        """GeomRect draws a small highlight rectangle in the left triangle."""
        from geofig_engine.renderers import MatplotlibRenderer
        from geofig_engine.core.layer import LayerSpec
        from geofig_engine.core.geom import GeomRect
        from geofig_engine.core.stat import StatIdentity
        renderer = MatplotlibRenderer()
        data = self._make_data()
        specs = build_piper_specs(data)
        spec = specs[0]
        rect_layer = LayerSpec(
            geom=GeomRect(),
            stat=StatIdentity(),
            visual_mapping={
                "xmin": 0.2, "xmax": 0.4,
                "ymin": 0.2, "ymax": 0.4,
                "color": "yellow", "alpha": 0.3,
            },
            subplot="left_tri",
            zorder=0,
        )
        spec = spec.__class__(
            data=spec.data, mappings=spec.mappings, settings=spec.settings,
            context=spec.context, template_name=spec.template_name,
            layers=list(spec.layers) + [rect_layer],
            coord=spec.coord, facet=spec.facet,
        )
        fig = renderer.render(spec)
        assert fig is not None

    def test_text_in_diamond(self):
        """GeomText places a label inside the diamond panel."""
        from geofig_engine.renderers import MatplotlibRenderer
        from geofig_engine.core.layer import LayerSpec
        from geofig_engine.core.geom import GeomText
        from geofig_engine.core.stat import StatIdentity
        renderer = MatplotlibRenderer()
        data = self._make_data()
        specs = build_piper_specs(data)
        spec = specs[0]
        text_layer = LayerSpec(
            geom=GeomText(),
            stat=StatIdentity(),
            visual_mapping={
                "x": 0.0, "y": 0.0,
                "label": "center", "color": "red", "size": 10,
            },
            subplot="diamond",
            zorder=5,
        )
        spec = spec.__class__(
            data=spec.data, mappings=spec.mappings, settings=spec.settings,
            context=spec.context, template_name=spec.template_name,
            layers=list(spec.layers) + [text_layer],
            coord=spec.coord, facet=spec.facet,
        )
        fig = renderer.render(spec)
        assert fig is not None

    def test_vspan_in_right_triangle(self):
        """GeomVSpan draws a vertical band in the right triangle."""
        from geofig_engine.renderers import MatplotlibRenderer
        from geofig_engine.core.layer import LayerSpec
        from geofig_engine.core.geom import GeomVSpan
        from geofig_engine.core.stat import StatIdentity
        renderer = MatplotlibRenderer()
        data = self._make_data()
        specs = build_piper_specs(data)
        spec = specs[0]
        vspan_layer = LayerSpec(
            geom=GeomVSpan(),
            stat=StatIdentity(),
            visual_mapping={
                "xmin": 0.3, "xmax": 0.5,
                "color": "lightblue", "alpha": 0.3,
            },
            subplot="right_tri",
            zorder=0,
        )
        spec = spec.__class__(
            data=spec.data, mappings=spec.mappings, settings=spec.settings,
            context=spec.context, template_name=spec.template_name,
            layers=list(spec.layers) + [vspan_layer],
            coord=spec.coord, facet=spec.facet,
        )
        fig = renderer.render(spec)
        assert fig is not None
