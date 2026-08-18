import pandas as pd

from geofig_engine.core.coord import StiffCoord
from geofig_engine.core.geom import GeomArea
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.core.spec import build_spec


def plot_stiff(
    ca: float,
    mg: float,
    na_k: float,
    cl: float,
    hco3: float,
    so4: float,
    title: str = "",
    figsize: tuple[float, float] = (6, 6),
):
    scale = max(ca, mg, na_k, cl, hco3, so4, 1.0) * 1.3
    left_vals = [na_k, ca, mg]
    right_vals = [cl, hco3, so4]
    y_positions = [2, 1, 0]

    poly_x = []
    poly_y = []
    for v, y in zip(left_vals, y_positions):
        poly_x.append(-v / scale)
        poly_y.append(y)
    for v, y in zip(right_vals, y_positions[::-1]):
        poly_x.append(v / scale)
        poly_y.append(y)
    poly_x.append(-na_k / scale)
    poly_y.append(2)

    data = pd.DataFrame({"x": poly_x, "y": poly_y})
    coord = StiffCoord(ca=ca, mg=mg, na_k=na_k, cl=cl, hco3=hco3, so4=so4, sample_title=title)

    layers = [
        LayerSpec(
            geom=GeomArea(),
            stat=StatIdentity(),
            visual_mapping={
                "x": data["x"],
                "y": data["y"],
                "color": "lightblue",
            },
        ),
    ]

    return build_spec(
        data=data,
        mappings={},
        settings={"figsize": figsize},
        context={},
        template_name="stiff",
        coord=coord,
        layers=layers,
    )
