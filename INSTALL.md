# Installing geofig-engine

`geofig-engine` requires Python 3.11 or newer. There are no upstream imports of
`geodata` or `geochemmodel`; a raw `pandas.DataFrame` is accepted directly.

## Core dependencies

Installed automatically:

- `pandas`
- `matplotlib`
- `numpy`
- `openpyxl` (Excel input through the legacy `Dataset.load_dataset` path)

## Optional extras

| Extra | Use it for |
| --- | --- |
| `dev` | Running the test suite and building distributions |
| `geo` | Projected `CoordGeo` CRSs (`pyproj`) and shapefile boundaries (`pyshp`) |
| `network` | `site_map` basemap tiles, DEM contours, and USGS streams (`requests`, `pillow`, `xyzservices`) |
| `full` | Everything above |

The `site_map` template enables basemap, contours, and streams by default, so a
network-connected environment should install `network` (and usually `geo`).
They degrade with warnings when unavailable. To render a geographic figure fully
offline:

```python
settings = {
    "basemap": None,
    "contours": None,
    "streams": None,
}
```

## Install from a source checkout

Recommended when the receiving machine will develop or run tests.

```powershell
git clone https://github.com/skip-skip/geofig-engine.git
cd geofig-engine
git checkout geofig-engine-v0.5.0

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -c constraints.txt -e ".[full]"
```

On macOS/Linux, activate the environment with:

```sh
source .venv/bin/activate
```

For runtime-only use, omit the extra:

```powershell
python -m pip install -e .
```

The constraints file pins the versions validated with v0.5.0. Omit `-c
constraints.txt` if the receiving platform needs different wheels.

## Install from a wheel

For a non-development consumer. The wheel contains the package only; use a
source checkout or sdist to run `tests/`.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install geofig_engine-0.5.0-py3-none-any.whl
```

Add optional capabilities explicitly:

```powershell
python -m pip install pyproj pyshp requests pillow xyzservices
```

## Offline install

On a machine with internet access, download the wheel and all dependencies:

```powershell
python -m pip download -r constraints.txt -d wheels
python -m pip download geofig_engine==0.5.0 -d wheels
```

Transfer `wheels/` to the target machine, then:

```powershell
python -m pip install --no-index --find-links wheels geofig-engine==0.5.0
```

Include the optional packages in the download set if `geo` or `network`
features are needed.

## Headless rendering

Set Matplotlib's non-interactive backend when there is no display:

```powershell
$env:MPLBACKEND = "Agg"
```

```sh
export MPLBACKEND=Agg
```

## Verify the install

From a source checkout with the `dev` extra:

```powershell
PYTHONPATH=src pytest
```

Expected baseline for v0.5.0: **1643 passed, 8 skipped**. The skips are
optional-dependency gates, not warning-policy skips.

Smoke test in any environment:

```powershell
python -c "import pandas as pd; from geofig_engine import render_template; df=pd.DataFrame({'x':[1,2,3],'y':[2,4,3]}); figures=render_template(df,'bivariate',mapping={'x':'x','y':'y'}); assert len(figures)==1; print('smoke ok')"
```

Check that imports resolve to the installed package:

```powershell
python -c "import geofig_engine as g; print(g.__file__)"
```

## Preparing a shareable release bundle

From a clean checkout at the release tag:

```powershell
git archive --format=zip --prefix=geofig-engine-v0.5.0/ geofig-engine-v0.5.0 -o geofig-engine-v0.5.0-source.zip
python -m build --outdir dist
Get-FileHash dist\* | Select-Object Path, Hash
```

Publish the source archive, `dist/geofig_engine-0.5.0-py3-none-any.whl`,
`dist/geofig_engine-0.5.0.tar.gz`, and the checksums together.
