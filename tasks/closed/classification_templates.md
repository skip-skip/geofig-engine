# Classification plot templates (NPR/NNP, ANP/AGP, NAGpH)

**Status**: open
**Phase**: 14
**Dependencies**: Phase 13 (GeomRect, GeomHSpan, GeomVSpan, GeomAbline, zorder)

## Description

Create three geochemical classification plot templates using composition of existing GoG components (GeomPoint for data + Phase 13 annotation layers for reference regions/lines). No new Geom types needed.

### Templates

**`npr_nnp(mapping, npr_crit=3, nnp_crit=20) -> FigureTemplate`**
Acid rock drainage classification (Net Potential Ratio vs Net Neutralization Potential).
- 4 quadrants defined by horizontal/vertical threshold lines at `(npr_crit, nnp_crit)`
- `GeomAbline` at x=npr_crit and y=nnp_crit (dashed, black)
- `GeomRect` quadrants with colored fills:
  - PAG (Potential Acid Generation): x < npr_crit, y < nnp_crit (red tint)
  - Non-PAG: x >= npr_crit, y >= nnp_crit (green tint)
  - Uncertain/PAG: other two quadrants (yellow tint)
- `GeomText` labels in each quadrant ("PAG", "Non-PAG", "Uncertain")
- Data points via `GeomPoint` on top (zorder=10)

**`anp_agp(mapping) -> FigureTemplate`**
Acid Neutralization Potential vs Acid Generation Potential classification.
- Threshold slope lines: y = k * x for k in {1, 2, 3, 4} (dashed reference lines)
- `GeomAbline` for each threshold slope
- `GeomRect`/`GeomHSpan` for reference regions
- `GeomText` labels for each region
- Data points via `GeomPoint` on top

**`nagph_nag(mapping) -> FigureTemplate`**
NAG pH vs Net Acid Generation classification.
- Vertical threshold lines at key pH values
- `GeomVSpan` for pH ranges (acidic, neutral, alkaline)
- `GeomAbline` for any reference thresholds
- `GeomText` labels
- Data points via `GeomPoint` on top

### All templates follow the same pattern:
```python
def npr_nnp(
    mapping: dict[str, SourceType],
    npr_crit: float = 3,
    nnp_crit: float = 20,
) -> FigureTemplate:
    return FigureTemplate(
        name="npr_nnp",
        layers=[
            # Annotation layers (low zorder)
            Layer(geom=GeomRect(...), stat=StatIdentity(), mapping=..., zorder=0),
            Layer(geom=GeomAbline(...), stat=StatIdentity(), mapping=..., zorder=1),
            Layer(geom=GeomText(...), stat=StatIdentity(), mapping=..., zorder=2),
            # Data layer (high zorder)
            Layer(geom=GeomPoint(), stat=StatIdentity(), mapping=mapping, zorder=10),
        ],
        default_settings={"figsize": (8, 8), "title": "NPR vs NNP", ...},
    )
```

### Constants
Define default threshold values and color schemes as module-level dicts for easy customization.

## Files to create / modify

- `src/geofig_engine/templates/npr_nnp.py` — `npr_nnp()` template
- `src/geofig_engine/templates/anp_agp.py` — `anp_agp()` template
- `src/geofig_engine/templates/nagph_nag.py` — `nagph_nag()` template
- `src/geofig_engine/templates/__init__.py` — export all three

## Acceptance criteria

- [ ] `npr_nnp()` produces a valid FigureTemplate with annotation + point layers
- [ ] `npr_nnp()` shows 4 quadrants with correct PAG/Non-PAG/Uncertain coloring
- [ ] `npr_nnp()` threshold values are configurable
- [ ] `anp_agp()` shows threshold slope lines with labeled regions
- [ ] `nagph_nag()` shows pH range bands with threshold lines
- [ ] All templates work with `render_template()` end-to-end
- [ ] Appropriate `default_settings` (figsize, labels, legends) included
- [ ] 526 existing tests still pass
