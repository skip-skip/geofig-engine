# Changelog

All notable changes to `geofig-engine` are documented here. Versioning follows
the policy in `ARCHITECTURE.md` `## Versioning`: version authority is
`pyproject.toml` `[project] version`; a version bump is its own explicit
commit. Deprecations are introduced in MINOR releases and removed **no earlier
than the next MAJOR** (>= 1.0.0).

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