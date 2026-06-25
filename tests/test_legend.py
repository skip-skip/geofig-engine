"""
Tests for legend data model, extraction, and figure rendering.
"""

import pandas as pd
import pytest

from geofig_engine.core.geom import GeomPoint, GeomLine
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.spec import FigureSpec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.renderers.matplotlib.legend import (
    LegendAccumulator,
    LegendEntry,
    LegendGroup,
    render_legend_figure,
    VISUAL_CHANNELS,
)


class TestLegendEntry:
    def test_defaults(self):
        entry = LegendEntry(label="A")
        assert entry.label == "A"
        assert entry.marker == "o"
        assert entry.color == "#888888"
        assert entry.linestyle == "-"
        assert entry.alpha == 1.0

    def test_custom_values(self):
        entry = LegendEntry(label="B", marker="s", color="red", linestyle="--", alpha=0.5)
        assert entry.label == "B"
        assert entry.marker == "s"
        assert entry.color == "red"
        assert entry.linestyle == "--"
        assert entry.alpha == 0.5


class TestLegendGroup:
    def test_construction(self):
        entries = [LegendEntry("A"), LegendEntry("B")]
        group = LegendGroup(column="type", entries=entries)
        assert group.column == "type"
        assert len(group.entries) == 2


class TestLegendAccumulator:
    def test_add_from_spec_with_color_group(self):
        data = pd.DataFrame({
            "x": [1, 2, 3],
            "y": [4, 5, 6],
            "location": ["site1", "site2", "site1"],
        })
        accumulator = LegendAccumulator()
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={
                        "x": data["x"],
                        "y": data["y"],
                        "color": pd.Series(["red", "blue", "red"], name="location"),
                    },
                ),
            ],
        )
        accumulator.add_from_spec(spec)
        groups = accumulator.groups
        assert len(groups) == 1
        assert groups[0].column == "location"
        assert len(groups[0].entries) == 2
        labels = {e.label for e in groups[0].entries}
        assert labels == {"site1", "site2"}

    def test_add_from_spec_no_visual_channels(self):
        data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        accumulator = LegendAccumulator()
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={"x": data["x"], "y": data["y"]},
                ),
            ],
        )
        accumulator.add_from_spec(spec)
        assert len(accumulator.groups) == 0

    def test_add_from_spec_color_and_marker_different_columns(self):
        data = pd.DataFrame({
            "x": [1, 2],
            "y": [3, 4],
            "location": ["site1", "site2"],
            "type": ["well", "spring"],
        })
        accumulator = LegendAccumulator()
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={
                        "x": data["x"],
                        "y": data["y"],
                        "color": pd.Series(["red", "blue"], name="location"),
                        "marker": pd.Series(["o", "s"], name="type"),
                    },
                ),
            ],
        )
        accumulator.add_from_spec(spec)
        groups = accumulator.groups
        assert len(groups) == 2
        col_names = {g.column for g in groups}
        assert col_names == {"location", "type"}

        # location group should have color info
        loc_group = next(g for g in groups if g.column == "location")
        assert loc_group.entries[0].color == "red"
        assert loc_group.entries[1].color == "blue"
        # location group should have default marker
        assert loc_group.entries[0].marker == "o"

        # type group should have marker info
        type_group = next(g for g in groups if g.column == "type")
        assert type_group.entries[0].marker == "o"
        assert type_group.entries[1].marker == "s"
        # type group should have default color
        assert type_group.entries[0].color == "#888888"

    def test_add_from_spec_consolidated_column(self):
        data = pd.DataFrame({
            "x": [1, 2],
            "y": [3, 4],
            "group": ["A", "B"],
        })
        accumulator = LegendAccumulator()
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={
                        "x": data["x"],
                        "y": data["y"],
                        "color": pd.Series(["red", "blue"], name="group"),
                        "marker": pd.Series(["o", "s"], name="group"),
                    },
                ),
            ],
        )
        accumulator.add_from_spec(spec)
        groups = accumulator.groups
        assert len(groups) == 1
        assert groups[0].column == "group"
        assert len(groups[0].entries) == 2

        entry_a = next(e for e in groups[0].entries if e.label == "A")
        assert entry_a.color == "red"
        assert entry_a.marker == "o"

        entry_b = next(e for e in groups[0].entries if e.label == "B")
        assert entry_b.color == "blue"
        assert entry_b.marker == "s"

    def test_accumulation_across_multiple_specs(self):
        accumulator = LegendAccumulator()
        data1 = pd.DataFrame({"x": [1], "y": [2], "location": ["site1"]})
        spec1 = FigureSpec(
            data=data1, mappings={}, settings={}, context={}, template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(), stat=StatIdentity(),
                    visual_mapping={
                        "x": data1["x"], "y": data1["y"],
                        "color": pd.Series(["red"], name="location"),
                    },
                ),
            ],
        )
        accumulator.add_from_spec(spec1)
        assert len(accumulator.groups) == 1
        assert len(accumulator.groups[0].entries) == 1

        data2 = pd.DataFrame({"x": [1], "y": [2], "location": ["site2"]})
        spec2 = FigureSpec(
            data=data2, mappings={}, settings={}, context={}, template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(), stat=StatIdentity(),
                    visual_mapping={
                        "x": data2["x"], "y": data2["y"],
                        "color": pd.Series(["blue"], name="location"),
                    },
                ),
            ],
        )
        accumulator.add_from_spec(spec2)
        assert len(accumulator.groups) == 1
        assert len(accumulator.groups[0].entries) == 2

    def test_accumulation_does_not_duplicate(self):
        accumulator = LegendAccumulator()
        data = pd.DataFrame({"x": [1, 2], "y": [3, 4], "location": ["site1", "site2"]})
        spec = FigureSpec(
            data=data, mappings={}, settings={}, context={}, template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(), stat=StatIdentity(),
                    visual_mapping={
                        "x": data["x"], "y": data["y"],
                        "color": pd.Series(["red", "blue"], name="location"),
                    },
                ),
            ],
        )
        accumulator.add_from_spec(spec)
        accumulator.add_from_spec(spec)
        assert len(accumulator.groups) == 1
        assert len(accumulator.groups[0].entries) == 2

    def test_clear(self):
        data = pd.DataFrame({"x": [1], "y": [2], "location": ["site1"]})
        spec = FigureSpec(
            data=data, mappings={}, settings={}, context={}, template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(), stat=StatIdentity(),
                    visual_mapping={
                        "x": data["x"], "y": data["y"],
                        "color": pd.Series(["red"], name="location"),
                    },
                ),
            ],
        )
        accumulator = LegendAccumulator()
        accumulator.add_from_spec(spec)
        assert len(accumulator.groups) == 1
        accumulator.clear()
        assert len(accumulator.groups) == 0

    def test_colors_are_distinct_for_different_values(self):
        data = pd.DataFrame({
            "x": [1, 2, 3],
            "y": [4, 5, 6],
            "loc": ["A", "B", "C"],
        })
        accumulator = LegendAccumulator()
        spec = FigureSpec(
            data=data,
            mappings={},
            settings={},
            context={},
            template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(),
                    stat=StatIdentity(),
                    visual_mapping={
                        "x": data["x"], "y": data["y"],
                        "color": data["loc"],
                    },
                ),
            ],
        )
        accumulator.add_from_spec(spec)
        group = accumulator.groups[0]
        colors = {e.color for e in group.entries}
        assert len(colors) == 3, f"Expected 3 distinct colors, got {len(colors)}: {colors}"

    def test_skip_constants_without_name(self):
        data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        accumulator = LegendAccumulator()
        spec = FigureSpec(
            data=data, mappings={}, settings={}, context={}, template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(), stat=StatIdentity(),
                    visual_mapping={
                        "x": data["x"], "y": data["y"],
                        "color": "red",
                    },
                ),
            ],
        )
        accumulator.add_from_spec(spec)
        # Constant "red" has no name attribute, so no group is created
        assert len(accumulator.groups) == 0


