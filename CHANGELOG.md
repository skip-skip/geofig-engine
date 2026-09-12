# Changelog

All notable changes to `geofig-engine` are documented here. Versioning follows
the policy in `ARCHITECTURE.md` `## Versioning`: version authority is
`pyproject.toml` `[project] version`; a version bump is its own explicit
commit. Deprecations are introduced in MINOR releases and removed **no earlier
than the next MAJOR** (>= 1.0.0).

## [v0.3.1] - 2026-09-11

### Added

- **Facet / iterator consistency fix (Phase 18.1)** — facets split the data
  into panels within a **single figure**; iterator permutations produce one
  independent figure per combination, per the `core/facet.py` contract, with
  generator + renderer coverage.
- **DEM elevation contours for `site_map` (Phase 18.2)** — default-on
  contour layer from a lazy AWS Terrarium XYZ tile fetch (`io/dem.py`;
  `requests` + `Pillow` only, no new required dependency), bbox-keyed tile
  cache, old-geomapper line style (white, 0.5 pt, alpha 0.6), offline/HTTP
  degrade to no lines.
- **Contour viewport + relief-aware interval fix (Phase 18.2 follow-up)** —
  contour layers render after the viewport is captured from the data layers,
  so the buffered DEM extent can no longer inflate the figure bounds; the
  default contour interval is derived from the DEM relief (~20 levels, ≥ 10 m
  spacing) instead of a fixed 10 m.

Nothing removed or deprecated in this release (additive MINOR).

Per the versioning policy, deprecations introduced in v0.2.0 are retained
through at least the next MAJOR (>= 1.0.0).

## [v0.3.0] - 2026-09-10

### Added

- `geofig_engine.io` data-utilities subpackage (pandas-only, no new required
  dependencies; input frames/series never mutated):
  - **EQuIS format conversion** (`io/equis.py`) — `equisflat_to_sample_df()`
    (flat→wide pivot, first-appearance parameter order, duplicate
    `(sample, parameter)` and non-constant extra columns raise
    `ValueError`), `sample_df_to_equisflat()` (inverse melt, round-trips),
    `equis_crosstab_to_flat()` (parse cross-tab DataFrames or Excel paths;
    underscore / parenthesized unit suffixes; `openpyxl` needed only by
    callers/tests exercising Excel files).
  - **Unit utilities** (`io/units.py`) — `equisflat_normalize_units()`
    group-scoped SI-prefix normalization (documented `SI_PREFIXES` n→G;
    most-frequent recognized unit wins, ties → lexicographically smallest;
    unrecognized units pass through untouched).
  - **Column utilities** (`io/columns.py`) — `ecesis_to_sample_df()` (parse
    Ecesis-style column names into a wide `(analyte, unit)` MultiIndex
    frame) and `create_bins()` (range / quantile categorical binning of
    numeric or datetime columns; NaN → NaN category).

Nothing removed or deprecated in this release (additive MINOR).

Per the versioning policy, deprecations introduced in v0.2.0 are retained
through at least the next MAJOR (>= 1.0.0).

## [v0.2.0] - 2026-09-10

### Added

- Canonical declarative entry `render_template(data, template=<key> |
  FigureTemplate, mapping=, settings=, iterators=, facet=, coord=, savedir=)
  -> list[Figure]` — all args after `data`/`template` are optional. Raw
  `pandas.DataFrame` and ndarray inputs are accepted and wrapped in a
  `DataProvider`.
- `TEMPLATES` registry with `register_template` / `get_template`, seeded with
  the pipeline keys `dendrogram`, `site_map`, `particle_overlay`, the support
  templates `bivariate` / `boxplot_with_points`, and thin adapters over the
  legacy factory set (`histogram`, `pie`, `radar`, `timeseries`, `isotope`,
  `npr_nnp`, `anp_agp`, `nagph_nag`, `piper`, `stiff`).
- `DataProvider` Protocol (`columns` / `resolve` / `expand` / `subset` /
  `unique_values` / `dimensions`) with `DataFrameProvider` for standalone
  frames and `DatasetProvider` adapting the legacy `Dataset`; provider-driven
  `FigureGenerator`. No `geodata` / `geochemmodel` import anywhere in
  `geofig_engine`.
- Geo support: `CoordGeo`, geo geoms (site point, boundary, label,
  annotation-inset, image) and the `[geo]` extra. `site_map` basemap tiles —
  Web-Mercator XYZ mosaic (Esri WorldImagery default, opt-out) — work without
  the `[geo]` extra.

### Deprecated

- `render_template_legacy` — old `(specs, figures, legend_fig)` tuple entry;
  warns at call time. Migrate to the new `render_template`.
- Legacy re-exports `Dataset`, `Dimension`, `DimensionSelector`,
  `ColumnSelector`, `IteratorEngine`, `FigureEngine` — import-time
  `DeprecationWarning`, pointing at `DataFrameProvider` / `DatasetProvider`
  and the generator path.

Per the versioning policy, nothing is removed before 1.0.0; these
deprecations are retained through at least the next MAJOR.