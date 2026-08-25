"""
Converter functions for serializing core types to/from plain dicts.

All converters produce JSON-compatible dicts (lists, dicts, scalars, None).
pd.Series objects are converted using a wrapper with ``__series__`` sentinel.
pd.DataFrame objects use ``orient="split"`` format.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from geofig_engine.core.geom import (
    Geom,
    GeomAbline,
    GeomArea,
    GeomBar,
    GeomBox,
    GeomErrorbar,
    GeomFunctionLine,
    GeomHSpan,
    GeomLine,
    GeomPoint,
    GeomRect,
    GeomRibbon,
    GeomStepLine,
    GeomText,
    GeomViolin,
    GeomVSpan,
)
from geofig_engine.core.coord import (
    Coord,
    CoordCartesian,
    CoordFlipped,
    CoordFixed,
    CoordPolar,
    PiperCoord,
    StiffCoord,
    TernaryCoord,
)
from geofig_engine.core.facet import (
    Facet,
    FacetGrid,
    FacetNull,
    FacetWrap,
)
from geofig_engine.core.link import AxisLink, LinkTransform
from geofig_engine.core.scale import (
    Scale,
    ScaleConstant,
    ScaleContinuous,
    ScaleDateTime,
    ScaleNormalize,
    ScaleOrdinal,
)
from geofig_engine.core.stat import (
    Stat,
    StatBin,
    StatCount,
    StatFn,
    StatIdentity,
    StatIonFractions,
    StatPieLabels,
    StatRadar,
    StatSmooth,
    StatSum,
)
from geofig_engine.core.spec import FigureSpec, build_spec
from geofig_engine.core.layer import LayerSpec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _series_to_dict(series: pd.Series) -> dict:
    return {
        "__series__": True,
        "name": series.name,
        "values": series.tolist(),
    }


def _series_from_dict(data: dict) -> pd.Series:
    return pd.Series(data["values"], name=data.get("name"))


def _visual_mapping_to_dict(vm: dict[str, Any]) -> dict[str, Any]:
    return {
        k: _series_to_dict(v) if isinstance(v, pd.Series) else v
        for k, v in vm.items()
    }


def _visual_mapping_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, dict) and v.get("__series__"):
            result[k] = _series_from_dict(v)
        else:
            result[k] = v
    return result


def _dataframe_to_dict(df: pd.DataFrame) -> dict:
    return df.to_dict(orient="split")


def _dataframe_from_dict(data: dict) -> pd.DataFrame:
    return pd.DataFrame(
        data["data"],
        columns=data["columns"],
        index=data.get("index"),
    )


# ---------------------------------------------------------------------------
# Geom converters
# ---------------------------------------------------------------------------

def geom_to_dict(geom: Geom) -> dict:
    base: dict[str, Any] = {"type": geom.name}
    if isinstance(geom, GeomAbline):
        if geom.slope is not None:
            base["slope"] = geom.slope
            base["intercept"] = geom.intercept
        else:
            base["x1"] = geom.x1
            base["y1"] = geom.y1
            base["x2"] = geom.x2
            base["y2"] = geom.y2
    elif isinstance(geom, GeomFunctionLine):
        base["func"] = geom.func
        base["label"] = geom.label
    elif isinstance(geom, GeomBox):
        base["showfliers"] = geom.showfliers
        base["showmeans"] = geom.showmeans
        base["show_n"] = geom.show_n
        base["min_box_n"] = geom.min_box_n
        base["is_horizontal"] = geom.is_horizontal
        base["sort_mode"] = geom.sort_mode
        base["smush"] = geom.smush
        base["box_width"] = geom.box_width
    elif isinstance(geom, GeomViolin):
        base["show_medians"] = geom.show_medians
        base["sort_mode"] = geom.sort_mode
        base["smush"] = geom.smush
    elif isinstance(geom, GeomStepLine):
        base["where"] = geom.where
    elif isinstance(geom, GeomPoint):
        if geom.jitter != 0.0:
            base["jitter"] = geom.jitter
        if geom.dodge != 0.0:
            base["dodge"] = geom.dodge
    elif isinstance(geom, GeomBar):
        if geom.position != "identity":
            base["position"] = geom.position
    return base


def geom_from_dict(data: dict) -> Geom:
    geom_type = data["type"]
    if geom_type == "point":
        return GeomPoint(
            jitter=data.get("jitter", 0.0),
            dodge=data.get("dodge", 0.0),
        )
    elif geom_type == "line":
        return GeomLine()
    elif geom_type == "function_line":
        return GeomFunctionLine(
            func=data.get("func", ""),
            label=data.get("label"),
        )
    elif geom_type == "bar":
        return GeomBar(position=data.get("position", "identity"))
    elif geom_type == "area":
        return GeomArea()
    elif geom_type == "ribbon":
        return GeomRibbon()
    elif geom_type == "text":
        return GeomText()
    elif geom_type == "errorbar":
        return GeomErrorbar()
    elif geom_type == "box":
        return GeomBox(
            showfliers=data.get("showfliers", True),
            showmeans=data.get("showmeans", False),
            show_n=data.get("show_n", False),
            min_box_n=data.get("min_box_n", 1),
            is_horizontal=data.get("is_horizontal", False),
            sort_mode=data.get("sort_mode", "none"),
            smush=data.get("smush", False),
            box_width=data.get("box_width", 0.8),
        )
    elif geom_type == "violin":
        return GeomViolin(
            show_medians=data.get("show_medians", True),
            sort_mode=data.get("sort_mode", "none"),
            smush=data.get("smush", False),
        )
    elif geom_type == "step_line":
        return GeomStepLine(
            where=data.get("where", "pre"),
        )
    elif geom_type == "abline":
        if "slope" in data:
            return GeomAbline(
                slope=data["slope"],
                intercept=data.get("intercept", 0.0),
            )
        else:
            return GeomAbline(
                x1=data["x1"], y1=data["y1"],
                x2=data["x2"], y2=data["y2"],
            )
    elif geom_type == "hspan":
        return GeomHSpan()
    elif geom_type == "vspan":
        return GeomVSpan()
    elif geom_type == "rect":
        return GeomRect()
    else:
        raise ValueError(f"Unknown geom type: {geom_type}")


# ---------------------------------------------------------------------------
# Coord converters
# ---------------------------------------------------------------------------

def coord_to_dict(coord: Coord) -> dict:
    return {"type": coord.name, "params": coord.params}


def coord_from_dict(data: dict) -> Coord:
    name = data["type"]
    params = data.get("params", {})
    if name == "cartesian":
        return CoordCartesian()
    elif name == "flipped":
        return CoordFlipped()
    elif name == "polar":
        return CoordPolar(**params)
    elif name == "fixed":
        return CoordFixed(**params)
    elif name == "ternary":
        return TernaryCoord(
            channels=tuple(params.get("channels", ("a", "b", "c"))),
            handedness=params.get("handedness", "left"),
        )
    elif name == "piper":
        return PiperCoord(
            left_tri=tuple(params.get("left_tri", params.get("cation_cols", ["Ca", "Mg", "Na+K"]))),
            right_tri=tuple(params.get("right_tri", params.get("anion_cols", ["HCO3", "SO4", "Cl"]))),
        )
    elif name == "stiff":
        return StiffCoord(
            ca=params.get("ca", 0.0),
            mg=params.get("mg", 0.0),
            na_k=params.get("na_k", 0.0),
            cl=params.get("cl", 0.0),
            hco3=params.get("hco3", 0.0),
            so4=params.get("so4", 0.0),
            sample_title=params.get("sample_title", ""),
        )
    else:
        raise ValueError(f"Unknown coord type: {name}")


# ---------------------------------------------------------------------------
# Link converters
# ---------------------------------------------------------------------------

def link_to_dict(link: AxisLink) -> dict:
    """Convert an AxisLink to a JSON-compatible dict."""
    result = {
        "name": link.name,
        "coord": coord_to_dict(link.coord),
        "transform": link.transform.to_dict(),
    }
    if link.frame is not None:
        result["frame"] = link.frame
    return result


def link_from_dict(data: dict) -> AxisLink:
    """Reconstruct an AxisLink from its dict representation."""
    return AxisLink(
        name=data["name"],
        coord=coord_from_dict(data["coord"]),
        transform=LinkTransform.from_dict(data.get("transform", {})),
        frame=data.get("frame"),
    )


# ---------------------------------------------------------------------------
# Facet converters
# ---------------------------------------------------------------------------

def facet_to_dict(facet: Facet) -> dict:
    return {
        "type": facet.name,
        "by": list(facet.by),
        "scales": facet.scales,
        "params": facet.params,
    }


def facet_from_dict(data: dict) -> Facet:
    name = data["type"]
    scales = data.get("scales", "fixed")
    if name == "null":
        return FacetNull()
    elif name == "wrap":
        return FacetWrap(
            by=data.get("by", []),
            ncol=data.get("params", {}).get("ncol", 0),
            nrow=data.get("params", {}).get("nrow", 0),
            scales=scales,
        )
    elif name == "grid":
        params = data.get("params", {})
        return FacetGrid(
            row=params["row"],
            col=params["col"],
            scales=scales,
        )
    else:
        raise ValueError(f"Unknown facet type: {name}")


# ---------------------------------------------------------------------------
# Scale converters
# ---------------------------------------------------------------------------

def scale_to_dict(scale: Scale) -> dict:
    return {
        "type": scale.name,
        "params": scale.params,
        "domain": list(scale.domain) if scale.domain else None,
        "range": list(scale.range) if scale.range else None,
    }


def scale_from_dict(data: dict) -> Scale:
    name = data["type"]
    params = data.get("params", {})
    domain = tuple(data["domain"]) if data.get("domain") else None
    range_ = tuple(data["range"]) if data.get("range") else None
    if name == "continuous":
        return ScaleContinuous(
            trans=params.get("trans", "identity"),
            domain=domain,
            range=range_,
        )
    elif name == "ordinal":
        return ScaleOrdinal(
            palette=params.get("palette", ()),
            domain=domain,
            range=range_,
        )
    elif name == "constant":
        return ScaleConstant(value=params.get("value"))
    elif name == "datetime":
        return ScaleDateTime(
            fmt=params.get("format", "%Y-%m-%d"),
            domain=domain,
            range=range_,
        )
    elif name == "normalize":
        return ScaleNormalize(
            range_min=params.get("range_min", 0.0),
            range_max=params.get("range_max", 1.0),
        )
    else:
        raise ValueError(f"Unknown scale type: {name}")


# ---------------------------------------------------------------------------
# Stat converters
# ---------------------------------------------------------------------------

def stat_to_dict(stat: Stat) -> dict:
    return {"type": stat.name, "params": stat.params}


def stat_from_dict(data: dict) -> Stat:
    name = data["type"]
    params = data.get("params", {})
    if name == "identity":
        return StatIdentity()
    elif name == "fn":
        # Callable can't be serialized; post-engine data is already transformed.
        return StatIdentity()
    elif name == "bin":
        return StatBin(**params)
    elif name == "count":
        return StatCount()
    elif name == "smooth":
        return StatSmooth(**params)
    elif name == "sum":
        return StatSum(**params)
    elif name == "pie_labels":
        return StatPieLabels(**params)
    elif name == "radar":
        return StatRadar(**params)
    elif name == "ion_fractions":
        return StatIonFractions(
            cations=[tuple(g) for g in params.get("cations", [["Ca"], ["Mg"], ["Na", "K"]])],
            anions=[tuple(g) for g in params.get("anions", [["HCO3", "CO3"], ["SO4"], ["Cl"]])],
        )
    else:
        raise ValueError(f"Unknown stat type: {name}")


# ---------------------------------------------------------------------------
# LayerSpec converters
# ---------------------------------------------------------------------------

def layer_spec_to_dict(layer: LayerSpec) -> dict:
    result = {
        "geom": geom_to_dict(layer.geom),
        "stat": stat_to_dict(layer.stat),
        "visual_mapping": _visual_mapping_to_dict(layer.visual_mapping),
        "data_override": layer.data_override,
    }
    if layer.zorder is not None:
        result["zorder"] = layer.zorder
    if layer.subplot is not None:
        result["subplot"] = layer.subplot
    if layer.xlim is not None:
        result["xlim"] = list(layer.xlim)
    if layer.ylim is not None:
        result["ylim"] = list(layer.ylim)
    return result


def layer_spec_from_dict(data: dict) -> LayerSpec:
    xlim = data.get("xlim")
    ylim = data.get("ylim")
    return LayerSpec(
        geom=geom_from_dict(data["geom"]),
        stat=stat_from_dict(data["stat"]),
        visual_mapping=_visual_mapping_from_dict(data["visual_mapping"]),
        data_override=data.get("data_override"),
        zorder=data.get("zorder"),
        subplot=data.get("subplot"),
        xlim=tuple(xlim) if xlim is not None else None,
        ylim=tuple(ylim) if ylim is not None else None,
    )


# ---------------------------------------------------------------------------
# FigureSpec converters
# ---------------------------------------------------------------------------

def figure_spec_to_dict(spec: FigureSpec) -> dict:
    """Convert a FigureSpec to a JSON-compatible dict."""
    return {
        "template_name": spec.template_name,
        "iterator_key": list(spec.iterator_key),
        "coord": coord_to_dict(spec.coord),
        "facet": facet_to_dict(spec.facet),
        "layers": [layer_spec_to_dict(l) for l in spec.layers],
        "settings": spec.settings,
        "context": spec.context,
        "mappings": _visual_mapping_to_dict(spec.mappings),
        "data": _dataframe_to_dict(spec.data),
        "links": [link_to_dict(link) for link in spec.links],
    }


def figure_spec_from_dict(data: dict) -> FigureSpec:
    """Reconstruct a FigureSpec from a JSON-compatible dict."""
    df = _dataframe_from_dict(data["data"])
    layers = [layer_spec_from_dict(l) for l in data["layers"]]
    return build_spec(
        data=df,
        mappings=_visual_mapping_from_dict(data["mappings"]),
        settings=data["settings"],
        context=data["context"],
        template_name=data["template_name"],
        iterator_key=tuple(data.get("iterator_key", [])),
        layers=layers,
        coord=coord_from_dict(data["coord"]),
        facet=facet_from_dict(data["facet"]),
        links=tuple(link_from_dict(link) for link in data.get("links", [])),
    )


# ---------------------------------------------------------------------------
# JSON convenience
# ---------------------------------------------------------------------------

def spec_to_json(spec: FigureSpec, **kwargs: Any) -> str:
    """Serialize a FigureSpec to a JSON string."""
    return json.dumps(figure_spec_to_dict(spec), **kwargs)


def spec_from_json(json_str: str) -> FigureSpec:
    """Deserialize a FigureSpec from a JSON string."""
    data = json.loads(json_str)
    return figure_spec_from_dict(data)
