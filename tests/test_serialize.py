"""
Tests for the serialize module: round-trip conversion of all core types.
"""

from __future__ import annotations

import pytest
import pandas as pd

from geofig_engine.core.geom import (
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
)
from geofig_engine.core.coord import (
    CoordCartesian,
    CoordFlipped,
    CoordPolar,
    CoordFixed,
)
from geofig_engine.core.facet import FacetNull, FacetWrap, FacetGrid
from geofig_engine.core.scale import (
    ScaleContinuous,
    ScaleOrdinal,
    ScaleConstant,
    ScaleDateTime,
)
from geofig_engine.core.stat import (
    StatIdentity,
    StatFn,
    StatBin,
    StatCount,
    StatSmooth,
    StatSum,
    StatPieLabels,
    StatRadar,
)
from geofig_engine.core.spec import FigureSpec
from geofig_engine.core.layer import LayerSpec
from geofig_engine.serialize import (
    geom_to_dict,
    geom_from_dict,
    coord_to_dict,
    coord_from_dict,
    facet_to_dict,
    facet_from_dict,
    scale_to_dict,
    scale_from_dict,
    stat_to_dict,
    stat_from_dict,
    layer_spec_to_dict,
    layer_spec_from_dict,
    figure_spec_to_dict,
    figure_spec_from_dict,
    spec_to_json,
    spec_from_json,
)


# ---------------------------------------------------------------------------
# Geom round-trip
# ---------------------------------------------------------------------------

class TestGeomSerialize:
    def test_geom_point_roundtrip(self):
        g = GeomPoint()
        d = geom_to_dict(g)
        assert d == {"type": "point"}
        assert type(geom_from_dict(d)) is GeomPoint

    def test_geom_line_roundtrip(self):
        g = GeomLine()
        d = geom_to_dict(g)
        assert d == {"type": "line"}
        assert type(geom_from_dict(d)) is GeomLine

    def test_geom_function_line_roundtrip(self):
        g = GeomFunctionLine(func="sin(x)", label="sine")
        d = geom_to_dict(g)
        assert d == {"type": "function_line", "func": "sin(x)", "label": "sine"}
        restored = geom_from_dict(d)
        assert type(restored) is GeomFunctionLine
        assert restored.func == "sin(x)"
        assert restored.label == "sine"

    def test_geom_function_line_no_label(self):
        g = GeomFunctionLine(func="x**2")
        d = geom_to_dict(g)
        restored = geom_from_dict(d)
        assert type(restored) is GeomFunctionLine
        assert restored.func == "x**2"
        assert restored.label is None

    def test_geom_bar_roundtrip(self):
        assert type(geom_from_dict(geom_to_dict(GeomBar()))) is GeomBar

    def test_geom_bar_stack_roundtrip(self):
        g = GeomBar(position="stack")
        d = geom_to_dict(g)
        assert d["position"] == "stack"
        restored = geom_from_dict(d)
        assert type(restored) is GeomBar
        assert restored.position == "stack"

    def test_geom_bar_fill_roundtrip(self):
        g = GeomBar(position="fill")
        d = geom_to_dict(g)
        assert d["position"] == "fill"
        restored = geom_from_dict(d)
        assert type(restored) is GeomBar
        assert restored.position == "fill"

    def test_geom_area_roundtrip(self):
        assert type(geom_from_dict(geom_to_dict(GeomArea()))) is GeomArea

    def test_geom_ribbon_roundtrip(self):
        assert type(geom_from_dict(geom_to_dict(GeomRibbon()))) is GeomRibbon

    def test_geom_text_roundtrip(self):
        assert type(geom_from_dict(geom_to_dict(GeomText()))) is GeomText

    def test_geom_errorbar_roundtrip(self):
        assert type(geom_from_dict(geom_to_dict(GeomErrorbar()))) is GeomErrorbar

    def test_geom_box_roundtrip(self):
        geom = GeomBox(showfliers=False, showmeans=True, show_n=True, sort_mode="forward")
        restored = geom_from_dict(geom_to_dict(geom))
        assert type(restored) is GeomBox
        assert restored.showfliers is False
        assert restored.showmeans is True
        assert restored.sort_mode == "forward"

    def test_geom_violin_roundtrip(self):
        geom = GeomViolin(show_medians=False, sort_mode="reverse")
        restored = geom_from_dict(geom_to_dict(geom))
        assert type(restored) is GeomViolin
        assert restored.show_medians is False
        assert restored.sort_mode == "reverse"

    def test_geom_step_line_roundtrip(self):
        geom = GeomStepLine(where="mid")
        restored = geom_from_dict(geom_to_dict(geom))
        assert type(restored) is GeomStepLine
        assert restored.where == "mid"

    def test_geom_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown geom type"):
            geom_from_dict({"type": "bogus"})


