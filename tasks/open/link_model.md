# Linked-axis core model (LinkTransform, AxisLink, FigureSpec.links)

**Status**: open
**Phase**: 14.5
**Dependencies**: (none)

## Description

Foundation of the linked-axes system (ROADMAP Phase 14.5). Introduce declarative secondary axes: a figure has one **main axis** plus named **links**, where world space is the main axis's *post-transform* data space and each link places its local `[0,1]²` space via an ordered translate → rotate → scale affine chain.

Key semantics locked during design:
- World-anchored (flat matrix stacks): link translates are declared in world units ("lower-left of the visible diamond"); no scene-graph nesting
- `matrix()` is built as a pure-numpy 3×3 homogeneous composition `M = T·R·S` in core (matplotlib-free), because fluent `Affine2D` call-order ≠ point-application order — conventions must be pinned by known-corner unit tests (incl. the diamond's rotate-then-squish)

## Files to modify

- `src/geofig_engine/core/link.py` (new) — `GEOM_KINDS`-style module docstring; frozen dataclasses `LinkTransform(translate=(0.0,0.0), rotate=0.0, scale=(1.0,1.0))` and `AxisLink(name, coord, transform, frame=None)`; `LinkTransform.matrix() -> np.ndarray`, `LinkTransform.transform_point(xy)`
- `src/geofig_engine/core/spec.py` — `FigureSpec.links: tuple[AxisLink, ...] = ()`; extend `validate_figure_spec`: link names unique, every non-None `LayerSpec.subplot` resolves to a defined link
- `src/geofig_engine/serialize/converters.py` — `link_to_dict()` / `link_from_dict()` (pattern: `coord_to_dict` at line 232); wire into spec converters
- `tests/test_links.py` (new)

## Acceptance criteria

- [ ] `LinkTransform` frozen dataclass; identity by default; rejects bools/non-numerics
- [ ] `matrix()` returns 3×3 numpy array composing `M = T·R·S`, no matplotlib import in `core/link.py`
- [ ] Unit tests pin point-application order (points experience scale → rotate → translate for declared T,R,S), including "rotate 45° then squash y" corner coordinates
- [ ] `transform_point()` maps local anchors into world space correctly for composed transforms
- [ ] `AxisLink` validates non-empty unique name, Coord instance, LinkTransform instance
- [ ] `FigureSpec.links` accepted by `build_spec()`; duplicate link names raise; unresolved `subplot` raises
- [ ] Layers without subplot routing still validate when links exist (main-axis layers)
- [ ] `link_to_dict`/`link_from_dict` round-trips losslessly; serialized FigureSpec including links round-trips
