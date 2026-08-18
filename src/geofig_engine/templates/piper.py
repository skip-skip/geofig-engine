import math

import numpy as np
import pandas as pd

from geofig_engine.core.attribute_mapping import resolve_source
from geofig_engine.core.coord import PiperCoord
from geofig_engine.core.dataset import Dataset
from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.layer import LayerSpec
from geofig_engine.core.spec import FigureSpec, build_spec
from geofig_engine.core.stat import StatIdentity
from geofig_engine.utils.typing import SourceType


def _cat_fracs(data, cols):
    total = data[list(cols)].sum(axis=1)
    f0 = data[cols[0]] / total
    f1 = data[cols[1]] / total
    f2 = data[cols[2]] / total
    return f0, f1, f2


def _ternary_x(f1, f0):
    return f1.fillna(0).values * 1.0 + f0.fillna(0).values * 0.5


def _ternary_y(f0):
    sx = math.sqrt(3) / 2.0
    return f0.fillna(0).values * sx


def _diamond_xy(cat_x, cat_y, an_x, an_y):
    h = 0.5 * math.sqrt(3)
    dx = an_y / (4 * h) + 0.5 * an_x - cat_y / (4 * h) + 0.5 * cat_x - 0.5
    dy = 0.5 * an_y + h * an_x + 0.5 * cat_y - h * cat_x
    return np.nan_to_num(dx), np.nan_to_num(dy)


def _resolve_mapping(mapping, data):
    resolved = {}
    ds = Dataset(dataframe=data, key_column=data.columns[0])
    for channel, source in mapping.items():
        result = resolve_source(source, ds, strict=True)
        if isinstance(result, list) and len(result) == 1:
            resolved[channel] = data[result[0]]
        elif isinstance(result, list):
            resolved[channel] = data[result]
        else:
            resolved[channel] = result
    return resolved


def build_piper_specs(
    data: pd.DataFrame,
    left_tri: tuple[str, str, str] = ("Ca", "Mg", "Na+K"),
    right_tri: tuple[str, str, str] = ("HCO3", "SO4", "Cl"),
    mapping: dict[str, SourceType] | None = None,
    title: str = "Piper Diagram",
) -> list[FigureSpec]:
    coord = PiperCoord(
        left_tri=left_tri,
        right_tri=right_tri,
    )

    ca_f, mg_f, nak_f = _cat_fracs(data, left_tri)
    hco3_f, so4_f, cl_f = _cat_fracs(data, right_tri)

    cat_x = _ternary_x(nak_f, mg_f)
    cat_y = _ternary_y(mg_f)
    an_x = _ternary_x(cl_f, so4_f)
    an_y = _ternary_y(so4_f)
    dia_x, dia_y = _diamond_xy(cat_x, cat_y, an_x, an_y)

    visuals = _resolve_mapping(mapping or {}, data)

    layers: list[LayerSpec] = []

    def _point_layer(xv, yv, sp, z=10):
        vm: dict = {"x": pd.Series(xv), "y": pd.Series(yv)}
        vm.update(visuals)
        layers.append(LayerSpec(
            geom=GeomPoint(),
            stat=StatIdentity(),
            visual_mapping=vm,
            subplot=sp,
            zorder=z,
        ))

    _point_layer(cat_x, cat_y, "left_tri")
    _point_layer(an_x, an_y, "right_tri")
    _point_layer(dia_x, dia_y, "diamond")

    spec = build_spec(
        data=data,
        mappings={},
        settings={
            "figsize": (10, 8),
            "title": title,
            "piper_layout": True,
        },
        context={},
        template_name="piper",
        coord=coord,
        layers=layers,
    )
    return [spec]


def piper_overlay_diamond(
    spec: FigureSpec,
    data: pd.DataFrame,
    mapping: dict[str, SourceType] | None = None,
) -> FigureSpec:
    coord = spec.coord
    left_tri = coord.params["left_tri"]
    right_tri = coord.params["right_tri"]
    ca_f, mg_f, nak_f = _cat_fracs(data, left_tri)
    hco3_f, so4_f, cl_f = _cat_fracs(data, right_tri)
    cat_x = _ternary_x(nak_f, mg_f)
    cat_y = _ternary_y(mg_f)
    an_x = _ternary_x(cl_f, so4_f)
    an_y = _ternary_y(so4_f)
    dia_x, dia_y = _diamond_xy(cat_x, cat_y, an_x, an_y)

    visuals = _resolve_mapping(mapping or {}, data)
    vm: dict = {"x": pd.Series(dia_x), "y": pd.Series(dia_y)}
    vm.update(visuals)

    overlay_layer = LayerSpec(
        geom=GeomPoint(),
        stat=StatIdentity(),
        visual_mapping=vm,
        subplot="diamond",
        zorder=10,
    )

    return build_spec(
        data=data,
        mappings=spec.mappings,
        settings={**spec.settings, "piper_overlay": True},
        context=spec.context,
        template_name=spec.template_name,
        coord=spec.coord,
        layers=list(spec.layers) + [overlay_layer],
    )