# ---------------------------------------------------------------------------
# Coord round-trip
# ---------------------------------------------------------------------------

class TestCoordSerialize:
    def test_coord_cartesian_roundtrip(self):
        assert type(coord_from_dict(coord_to_dict(CoordCartesian()))) is CoordCartesian

    def test_coord_flipped_roundtrip(self):
        assert type(coord_from_dict(coord_to_dict(CoordFlipped()))) is CoordFlipped

    def test_coord_polar_roundtrip(self):
        g = CoordPolar(theta="y", start=45.0, end=180.0)
        d = coord_to_dict(g)
        assert d == {"type": "polar", "params": {"theta": "y", "start": 45.0, "end": 180.0}}
        restored = coord_from_dict(d)
        assert type(restored) is CoordPolar
        assert restored.params["theta"] == "y"

    def test_coord_fixed_roundtrip(self):
        g = CoordFixed(ratio=0.5)
        d = coord_to_dict(g)
        assert d["params"]["ratio"] == 0.5
        restored = coord_from_dict(d)
        assert type(restored) is CoordFixed
        assert restored.params["ratio"] == 0.5
        assert restored.aspect_ratio() == 0.5

    def test_coord_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown coord type"):
            coord_from_dict({"type": "bogus"})


# ---------------------------------------------------------------------------
# Facet round-trip
# ---------------------------------------------------------------------------

class TestFacetSerialize:
    def test_facet_null_roundtrip(self):
        assert type(facet_from_dict(facet_to_dict(FacetNull()))) is FacetNull

    def test_facet_wrap_roundtrip(self):
        g = FacetWrap(by="category", ncol=3, scales="free_x")
        d = facet_to_dict(g)
        assert d["type"] == "wrap"
        assert d["by"] == ["category"]
        assert d["scales"] == "free_x"
        restored = facet_from_dict(d)
        assert type(restored) is FacetWrap
        assert restored.by == ("category",)
        assert restored.scales == "free_x"

    def test_facet_wrap_multiple_by(self):
        g = FacetWrap(by=("a", "b"), nrow=2)
        d = facet_to_dict(g)
        assert d["by"] == ["a", "b"]
        restored = facet_from_dict(d)
        assert restored.by == ("a", "b")
        assert restored.params["nrow"] == 2

    def test_facet_grid_roundtrip(self):
        g = FacetGrid(row="row_col", col="col_col", scales="free")
        d = facet_to_dict(g)
        assert d["type"] == "grid"
        assert d["params"]["row"] == "row_col"
        assert d["params"]["col"] == "col_col"
        restored = facet_from_dict(d)
        assert type(restored) is FacetGrid
        assert restored.params["row"] == "row_col"

    def test_facet_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown facet type"):
            facet_from_dict({"type": "bogus"})


# ---------------------------------------------------------------------------
# Scale round-trip
# ---------------------------------------------------------------------------

class TestScaleSerialize:
    def test_scale_continuous_roundtrip(self):
        g = ScaleContinuous(trans="log", domain=(0.1, 100.0))
        d = scale_to_dict(g)
        assert d["type"] == "continuous"
        assert d["params"]["trans"] == "log"
        restored = scale_from_dict(d)
        assert type(restored) is ScaleContinuous
        assert restored.params["trans"] == "log"

    def test_scale_ordinal_roundtrip(self):
        g = ScaleOrdinal(palette=["red", "blue", "green"])
        d = scale_to_dict(g)
        assert d["type"] == "ordinal"
        restored = scale_from_dict(d)
        assert type(restored) is ScaleOrdinal

    def test_scale_constant_roundtrip(self):
        g = ScaleConstant(value=42)
        d = scale_to_dict(g)
        assert d["params"]["value"] == 42
        restored = scale_from_dict(d)
        assert type(restored) is ScaleConstant

    def test_scale_datetime_roundtrip(self):
        g = ScaleDateTime(fmt="%Y-%m")
        d = scale_to_dict(g)
        assert d["params"]["format"] == "%Y-%m"
        restored = scale_from_dict(d)
        assert type(restored) is ScaleDateTime

    def test_scale_with_domain_range(self):
        g = ScaleContinuous(domain=(0, 10), range=(0, 1))
        d = scale_to_dict(g)
        assert d["domain"] == [0, 10]
        assert d["range"] == [0, 1]
        restored = scale_from_dict(d)
        assert restored.domain == (0, 10)
        assert restored.range == (0, 1)

    def test_scale_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown scale type"):
            scale_from_dict({"type": "bogus"})


