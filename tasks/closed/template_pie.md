# pie() template

**Status**: open
**Phase**: 12
**Dependencies**: geom_bar_position, stat_sum, stat_pie_labels, render_text_polar

## Description

Create a `pie()` template factory in `templates/pie.py` that composes existing
GoG primitives into a pie chart.

Composition:
- `CoordPolar(theta="x")`
- Bar layer: `GeomBar(position="identity")` + `StatSum`
  - mapping: `x=angle`, `y=radius`, `width=width`, `color=label`
- Optional label layer: `GeomText()` + `StatPieLabels`
  - mapping: `x=label_x`, `y=label_y`, `label=label_text`

Template parameters:
- `mapping` — requires `x` (category) and `y` (value); accepts `color`, `alpha`
- `stat` — optional override (default: auto-created `StatSum`)
- `show_percent`, `show_count` — label content flags
- `label_distance` — how far from centre labels are placed

## Files to modify

- `src/geofig_engine/templates/pie.py` — new file
- `src/geofig_engine/templates/__init__.py` — export `pie`

## Acceptance criteria

- [ ] `pie(mapping={"x": "cat", "y": "val"}).layers` contains a `GeomBar` layer
- [ ] When `show_percent=True`, a `GeomText` layer is added for labels
- [ ] The template sets `CoordPolar(theta="x")`
- [ ] `default_settings` includes a square figsize