class TestRenderLegendFigure:
    def test_empty_legend_returns_figure(self):
        accumulator = LegendAccumulator()
        fig = render_legend_figure(accumulator)
        assert fig is not None

    def test_single_group_has_one_column(self):
        data = pd.DataFrame({"x": [1, 2], "y": [3, 4], "loc": ["A", "B"]})
        accumulator = LegendAccumulator()
        spec = FigureSpec(
            data=data, mappings={}, settings={}, context={}, template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(), stat=StatIdentity(),
                    visual_mapping={
                        "x": data["x"], "y": data["y"],
                        "color": pd.Series(["red", "blue"], name="loc"),
                    },
                ),
            ],
        )
        accumulator.add_from_spec(spec)
        fig = render_legend_figure(accumulator)
        assert len(fig.axes) == 1

    def test_two_groups_have_two_columns(self):
        data = pd.DataFrame({
            "x": [1, 2], "y": [3, 4],
            "loc": ["A", "B"], "typ": ["X", "Y"],
        })
        accumulator = LegendAccumulator()
        spec = FigureSpec(
            data=data, mappings={}, settings={}, context={}, template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(), stat=StatIdentity(),
                    visual_mapping={
                        "x": data["x"], "y": data["y"],
                        "color": pd.Series(["red", "blue"], name="loc"),
                        "marker": pd.Series(["o", "s"], name="typ"),
                    },
                ),
            ],
        )
        accumulator.add_from_spec(spec)
        fig = render_legend_figure(accumulator)
        assert len(fig.axes) == 2

    def test_header_is_column_name(self):
        data = pd.DataFrame({"x": [1], "y": [2], "loc": ["A"]})
        accumulator = LegendAccumulator()
        spec = FigureSpec(
            data=data, mappings={}, settings={}, context={}, template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(), stat=StatIdentity(),
                    visual_mapping={
                        "x": data["x"], "y": data["y"],
                        "color": pd.Series(["red"], name="loc"),
                    },
                ),
            ],
        )
        accumulator.add_from_spec(spec)
        fig = render_legend_figure(accumulator)
        legend = fig.axes[0].get_legend()
        assert legend is not None
        texts = legend.get_texts()
        assert any("loc" in t.get_text() for t in texts)

    def test_entries_have_labels(self):
        data = pd.DataFrame({"x": [1, 2], "y": [3, 4], "loc": ["A", "B"]})
        accumulator = LegendAccumulator()
        spec = FigureSpec(
            data=data, mappings={}, settings={}, context={}, template_name="custom",
            layers=[
                LayerSpec(
                    geom=GeomPoint(), stat=StatIdentity(),
                    visual_mapping={
                        "x": data["x"], "y": data["y"],
                        "color": pd.Series(["red", "blue"], name="loc"),
                    },
                ),
            ],
        )
        accumulator.add_from_spec(spec)
        fig = render_legend_figure(accumulator)
        legend = fig.axes[0].get_legend()
        assert legend is not None
        texts = legend.get_texts()
        entry_labels = [t.get_text() for t in texts[1:]]
        assert "A" in entry_labels
        assert "B" in entry_labels


