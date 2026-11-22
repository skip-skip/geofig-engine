# Geo viewport: basemap fetch bbox and contour DEM bounds

**Status**: complete
**Version target**: v0.3.2 (patch — follows the style-knob ticket)
**Dependencies**: none

## Description

Two geo-viewport defects in the `site_map` stack:

- basemap tiles are fetched for the transient data auto-window even when the
  caller declares `xlim`/`ylim`; the declared viewport must drive the fetch;
- `site_map_builder` accepts a `contours.dem_bounds` override but never passes
  it to `StatContour`.

Both changes preserve the existing fallback behavior and lazy-fetch/degrade
semantics.

## Changes

### `src/geofig_engine/renderers/matplotlib/renderer.py`

- Add a helper that resolves the basemap fetch bbox from declared settings,
  validates partial declarations through `parse_axis_settings`, applies the
  `CoordFlipped` x/y swap, and falls back to the captured data window per axis.
- Call the helper from the basemap integration just before `_render_basemap`.

### `src/geofig_engine/templates/site_map.py`

- Pass `contours_cfg["dem_bounds"]` into `StatContour`.
- Mention the override in the module docstring.

### Tests

- `tests/test_basemap.py`: declared-limit bbox, partial-limit bbox (declared
  `xlim` + data-derived `ylim`), and `CoordFlipped` limit swap.
- `tests/test_contour.py`: builder propagation and invalid `dem_bounds` through
  the builder.

### Docs

- `docs/api/engine.md`: list `dem_bounds` among contour settings.
- `docs/api/dem.md`: document the builder-level DEM fetch bbox override.

## Acceptance criteria

- [ ] Basemap fetch honors declared `xlim`/`ylim`, including `CoordFlipped`
- [ ] Data auto-window remains the fallback when no declared limits exist
- [ ] `site_map_builder(settings={"contours": {"dem_bounds": ...}})` pins the DEM bbox
- [ ] Invalid `dem_bounds` fails clearly at builder/spec time
- [ ] Docs cover the new setting
- [ ] Full suite green; stop before committing for review
- [ ] Committed as `geofig-engine: geo viewport and contour bounds -> v0.3.2`

## Files

- `src/geofig_engine/renderers/matplotlib/renderer.py`
- `src/geofig_engine/templates/site_map.py`
- `tests/test_basemap.py`
- `tests/test_contour.py`
- `docs/api/engine.md`
- `docs/api/dem.md`
- `tasks/open/geo_viewport_basemap_dem_bounds.md`
