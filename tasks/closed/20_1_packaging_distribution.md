# Packaging and install deliverables

**Status**: complete
**Phase**: 20
**Dependencies**: none

## Description

Prepare `geofig-engine` v0.5.0 for sharing with another machine/environment.
The source tree is release-clean, but the built distribution metadata is not:
setuptools is configured to package only the top-level module, runtime imports
need `numpy` and `openpyxl` beyond the declared dependencies, optional geo/network
capabilities are undocumented, and the bundled preset JSON / typing marker are
not explicitly included as package data.

## Files to modify

- `pyproject.toml` — discover all `geofig_engine*` subpackages; declare `numpy`
  and `openpyxl` as runtime dependencies; add `dev` / `geo` / `network` / `full`
  extras; declare preset JSON and `py.typed` as package data.
- `src/geofig_engine/py.typed` — add the PEP 561 marker referenced by packaging
  metadata.
- `constraints.txt` — pin the dependency versions validated in the v0.5.0
  environment for reproducible installs.
- `MANIFEST.in` — include install/versioning docs and example inputs in the
  sdist.
- `README.md` — replace the minimal install note with runtime/extras summary and
  link to `INSTALL.md`.
- `INSTALL.md` — new guide covering source, wheel, offline, geo/network,
  headless rendering, and verification.
- `tests/test_packaging.py` — regression tests for dependency declarations,
  package discovery, package data, and the typing marker.
- `CHANGELOG.md` — record the unreleased packaging/install work.
- `ROADMAP.md` — add the Phase 20 entry.

## Changes

- Correct wheel/sdist contents and dependency resolution for a clean machine.
- Separate optional geospatial/network capabilities from the core runtime.
- Provide reproducible constraints and end-user install instructions.
- Add tests that prevent the packaging metadata from silently regressing.

## Acceptance criteria

- [x] `pyproject.toml` discovers every `geofig_engine*` subpackage instead of
  only the top-level package.
- [x] Runtime dependencies include `pandas`, `matplotlib`, `numpy`, and
  `openpyxl`; optional extras cover dev, geo, network, and combined installs.
- [x] Built distributions include `data/geom_presets/water_isotope.json` and
  `py.typed`.
- [x] `constraints.txt` pins the dependency versions validated in the current
  environment.
- [x] `README.md` and `INSTALL.md` document source, wheel, offline, optional
  geo/network, headless, and verification steps.
- [x] `python -m build --outdir <temp>` produces a wheel containing all
  subpackages and the preset JSON.
- [x] The sdist contains `INSTALL.md`, `constraints.txt`, docs, and the pinned
  preset JSON.
- [x] A clean venv install from the built wheel imports `geofig_engine` and
  renders a smoke figure.
- [x] `PYTHONPATH=src pytest` stays green with no new skips caused by this work.

## Verification

- `PYTHONPATH=src pytest`: **1648 passed, 8 skipped, 5 warnings** (baseline 1643
  plus 5 new packaging tests; skips unchanged).
- `python -m build --no-isolation --outdir <temp>`: wheel and sdist built; wheel
  contains all `geofig_engine*` subpackages, `py.typed`, and
  `data/geom_presets/water_isotope.json`; sdist contains `INSTALL.md`,
  `constraints.txt`, `MANIFEST.in`, docs, examples, tasks, and tests.
- Fresh venv install from the wheel with `-c constraints.txt`: succeeded,
  `pip check` reported no broken requirements, and a `bivariate` smoke render
  returned one Matplotlib figure from the installed package.
