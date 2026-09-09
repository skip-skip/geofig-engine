# Phase 14.59: Offset semantics across all four edges

**Status**: open
**Phase**: 14.59
**Dependencies**: `14_59_wp10_majortick_renderer`

## Description

Parametrized render tests proving `majortick_offset` behaves the same on all
four frame edges. Build minimal framed cartesian specs (explicit `xlim`/
`ylim`, one numeric or named axis at a time) and assert the interior/exterior
tip positions for offsets `{0, 0.5, 1}`:

- bottom: interior tip y = ylo + offset*L; exterior tip y = ylo - (1-offset)*L
- top: interior tip y = yhi - offset*L; exterior tip y = yhi + (1-offset)*L
- left: interior tip x = xlo + offset*L; exterior tip x = xlo - (1-offset)*L
- right: interior tip x = xhi - offset*L; exterior tip x = xhi + (1-offset)*L

## Files to modify

- `tests/test_stiff.py` (or a dedicated `tests/test_axis_majorticks.py` if
  the offset matrix gets large — prefer existing file)

## Acceptance criteria

- [ ] Parametrized over edge x {bottom, top, left, right} and offset {0, 0.5, 1}
- [ ] Tip positions verified per the formulas for each edge
- [ ] All cases render with `majortick_length` set and no other template
      dependencies