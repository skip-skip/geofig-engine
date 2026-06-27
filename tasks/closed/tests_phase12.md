# Tests for all Phase 12 changes

**Status**: open
**Phase**: 12
**Dependencies**: geom_bar_position, stat_sum, stat_pie_labels, stat_radar, render_text_polar, template_pie, template_radar

## Description

Add tests for all Phase 12 additions: GeomBar position, new stats, polar text
alignment, pie template, and radar template.

## Files to modify

- `tests/test_geom.py` — test `GeomBar(position="stack")` and `GeomBar(position="fill")`
- `tests/test_stat.py` — test `StatSum`, `StatPieLabels`, `StatRadar` output shapes and values
- `tests/test_renderers.py` — integration tests for stacked bars, pie chart, radar chart
- `tests/test_templates.py` — test `pie()` and `radar()` creation and defaults
- `tests/test_serialize.py` — round-trip for `GeomBar.position` and new stats

## Acceptance criteria

- [ ] All new tests pass alongside existing 444 tests
- [ ] Stat tests verify correct aggregation, normalisation, and label formatting
- [ ] Renderer tests verify the correct number/types of matplotlib patches
- [ ] Template tests verify layer structure and coord settings