# ---------------------------------------------------------------------------
# Stat round-trip
# ---------------------------------------------------------------------------

class TestStatSerialize:
    def test_stat_identity_roundtrip(self):
        assert type(stat_from_dict(stat_to_dict(StatIdentity()))) is StatIdentity

    def test_stat_fn_converts_to_identity(self):
        g = StatFn(func=lambda df: df)
        d = stat_to_dict(g)
        assert d["type"] == "fn"
        restored = stat_from_dict(d)
        assert type(restored) is StatIdentity

    def test_stat_bin_roundtrip(self):
        g = StatBin(bins=20, range=(0, 100))
        d = stat_to_dict(g)
        assert d["type"] == "bin"
        assert d["params"]["bins"] == 20
        restored = stat_from_dict(d)
        assert type(restored) is StatBin
        assert restored.params["bins"] == 20

    def test_stat_count_roundtrip(self):
        assert type(stat_from_dict(stat_to_dict(StatCount()))) is StatCount

    def test_stat_smooth_roundtrip(self):
        g = StatSmooth(method="loess", span=0.5, degree=1)
        d = stat_to_dict(g)
        assert d["type"] == "smooth"
        restored = stat_from_dict(d)
        assert type(restored) is StatSmooth

    def test_stat_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown stat type"):
            stat_from_dict({"type": "bogus"})

    def test_stat_sum_roundtrip(self):
        g = StatSum(column="val", group="cat", sort=False)
        d = stat_to_dict(g)
        assert d["type"] == "sum"
        restored = stat_from_dict(d)
        assert type(restored) is StatSum
        assert restored.params["group"] == "cat"

    def test_stat_pie_labels_roundtrip(self):
        g = StatPieLabels(column="val", group="cat", show_percent=False, label_distance=1.5)
        d = stat_to_dict(g)
        assert d["type"] == "pie_labels"
        restored = stat_from_dict(d)
        assert type(restored) is StatPieLabels
        assert restored.params["label_distance"] == 1.5

    def test_stat_radar_roundtrip(self):
        g = StatRadar(shared_axes=False)
        d = stat_to_dict(g)
        assert d["type"] == "radar"
        restored = stat_from_dict(d)
        assert type(restored) is StatRadar
        assert restored.params["shared_axes"] is False


# ---------------------------------------------------------------------------
# LayerSpec round-trip
# ---------------------------------------------------------------------------

class TestLayerSpecSerialize:
    def test_layer_spec_roundtrip(self):
        layer = LayerSpec(
            geom=GeomPoint(),
            stat=StatIdentity(),
            visual_mapping={
                "x": pd.Series([1, 2, 3], name="X"),
                "y": pd.Series([4, 5, 6], name="Y"),
                "color": "red",
            },
        )
        d = layer_spec_to_dict(layer)
        restored = layer_spec_from_dict(d)
        assert type(restored.geom) is GeomPoint
        assert type(restored.stat) is StatIdentity
        assert list(restored.visual_mapping["x"]) == [1, 2, 3]
        assert restored.visual_mapping["x"].name == "X"
        assert list(restored.visual_mapping["y"]) == [4, 5, 6]
        assert restored.visual_mapping["color"] == "red"
        assert restored.data_override is None

    def test_layer_spec_with_data_override(self):
        layer = LayerSpec(
            geom=GeomLine(),
            stat=StatIdentity(),
            visual_mapping={"x": pd.Series([1, 2, 3])},
            data_override="other_key",
        )
        restored = layer_spec_from_dict(layer_spec_to_dict(layer))
        assert restored.data_override == "other_key"

    def test_layer_spec_unnamed_series(self):
        layer = LayerSpec(
            geom=GeomPoint(),
            stat=StatIdentity(),
            visual_mapping={"x": pd.Series([1, 2, 3])},
        )
        restored = layer_spec_from_dict(layer_spec_to_dict(layer))
        assert restored.visual_mapping["x"].name is None

    def test_layer_spec_xlim_roundtrip(self):
        layer = LayerSpec(
            geom=GeomPoint(), stat=StatIdentity(), visual_mapping={},
            xlim=(0, 10), ylim=(-5, 5),
        )
        restored = layer_spec_from_dict(layer_spec_to_dict(layer))
        assert restored.xlim == (0, 10)
        assert restored.ylim == (-5, 5)

    def test_layer_spec_xlim_none_omitted(self):
        layer = LayerSpec(geom=GeomPoint(), stat=StatIdentity(), visual_mapping={})
        d = layer_spec_to_dict(layer)
        assert "xlim" not in d
        assert "ylim" not in d


