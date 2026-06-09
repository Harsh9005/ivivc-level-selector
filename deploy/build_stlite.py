"""Build a self-contained stlite (Pyodide/WASM) static bundle for GitHub Pages.

Collects the Streamlit app's Python files into an in-memory manifest and renders
a single dist/index.html that boots @stlite/browser and mount()s the multipage
app with the files embedded. Pure stdlib.
"""
from __future__ import annotations

import json
from pathlib import Path

STLITE_VERSION = "0.85.1"
ENTRYPOINT = "app.py"

# Directories whose .py files make up the app (relative to repo root).
APP_DIRS = ("pages", "utils")
# Names/paths to never include.
EXCLUDE_PARTS = ("__pycache__", ".git", "tests", "deploy", "docs")


def collect_app_files(repo_root: Path) -> dict[str, str]:
    """Return {posix_relpath: text} for app.py + pages/**.py + utils/**.py."""
    repo_root = Path(repo_root)
    manifest: dict[str, str] = {}

    entry = repo_root / ENTRYPOINT
    if entry.is_file():
        manifest[ENTRYPOINT] = entry.read_text(encoding="utf-8")

    for d in APP_DIRS:
        base = repo_root / d
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(repo_root)
            if any(part in EXCLUDE_PARTS for part in rel.parts):
                continue
            manifest[rel.as_posix()] = path.read_text(encoding="utf-8")
    return manifest


import re

# Provided by the stlite runtime or unused → never request via micropip.
_OMIT_PACKAGES = {"streamlit", "matplotlib"}


def derive_requirements(requirements_txt: Path) -> list[str]:
    """Bare package names from requirements.txt, minus runtime-provided/unused."""
    reqs: list[str] = []
    for line in Path(requirements_txt).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # split off version specifiers / extras / markers
        name = re.split(r"[<>=!~;\[ ]", line, maxsplit=1)[0].strip().lower()
        if not name or name in _OMIT_PACKAGES:
            continue
        reqs.append(name)
    return reqs
