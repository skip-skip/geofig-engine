#!/usr/bin/env python3
"""Upload built distributions to TestPyPI or PyPI using tokens from .env.

Usage:
    python scripts/release_upload.py --target testpypi
    python scripts/release_upload.py --target pypi
    python scripts/release_upload.py --target testpypi --dry-run

The .env file is gitignored and never printed. Tokens are passed to twine only
through TWINE_USERNAME / TWINE_PASSWORD in the child process environment.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
DIST_DIR = ROOT / "dist"

REPOSITORIES = {
    "testpypi": ("https://test.pypi.org/legacy/", "TEST_PYPI_API_TOKEN"),
    "pypi": ("https://upload.pypi.org/legacy/", "PYPI_API_TOKEN"),
}


def load_env(path: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE .env files; comments, blank lines and export work."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "").isalnum():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def distributions() -> list[str]:
    files = sorted(DIST_DIR.glob("*.whl")) + sorted(DIST_DIR.glob("*.tar.gz"))
    return [path.name for path in files]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=sorted(REPOSITORIES), required=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate token presence and show the twine command without uploading",
    )
    args = parser.parse_args()

    url, token_key = REPOSITORIES[args.target]
    names = distributions()
    if not names:
        print(
            f"No distributions in {DIST_DIR.relative_to(ROOT)}; "
            "run 'python -m build --outdir dist' first.",
            file=sys.stderr,
        )
        return 2

    values = load_env(ENV_FILE)
    token = values.get(token_key, "").strip()
    if not token:
        print(
            f"Missing {token_key} in {ENV_FILE.relative_to(ROOT)}; "
            "copy .env.example to .env and add the token.",
            file=sys.stderr,
        )
        return 2

    child_env = dict(os.environ)
    child_env["TWINE_USERNAME"] = "__token__"
    child_env["TWINE_PASSWORD"] = token
    command = [
        sys.executable,
        "-m",
        "twine",
        "upload",
        "--repository-url",
        url,
        *[str(Path("dist") / name) for name in names],
    ]

    if args.dry_run:
        print(f"dry run: token {token_key} present; would upload: {', '.join(names)}")
        print("command:", " ".join(command))
        return 0

    checked = subprocess.run(
        [sys.executable, "-m", "twine", "check", *[str(Path("dist") / name) for name in names]],
        cwd=ROOT,
        check=False,
    )
    if checked.returncode != 0:
        print("twine check failed; upload aborted.", file=sys.stderr)
        return checked.returncode

    return subprocess.run(command, cwd=ROOT, env=child_env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
