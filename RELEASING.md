# Publishing releases

This project publishes to **TestPyPI first** and then to **PyPI** using the
same wheel and sdist. Credentials live in a local `.env` file that is
gitignored and excluded from source distributions.

## 1. Prepare credentials

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set the tokens you need:

- `TEST_PYPI_API_TOKEN` — create at https://test.pypi.org/manage/account/token/
- `PYPI_API_TOKEN` — create at https://pypi.org/manage/account/token/

TestPyPI and PyPI tokens are **different**; the upload script never uses one
index's token for the other. `.env` must never be committed or attached to a
release.

## 2. Build and validate artifacts

From the clean release tag:

```powershell
python -m build --outdir dist
python -m twine check dist/*
Get-FileHash dist\* | Select-Object Path, Hash
```

The wheel and sdist must match the tag's version and package contents before
uploading.

## 3. Upload to TestPyPI

```powershell
python scripts/release_upload.py --target testpypi
```

The script loads `.env`, sets `TWINE_USERNAME=__token__` and the token in the
twine child process only, runs `twine check`, and uploads `dist/*.whl` and
`dist/*.tar.gz` to `https://test.pypi.org/legacy/`. It never prints the token.
Use `--dry-run` to confirm token discovery without uploading:

```powershell
python scripts/release_upload.py --target testpypi --dry-run
```

Verify the TestPyPI artifact in a fresh environment. The extra index is needed
because TestPyPI does not mirror all runtime dependencies:

```powershell
py -3.11 -m venv .venv-test
.\.venv-test\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ --no-cache-dir geofig-engine==<version>
python -c "import pandas as pd; from geofig_engine import render_template; df=pd.DataFrame({'x':[1,2,3],'y':[2,4,3]}); assert len(render_template(df,'bivariate',mapping={'x':'x','y':'y'}))==1; print('smoke ok')"
```

TestPyPI rejects re-uploading an existing filename. If retesting the same
version, remove the old TestPyPI release or build a new patch version.

## 4. Upload to PyPI

Once the TestPyPI install and smoke test pass:

```powershell
python scripts/release_upload.py --target pypi
```

Verify with https://pypi.org/pypi/geofig-engine/<version>/json or:

```powershell
python -m pip install --no-cache-dir geofig-engine==<version>
```

## 5. Attach the same artifacts to GitHub

```powershell
git archive --format=zip --prefix=geofig-engine-v<version>/ geofig-engine-v<version> -o geofig-engine-v<version>-source.zip
# Write SHA256SUMS.txt for the wheel, sdist, and source archive.
gh release create geofig-engine-v<version> dist/*.whl dist/*.tar.gz geofig-engine-v<version>-source.zip SHA256SUMS.txt --title "geofig-engine v<version>" --notes-file <notes>
```

## Safety rules

- Keep `.env` local; only `.env.example` with empty placeholders is tracked.
- Do not commit tokens, keyring dumps, or generated `dist/` artifacts.
- Never bypass `twine check`; stop on credential or metadata errors.
- The published wheel and sdist must be built from the release commit.