# ---------------------------------------------------------------------------
# FigureSpec round-trip
# ---------------------------------------------------------------------------

class TestFigureSpecSerialize:
    @pytest.fixture
    def sample_spec(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        return FigureSpec(
            data=df,
            mappings={"x": pd.Series([1, 2, 3], name="a"), "y": pd.Series([4, 5, 6], name="b")},
            settings={"title": "Test", "figsize": [6, 4]},
            context={"iter": 0},
            template_name="bivariate",
            iterator_key=("group",),
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={
                        "x": pd.Series([1, 2, 3], name="a"),
                        "y": pd.Series([4, 5, 6], name="b"),
                        "color": "blue",
                    },
                ),
            ],
            coord=CoordPolar(theta="x"),
            facet=FacetWrap(by="category", ncol=2),
        )

    def test_figure_spec_roundtrip(self, sample_spec):
        d = figure_spec_to_dict(sample_spec)
        restored = figure_spec_from_dict(d)

        assert restored.template_name == "bivariate"
        assert restored.iterator_key == ("group",)
        assert restored.settings == {"title": "Test", "figsize": [6, 4]}
        assert restored.context == {"iter": 0}
        assert type(restored.coord) is CoordPolar
        assert type(restored.facet) is FacetWrap

        assert len(restored.layers) == 1
        assert type(restored.layers[0].geom) is GeomPoint
        assert restored.layers[0].visual_mapping["color"] == "blue"

        # Data preserved
        assert list(restored.data["a"]) == [1, 2, 3]
        assert list(restored.data["b"]) == [4, 5, 6]

        # Mappings preserved with Series
        assert list(restored.mappings["x"]) == [1, 2, 3]
        assert restored.mappings["x"].name == "a"

    def test_figure_spec_empty_layers(self, sample_spec):
        df = pd.DataFrame({"a": [1]})
        spec = FigureSpec(
            data=df,
            mappings={},
            settings={},
            context={},
            template_name="test",
            layers=[],
        )
        restored = figure_spec_from_dict(figure_spec_to_dict(spec))
        assert restored.layers == []

    def test_figure_spec_index_preserved(self):
        df = pd.DataFrame({"x": [10, 20]}, index=[5, 10])
        spec = FigureSpec(
            data=df,
            mappings={"x": pd.Series([10, 20], name="x")},
            settings={},
            context={},
            template_name="test",
        )
        restored = figure_spec_from_dict(figure_spec_to_dict(spec))
        assert list(restored.data.index) == [5, 10]

    def test_spec_to_json_roundtrip(self, sample_spec):
        json_str = spec_to_json(sample_spec, indent=2)
        assert isinstance(json_str, str)
        restored = spec_from_json(json_str)
        assert restored.template_name == "bivariate"
        assert len(restored.layers) == 1


# ---------------------------------------------------------------------------
# Mappings with Series (post-engine format)
# ---------------------------------------------------------------------------

class TestMappingsWithSeries:
    def test_mappings_series_roundtrip(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        spec = FigureSpec(
            data=df,
            mappings={
                "x": pd.Series([1, 2, 3], name="a"),
                "color": "red",
            },
            settings={},
            context={},
            template_name="test",
        )
        d = figure_spec_to_dict(spec)
        restored = figure_spec_from_dict(d)
        assert isinstance(restored.mappings["x"], pd.Series)
        assert restored.mappings["x"].name == "a"
        assert restored.mappings["color"] == "red"