class TestLegendIntegration:
    """End-to-end: engine → specs → legend rendering."""

    def test_engine_accumulates_legend_data(self):
        from geofig_engine.core.dataset import Dataset
        from geofig_engine.engine import FigureEngine
        from geofig_engine.templates import bivariate

        data = pd.DataFrame({
            "id": [1, 2, 3],
            "x": [1.0, 2.0, 3.0],
            "y": [4.0, 5.0, 6.0],
            "loc": ["A", "B", "A"],
        })
        dataset = Dataset(dataframe=data, key_column="id")
        engine = FigureEngine()
        template = bivariate(mapping={"x": "x", "y": "y", "color": "loc"})
        specs = engine.build_specs_from_template(dataset, template)

        from geofig_engine.renderers import MatplotlibRenderer
        renderer = MatplotlibRenderer()
        fig = engine.render_legend(renderer)
        assert fig is not None
        assert len(fig.axes) == 1
        legend = fig.axes[0].get_legend()
        assert legend is not None
        texts = legend.get_texts()
        assert any("A" in t.get_text() for t in texts)
        assert any("B" in t.get_text() for t in texts)

    def test_engine_clear_legend(self):
        from geofig_engine.core.dataset import Dataset
        from geofig_engine.engine import FigureEngine
        from geofig_engine.templates import bivariate

        data = pd.DataFrame({
            "id": [1], "x": [1.0], "y": [2.0], "loc": ["A"],
        })
        dataset = Dataset(dataframe=data, key_column="id")
        engine = FigureEngine()
        template = bivariate(mapping={"x": "x", "y": "y", "color": "loc"})
        engine.build_specs_from_template(dataset, template)
        assert len(engine._legend_accumulator.groups) == 1
        engine.clear_legend()
        assert len(engine._legend_accumulator.groups) == 0

    def test_legend_accumulates_across_iterations(self):
        from geofig_engine.core.dataset import Dataset
        from geofig_engine.engine import FigureEngine
        from geofig_engine.templates import bivariate

        data = pd.DataFrame({
            "id": [1], "x": [1.0], "y": [2.0], "loc": ["A"],
        })
        dataset = Dataset(dataframe=data, key_column="id")
        engine = FigureEngine()
        template = bivariate(mapping={"x": "x", "y": "y", "color": "loc"})

        engine.build_specs_from_template(dataset, template)

        data2 = pd.DataFrame({
            "id": [2], "x": [3.0], "y": [4.0], "loc": ["B"],
        })
        dataset2 = Dataset(dataframe=data2, key_column="id")
        engine.build_specs_from_template(dataset2, template)

        assert len(engine._legend_accumulator.groups) == 1
        assert len(engine._legend_accumulator.groups[0].entries) == 2
