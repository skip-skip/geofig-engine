# Phase 14.59: Docs & roadmap update

**Status**: open
**Phase**: 14.59
**Dependencies**: `14_59_wp6_tests`

## Description

Document the migration: the Stiff diagram is now an ordinary `CoordCartesian`
figure built from the declarative frame + layer machinery, and the deprecated
`PiperCoord` / `StiffCoord` coordinate types are gone. Record the new
`abs_ticks` / `tick_labels` frame capabilities.

## Changes

### `ARCHITECTURE.md`

- Remove `PiperCoord` and `StiffCoord` from the built-in Coords list (section 8
  and the coord section reference).
- Add a note that advanced diagrams compose `CoordCartesian` / `TernaryCoord`
  with nested `FigureSpec` children or settings-driven frames (Stiff is a
  cartesian template); dependency rules unchanged.

### `ROADMAP.md`

- Add a ✅ Phase 14.59 entry: stiff-as-cartesian migration (named/absolute tick
  labels, framed xlabel, new `GeomPolygon` geom with outline
  color/alpha/weight/style), removal of `StiffCoord` and deprecated `PiperCoord`,
  test count.

## Acceptance criteria

- [ ] ARCHITECTURE.md no longer lists `PiperCoord` / `StiffCoord`
- [ ] ROADMAP.md documents Phase 14.59 with final test count
- [ ] No stale references to the removed coord classes in docs

## Files

- `ARCHITECTURE.md`
- `ROADMAP.md`