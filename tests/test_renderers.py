"""
Tests for FigEngine renderers.
"""

import pandas as pd

from geofig_engine.core.spec import FigureSpec
from geofig_engine.renderers import BaseRenderer, MatplotlibRenderer


class DummyRenderer(BaseRenderer):
    def render(self, spec: FigureSpec) -> str:
        return f"rendered {spec.template_name}"


def test_base_renderer_render_all():
    renderer = DummyRenderer()
    spec_a = FigureSpec(
        data=pd.DataFrame({"x": [1], "y": [2]}),
        mappings={"x": ["x"], "y": ["y"]},
        settings={},
        context={},
        template_name="a",
    )
    spec_b = FigureSpec(
        data=pd.DataFrame({"x": [3], "y": [4]}),
        mappings={"x": ["x"], "y": ["y"]},
        settings={},
        context={},
        template_name="b",
    )

    results = renderer.render_all([spec_a, spec_b])

    assert results == ["rendered a", "rendered b"]


def test_matplotlib_renderer_renders_figure():
    renderer = MatplotlibRenderer()
    data = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    spec = FigureSpec(
        data=data,
        mappings={"x": ["x"], "y": ["y"], "color": "red", "marker": "o"},
        settings={"title": "Test Plot", "figsize": (4, 3), "xlabel": "X", "ylabel": "Y"},
        context={},
        template_name="test",
    )

    fig = renderer.render(spec)

    assert fig is not None
    assert fig.axes
    ax = fig.axes[0]
    assert ax.get_title() == "Test Plot"
    assert ax.get_xlabel() == "X"
    assert ax.get_ylabel() == "Y"
    assert tuple(fig.get_size_inches()) == (4.0, 3.0)
