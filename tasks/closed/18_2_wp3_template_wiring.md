# Phase 18.2: site_map template wiring (default-on contours)

**Status**: complete
**Phase**: 18.2
**Version target**: v0.3.1+ (patch — bump decision deferred to the epic review WP)
**Dependencies**: `18_2_wp2_stat_geom_contour`

## Description

Wire the contour layer into the `site_map` recipe, default-on (lazy per-render
DEM fetch, old-geomapper parity), opt-out via settings; update the builder
docstring, `docs/api/engine.md`, the example, and the now-stale
`tests/test_site_map.py` render assertions that count line artists (a real
DEM draw on network-enabled runs would break `len(ax.lines) == 0/1`).

## Changes

### `src/geofig_engine/templates/site_map.py`

- `SITE_MAP_DEFAULTS["contours"] = {"interval": 10, "color": "white",
  "linewidth": 0.5, "alpha": 0.6}` (old-geomapper `add_contours` defaults).
- `site_map_builder(...)`:
  - reads `settings["contours"]`; normalized as an enable/disable + config:
    `None`/`False` → **disabled** (no fetch, layer renders empty);
    `True` → defaults; dict merges over defaults and supports
    `"enabled": False` to disable; unknown keys warn? (no — silently
    ignored, matching the basemap setting tolerance);
  - configures a `StatContour(interval=settings.contours["interval"],
    dem_source=settings.contours.get("dem_source"))` — the `dem_source`
    seam passes through the builder so tests can inject a synthetic DEM
    without `render_template`-level stubbing;
  - appends a `Layer(geom=GeomContour(...), stat=StatContour(...),
    mapping={"x": "x", "y": "y"}, zorder=1)` **before** the boundary layer
    (same zorder as boundary; listed first so contours sit under the ring;
    above the zorder-0 basemap image). When disabled, either omit the layer
    or bind a stat that returns empty — **prefer omitting** (clean spec,
    no fetch, no legend noise); the recipe layer count then stays 3 (tests
    assert `len(recipe.layers) == 3`).
  - `enable_contours` helper: `settings_contours(recipe_settings) -> bool`
    small private function shared by builder + tests.
- Module docstring: add a "**Elevation contours** (18.2)" paragraph —
  default-on lazy terrarium DEM fetch (bbox from the provider coordinates,
  10% buffer), old-geomapper defaults, opt-out `settings={"contours": None}`
  / `{"enabled": False}`, offline degrade → warning + no contours, constant
  style (no legend interplay), projection via `CoordGeo`.

### `tests/test_site_map.py` (stale updates — no new coverage here)

- Every render test asserting `ax.lines` counts (or artist counts that a
  contour layer could perturb) pins `settings={"contours": None}` alongside
  `"basemap": None`: `test_no_mapping_renders_points_and_labels`,
  `test_boundary_draws_closed_ring`, `test_labels_optional`,
  `test_color_override_with_nan_group_rows`, the legend-shape tests that
  build specs via `FigureGenerator`, and any test asserting
  `len(recipe.layers) == 3` (recipe.shape tests stay valid because the
  disabled/omitted layer keeps the count at 3 — verify).
- `test_default_settings_enable...` style addition (one line each):
  - `test_default_settings_include_contours` — default `contours` dict
    carries the old-geomapper defaults;
  - `test_contours_opt_out_omits_layer` — `settings={"contours": None}`
    recipe has 3 layers; default recipe has 4.

### `docs/api/engine.md`

- `render_template` → `site_map` template row/paragraph: default-on DEM
  elevation contours (terrarium tiles, lazy fetch, bbox-keyed cache,
  old-geomapper defaults, opt-out + degrade), matching the wp14 basemap row
  wording.

### `examples/site_map_example.py`

- Leave the default-on path (contours render); add a comment noting the
  lazy DEM fetch, the offline degrade, and the
  `settings={"contours": None}` opt-out. Optionally pass an explicit
  `settings={"contours": {"interval": 5, "color": "white", "alpha": 0.5}}`
  to demonstrate the override in one of the two calls.

## Acceptance criteria

- [ ] Default `site_map` recipe includes the contour layer (4 layers);
      `settings={"contours": None}` restores the 3-layer recipe
- [ ] `SITE_MAP_DEFAULTS["contours"]` = old-geomapper defaults
      (`interval=10`, `color="white"`, `linewidth=0.5`, `alpha=0.6`);
      dict overrides merge over defaults; `{"enabled": False}` disables
- [ ] No contour-layer legend entries (constant style; recipe contributes
      nothing to `LegendAccumulator` groups beyond the points layer)
- [ ] Existing `tests/test_site_map.py` render assertions are deterministic
      again after pinning `settings={"contours": None}` (network-free, no
      DEM fetch)
- [ ] `dem_source` override threads from `settings["contours"]["dem_source"]`
      into `StatContour` (test-injection seam)
- [ ] `docs/api/engine.md` + example updated; full suite green after this WP