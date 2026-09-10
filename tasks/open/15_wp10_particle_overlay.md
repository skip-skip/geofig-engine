# Phase 15: particle_overlay template

**Status**: open
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_wp6_base_templates`, `15_wp8_coordgeo_geoms`

## Description

Add the `particle_overlay` registry template (`ARCHITECTURE.md` `## Templates &
Registry`: "per-photo QA overlay: segmentation edges on the (downsampled) source
image, classified particles, per-photo QA stats — the only figure for
`ParticleImageModel`"). It combines an image layer, polygon/point particle
layers, and a QA-stats caption, rendered on the shared matplotlib backend with
`OffsetImage` insets from `15_wp8`.

Consumes `ParticleImageModel` results duck-typed: source image (as an array via
an `image` cell), particle table (`tables["particles"]` with contour/centroid/
class columns), QA summary. Spec building must stay matplotlib-free.

## Changes

### `src/geofig_engine/templates/particle_overlay.py` (new)

- `particle_overlay_builder(mapping=None, settings=None, **_) -> TemplateRecipe`:
  - Image layer: `GeomImageInset` (or a full-frame image layer) rendering the
    source image / segmentation mask as the figure background
  - `GeomBoundary`-style layers for particle contours (segmentation edges,
    from contour vertex columns)
  - `GeomSitePoint`/`GeomPoint` for classified particles, `color` by class;
    size by measured area where available
  - QA stats caption: per-photo n particles, mean/summary stats rendered as a
    `GeomText` / title block
  - Grouped legend sections (Particles / QA overlay) via
    `LegendGroup`/`LegendAccumulator`
- Default mapping resolves from the particle-table columns (contours,
  centroid x/y, class, area); mapping overrides merge on top.

### `src/geofig_engine/engine/api.py`

- Register `particle_overlay` in `TEMPLATES`.

## Acceptance criteria

- [ ] `render_template(particles_df + image, template="particle_overlay")` renders
      source image, particle contours, classified points, and the QA caption
- [ ] Works with the real `ParticleImageModel` tables shape (contour vertices,
      centroid, class, area) — verified against a recorded output
- [ ] No mapping required (defaults resolve); mapping overrides accepted
- [ ] Spec building is matplotlib-free (mock-import guard, like dendrogram)
- [ ] Image absent → clear error message rather than a blank figure
- [ ] New `tests/test_particle_overlay.py` uses a synthetic image array
      (no cv2/skimage dependency)
- [ ] Committed as a single commit (`geofig-engine: add particle_overlay template → v0.2.0`); full suite green

## Files

- `src/geofig_engine/templates/particle_overlay.py` (new)
- `src/geofig_engine/engine/api.py`
- `tests/test_particle_overlay.py` (new)