# Phase 15: dendrogram template

**Status**: complete
**Phase**: 15
**Version target**: v0.2.0
**Dependencies**: `15_wp6_base_templates`

## Description

Add the `dendrogram` registry template (`ARCHITECTURE.md` `## Templates &
Registry` table: "hierarchical linkage dendrogram from
`ModelResult.tables["linkage"]`"). Input is the **linkage matrix** produced by
`AgglomerativeClusterModel` (n-1 × 4: `[left, right, distance, count]`), already
computed — **no scipy/matplotlib during spec building**. The builder converts
linkage arrays to tree coordinates (**matplotlib-free**) and expresses them as a
`CoordCartesian` `FigureSpec` with line layers for the dendrogram edges and text
layers for leaf labels.

`render_template` already accepts raw frames and ndarrays (`15_wp4`); a
`DataFrame` whose columns are the four linkage columns (or an ndarray with
positional columns) is the intended input. `VisualizationEncoding` for the
cluster model references `template="dendrogram"`, `data_ref="linkage"`.

## Changes

### `src/geofig_engine/templates/dendrogram.py` (new)

- Pure helper `_dendrogram_coords(linkage: np.ndarray) -> dict` — computes
  merge heights `y = distance`, leaf x-order, and the classical
  inverted-U segment coordinates; validated (linkage shape `(n-1, 4)`, monotone
  non-decreasing distances as a warning, not a hard error).
- `dendrogram_builder(mapping=None, settings=None, **_) -> TemplateRecipe` —
  `CoordCartesian` figure: one `GeomLine`/`GeomPath` layer for the tree edges,
  one `GeomText` layer for leaf labels; default settings (title, axis labels
  "Distance", framing) so `render_template(data=linkage_df,
  template="dendrogram")` works with no mapping.

### `src/geofig_engine/engine/api.py`

- Register `dendrogram` in `TEMPLATES`.

## Acceptance criteria

- [ ] `_dendrogram_coords` returns correct merge coordinates for a known
      4-leaf linkage (assert heights/x-order by hand-computed values)
- [ ] `render_template(linkage_df, template="dendrogram")` renders without a
      mapping (default x/y from positional columns)
- [ ] Spec building performs **no** scipy/matplotlib calls (mock-import guard)
- [ ] Malformed input (wrong shape / NaN distances) raises a clear error
- [ ] Rendered figure contains the expected number of edges = 2·(n-1) and n leaf labels
- [ ] New `tests/test_dendrogram.py` covers coordinates, registry, no-mapping
      render, malformed input
- [ ] Committed as a single commit (`geofig-engine: add dendrogram template → v0.2.0`); full suite green

## Files

- `src/geofig_engine/templates/dendrogram.py` (new)
- `src/geofig_engine/engine/api.py`
- `tests/test_dendrogram.py` (new)