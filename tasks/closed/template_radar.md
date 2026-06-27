# radar() template

**Status**: open
**Phase**: 12
**Dependencies**: stat_radar

## Description

Create a `radar()` template factory in `templates/radar.py` that composes
existing GoG primitives into a spider/radar chart.

Composition:
- `CoordPolar(theta="x")`
- Line layer: `GeomLine()` + `StatRadar`
  - mapping: `x=x`, `y=y`, `color=color`
- Optional area layer: `GeomArea()` + `StatRadar`
  - mapping: `x=x`, `y=y`, `color=color`

Template parameters:
- `mapping` — requires `x` (axis labels) and `y` (values); accepts `color`
- `shared_axes` — passed to `StatRadar`
- `fill=True` / `fill_alpha=0.15` — control the filled area layer
- `stat` — optional override (default: auto-created `StatRadar`)

## Files to modify

- `src/geofig_engine/templates/radar.py` — new file
- `src/geofig_engine/templates/__init__.py` — export `radar`

## Acceptance criteria

- [ ] `radar(mapping={"x": "axis", "y": "val"}).layers` contains a `GeomLine` layer
- [ ] When `fill=True`, a `GeomArea` layer is included
- [ ] The template sets `CoordPolar(theta="x")`
- [ ] `default_settings` includes a square figsize
