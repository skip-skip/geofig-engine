# Phase 15: site_map template

**Status**: complete
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_wp6_base_templates`, `15_wp8_coordgeo_geoms`

## Description

Add the `site_map` registry template (`ARCHITECTURE.md` `## Templates &
Registry`: "`CoordGeo` site map: basemap + point layers + grouped legend").
**Basemap *tiles* are deferred to M2** (per the roadmap) — the "basemap" here is
the site boundary/context geometry rendered from the provider, with sample
points colored by a mapping (analyte/fraction/group) and site labels. Grouped
legends come from the existing `LegendGroup` / `LegendAccumulator`
(`renderers/matplotlib/legend.py`), labeling sections like Boundaries /
Facilities / Sample Points / QA overlay.

Consumes `GeoData`-style provider views (`samples`/`long` with coordinates)
duck-typed — this template never imports geodata.

## Changes

### `src/geofig_engine/templates/site_map.py` (new)

- `site_map_builder(mapping=None, settings=None, coord=None, **_) -> TemplateRecipe`:
  - `CoordGeo` recipe coord (override with `coord=`), lon/lat from the mapping
    (default: first `x`/`y`-like coordinate columns)
  - Layers: `GeomBoundary` (site outline from an optional `boundary` path in
    the provider), `GeomSitePoint` (colored by `color` mapping), `GeomLabel`
    (site/well names when a label column present)
  - Grouped legend via `LegendGroup`/`LegendAccumulator` sections
    (Boundaries / Facilities / Sample Points); no auto-rendering of tile
    services
- `Default settings`: title, coordinate aspect bounds (lon/lat extent).

### `src/geofig_engine/engine/api.py`

- Register `site_map` in `TEMPLATES`.

## Acceptance criteria

- [ ] `render_template(boundary_df_or_geodata_view, template="site_map")` renders
      boundary + sample points + labels with a grouped legend
- [ ] `color` mapping colors points by group; legend groups by section
- [ ] No mapping required: sensible lon/lat defaults resolve from the recipe
- [ ] Renders without the `[geo]` extra (identity projection); with `[geo]`
      installed, honors `CoordGeo` projection when `crs=` is set
- [ ] No tile-service requests are made/prepared (deferred to M2; a docstring
      note marks the future tile hook)
- [ ] New `tests/test_site_map.py` covers no-mapping render, point coloring,
      boundary draw, grouped legend sections, and the no-geo fallback
- [ ] Committed as a single commit (`geofig-engine: add site_map template → v0.2.0`); full suite green

## Files

- `src/geofig_engine/templates/site_map.py` (new)
- `src/geofig_engine/engine/api.py`
- `tests/test_site_map.py` (new)