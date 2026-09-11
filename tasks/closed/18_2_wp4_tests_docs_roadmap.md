# Phase 18.2: contour tests + docs/ROADMAP un-defer

**Status**: complete
**Phase**: 18.2
**Version target**: v0.3.1+ (patch — bump decision deferred to the epic review WP)
**Dependencies**: `18_2_wp3_template_wiring`

## Description

Behavioral coverage for the shipped contour stack (unit + renderer
integration, all network-free) and the documentation/ROADMAP un-defer of the
DEM contour geom. Closes the epic.

## Changes

### `tests/test_contour.py` (new)

- `StatContour` with a **synthetic DEM source** (`dem_source` returning a
  small lon/lat grid, e.g. `z = 100 + 25*sin(3x)*cos(2y)` over a ~1° bbox):
  - produced frame is exactly `{"x": [...], "y": [...]}` (columns == 2);
  - polylines lie on the DEM domain; **NaN separators** split distinct
    segments; trailing separator trimmed;
  - a level-set matches `np.arange(nanmin, nanmax, interval)` scan —
    closed loops at interval multiples (count levels within
    `[nanmin, nanmax)`);
  - flat/constant DEM → zero levels → empty frame;
  - all-NaN DEM → empty frame + `UserWarning` ("contours unavailable");
  - `dem_source` raising → `UserWarning` + empty frame (never propagates);
  - missing coordinate columns in the provider frame → empty frame, **no**
    source call;
  - `interval <= 0` → `ValueError`;
  - `dem_bounds` override pins the bbox fed to the source.
- `GeomContour`:
  - geom registration (name `"contour"`, channels, defaults);
  - renderer dispatch: `render_template(... site_map ...)`-style spec with a
    contour layer draws `ax.lines` (one per level-set or per
    NaN-separated segment, consistent with `render_boundary`) above the
    basemap and below the boundary ring.
- Non-WGS84 projection (pyproj-gated, `skipif` both ways like
  `test_site_map.py`): with `[geo]`, contour lon/lat polylines project like
  the boundary layer; without `[geo]`, identity fallback warning + render.

### `tests/test_site_map.py` (small additions)

- `test_contours_render_default_on` — `render_template(..., settings=
  {"basemap": None})` **plus the wp3-provided seam** (monkeypatched
  `StatContour.compute` or `dem_source` via settings): default recipe
  produces line artists; `settings={"contours": None}` produces none.
- Update the module docstring reference line (contours now imported in the
  classmap) if the class docstring lists the layer stack.

### Docs

- `ROADMAP.md`:
  - Phase 18.2 section: add `## ✅ Phase 18.2 — DEM elevation contours
    (site_map)` after the 18.1 entry — terrarium tiles, default-on, cache,
    old-geomapper parity, WPs `tasks/closed/18_2_*.md`, suite count.
  - Phase 15 bullet (l.455): "**Deferred to M2:** DEM contour, stream
    geoms" → DEM contour **shipped via 18.2**; stream geoms remain deferred.
- `ARCHITECTURE.md`:
  - l.80 `| DEM contour / stream geoms | deferred |` →
    `| DEM contour (site_map, 18.2) / stream geoms | contour implemented, streams deferred |`;
  - Phase-15 geo-support checkbox (l.633-634) mention; the M2 deferred
    geoms checkbox (l.640) drops contours from the deferred list (leaving
    streams, `GeomTable`/`GeomColorbar`);
  - the geo geoms table (l.346-355) marks the contour geom implemented.
- `docs/api/engine.md` / `docs/api/dem.md` (new, small): the DEM access
  contract — terrarium endpoint, decode formula, cache layout, fail/degrade
  semantics; a `site_map` contours settings row in the engine doc.

## Acceptance criteria

- [ ] `tests/test_contour.py` covers stat behavior (columns, NaN
      separators, level scan, empty/flat/all-NaN/elevation-sourced cases,
      interval validation, `dem_bounds`, **no-network** invariant) and the
      renderer integration (lines above basemap/below boundary;
      pyproj-gated projection both ways)
- [ ] `tests/test_site_map.py` gains a default-on / opt-out render pair
      using the wp3 seam; no test in the suite touches the network
- [ ] ROADMAP Phase 18.2 entry added; Phase 15 deferral line and
      ARCHITECTURE deferral rows/checkboxes updated (contours shipped,
      streams still deferred)
- [ ] `docs/api/engine.md` + `docs/api/dem.md` document the contour
      setting and the DEM access contract
- [ ] Full suite green (baseline 1392 passed / 6 skipped — 6 pyproj-gated
      skips unchanged; no new skips from the warning policy)
- [ ] Committed as a single commit
      (`geofig-engine: contour tests + docs → v0.3.1`)