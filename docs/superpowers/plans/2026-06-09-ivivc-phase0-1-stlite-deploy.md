# IVIVC v2 — Phase 0 + Phase 1: stlite Re-platform & Always-Live Deploy — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing IVIVC Streamlit app run entirely in the browser via stlite (Pyodide/WASM) and auto-deploy to GitHub Pages, so it is live 24/7 with zero maintenance and never sleeps.

**Architecture:** A stdlib-only Python build script (`deploy/build_stlite.py`) collects all app files (`app.py`, `pages/*`, `utils/*`) into an in-memory manifest and renders a single self-contained `dist/index.html` that boots `@stlite/browser@0.85.1` and `mount()`s the multipage app with the files embedded (no runtime fetch of `.py` files → emoji filenames safe). A GitHub Actions workflow runs the build and publishes `dist/` to GitHub Pages on every push to `main`. The Streamlit Python source is unchanged in Phase 0/1; only deployment is added.

**Tech Stack:** Streamlit (existing app), stlite `@stlite/browser@0.85.1` (Pyodide), Python 3.12 stdlib (build script), pytest (build-script tests), GitHub Actions + GitHub Pages, `python -m http.server` + browser MCP (local smoke test).

**Reference spec:** `docs/superpowers/specs/2026-06-09-ivivc-selector-v2-design.md`

**Verified stlite facts (2026-06-09, from @stlite/browser README):**
- JS module: `https://cdn.jsdelivr.net/npm/@stlite/browser@0.85.1/build/stlite.js` (ESM, exports `mount`)
- CSS: `https://cdn.jsdelivr.net/npm/@stlite/browser@0.85.1/build/stlite.css`
- API: `mount({ requirements, entrypoint, files, streamlitConfig }, document.getElementById("root"))`
- Multipage: pages listed in `files` as `"pages/1_⭐️_Page1.py": "<source>"`; entrypoint may be emoji-named. → **embedding files in the manifest avoids any on-disk non-ASCII filename issue.**
- `streamlitConfig` is a flat object with dot keys (e.g. `"theme.primaryColor": "#2196F3"`).
- stlite runs without COOP/COEP headers → compatible with GitHub Pages (which cannot set custom headers).

---

## Pre-flight (one-time, before Chunk 1)

- [ ] **Step P1: Confirm branch + clean tree**

Run: `cd "/Users/harsh/Desktop items/work/ivivc-level-selector" && git branch --show-current && git status --short`
Expected: on `feat/v2-stlite-cited-interactive`, only the new spec/plan docs tracked, no stray edits.

- [ ] **Step P2: Confirm tooling present**

Run: `python3 --version && python3 -m pytest --version`
Expected: **Python ≥3.11** (required — `streamlit_config()` uses stdlib `tomllib`, which is 3.11+; on 3.10 the build crashes with `ModuleNotFoundError: tomllib`) and pytest available. If pytest missing: `python3 -m pip install pytest`.

---

## Chunk 1: Build pipeline (`deploy/build_stlite.py`) — TDD

Builds the stlite bundle generator and its tests. This is the only new code in Phase 1; everything is pure stdlib + pytest.

**Files:**
- Create: `deploy/__init__.py` (empty, makes `deploy` importable by tests)
- Create: `deploy/build_stlite.py`
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_build_stlite.py`
- Create: `pytest.ini`

### Task 1.1: Test harness scaffolding

- [ ] **Step 1: Create empty package markers**

Create `deploy/__init__.py` with a single comment line:
```python
# deploy package — stlite static-bundle builder
```
Create `tests/__init__.py` empty (0 bytes is fine; add a comment):
```python
# tests package
```

- [ ] **Step 2: Create `pytest.ini`**

Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

- [ ] **Step 3: Commit scaffolding**

```bash
git add deploy/__init__.py tests/__init__.py pytest.ini
git commit -m "test: add pytest scaffolding for build pipeline"
```

### Task 1.2: `collect_app_files()` — gather the manifest

**Behavior:** Walk the repo root and return `dict[str, str]` mapping POSIX relative path → file text, for `app.py`, every `pages/**/*.py`, and every `utils/**/*.py`. Exclude `__pycache__`, `.pyc`, and anything under `deploy/`, `tests/`, `docs/`, `.git/`. Preserve emoji filenames exactly.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_build_stlite.py`:
```python
import json
from pathlib import Path

import pytest

from deploy import build_stlite as b

REPO = Path(__file__).resolve().parents[1]


def test_collect_includes_entrypoint_and_emoji_pages():
    files = b.collect_app_files(REPO)
    assert "app.py" in files
    # all five existing emoji-prefixed pages must be present, exact names
    expected_pages = [
        "pages/1_🏠_Home.py",
        "pages/2_🔍_Level_Selector.py",
        "pages/3_📈_Level_A_Demo.py",
        "pages/4_📊_Level_B_Demo.py",
        "pages/5_📉_Level_C_Demo.py",
    ]
    for p in expected_pages:
        assert p in files, f"missing {p}"
    # util modules present
    for u in ["utils/deconvolution.py", "utils/ivivc_calculations.py",
              "utils/dissolution_models.py", "utils/pk_models.py",
              "utils/synthetic_data.py", "utils/plotting.py"]:
        assert u in files, f"missing {u}"
    # file contents are real source, not empty
    assert "import streamlit" in files["app.py"]


def test_collect_excludes_pycache_and_pyc():
    files = b.collect_app_files(REPO)
    assert not any("__pycache__" in k for k in files)
    assert not any(k.endswith(".pyc") for k in files)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/harsh/Desktop items/work/ivivc-level-selector" && python3 -m pytest tests/test_build_stlite.py -q`
Expected: FAIL — `ModuleNotFoundError`/`AttributeError` (no `build_stlite` / no `collect_app_files`).

- [ ] **Step 3: Write minimal implementation**

Create `deploy/build_stlite.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_build_stlite.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add deploy/build_stlite.py tests/test_build_stlite.py
git commit -m "feat(deploy): collect app files into stlite manifest"
```

### Task 1.3: `derive_requirements()` — Pyodide package list

**Behavior:** Read `requirements.txt`, return a list of **bare package names** (version specifiers stripped) **excluding** `streamlit` (provided by stlite runtime) and `matplotlib` (unused). Order preserved.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_build_stlite.py`:
```python
def test_derive_requirements_excludes_streamlit_and_matplotlib():
    reqs = b.derive_requirements(REPO / "requirements.txt")
    assert "streamlit" not in reqs
    assert "matplotlib" not in reqs
    # scipy + plotly are NOT streamlit deps → must be explicitly present
    assert "scipy" in reqs
    assert "plotly" in reqs
    # version specifiers stripped to bare names
    assert all("=" not in r and ">" not in r and "<" not in r for r in reqs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_build_stlite.py::test_derive_requirements_excludes_streamlit_and_matplotlib -q`
Expected: FAIL (`AttributeError: derive_requirements`).

- [ ] **Step 3: Write minimal implementation**

Add to `deploy/build_stlite.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_build_stlite.py -q`
Expected: PASS (3 passed).

> **Phase-0 tuning note:** if Chunk 2's in-browser load shows a micropip version conflict on `numpy`/`pandas` (streamlit pins them), trim those from the returned list so only `scipy` + `plotly` are requested. Leave a code comment marking this as the adjustment point.

- [ ] **Step 5: Commit**

```bash
git add deploy/build_stlite.py tests/test_build_stlite.py
git commit -m "feat(deploy): derive Pyodide requirements (drop streamlit/matplotlib)"
```

### Task 1.4: `streamlit_config()` — carry the existing theme

**Behavior:** Return a flat dict of stlite `streamlitConfig` keys from `.streamlit/config.toml` theme (primaryColor, backgroundColor, secondaryBackgroundColor, textColor, font) plus `client.toolbarMode: "viewer"`. Use stdlib `tomllib` (3.11+); if `.streamlit/config.toml` missing, return just the toolbar default.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_build_stlite.py`:
```python
def test_streamlit_config_maps_theme():
    cfg = b.streamlit_config(REPO / ".streamlit" / "config.toml")
    assert cfg.get("client.toolbarMode") == "viewer"
    assert cfg.get("theme.primaryColor") == "#2196F3"
    assert cfg.get("theme.base", "light") in ("light", "dark")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_build_stlite.py::test_streamlit_config_maps_theme -q`
Expected: FAIL (`AttributeError: streamlit_config`).

- [ ] **Step 3: Write minimal implementation**

Add to `deploy/build_stlite.py` (add `import tomllib` at top):
```python
def streamlit_config(config_toml: Path) -> dict[str, str]:
    """Flat stlite streamlitConfig dict, carrying the existing [theme]."""
    cfg: dict[str, str] = {"client.toolbarMode": "viewer"}
    p = Path(config_toml)
    if not p.is_file():
        return cfg
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    theme = data.get("theme", {})
    cfg["theme.base"] = "light"
    for key in ("primaryColor", "backgroundColor",
                "secondaryBackgroundColor", "textColor", "font"):
        if key in theme:
            cfg[f"theme.{key}"] = theme[key]
    return cfg
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_build_stlite.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add deploy/build_stlite.py tests/test_build_stlite.py
git commit -m "feat(deploy): carry existing Streamlit theme into stlite config"
```

### Task 1.5: `render_html()` — the index.html template

**Behavior:** Given manifest, requirements, entrypoint, config → return a complete HTML string that:
- links the stlite CSS,
- has a `<div id="root">` and a branded loading overlay,
- imports `mount` from the pinned CDN module and calls `mount({requirements, entrypoint, files, streamlitConfig}, root)`,
- removes the loading overlay once Streamlit renders (MutationObserver on `#root`),
- embeds `files`, `requirements`, `streamlitConfig` via `json.dumps` (safe escaping of Python source + emoji).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_build_stlite.py`:
```python
def test_render_html_contains_mount_and_embedded_files():
    manifest = {"app.py": "import streamlit as st\nst.write('hi')\n",
                "pages/1_🏠_Home.py": "import streamlit as st\n"}
    html = b.render_html(manifest, ["scipy", "plotly"], "app.py",
                         {"client.toolbarMode": "viewer"})
    assert "@stlite/browser@0.85.1/build/stlite.js" in html
    assert "@stlite/browser@0.85.1/build/stlite.css" in html
    assert "mount(" in html
    assert '"entrypoint"' in html or "entrypoint" in html
    assert '<div id="root">' in html
    # emoji page key survives embedding (as JSON-escaped unicode or literal)
    assert ("1_🏠_Home.py" in html) or ("1_\\ud83c\\udfe0_Home.py" in html)
    # loading overlay present
    assert "stlite-loading" in html


def test_render_html_is_valid_standalone():
    manifest = {"app.py": "x = 1\n"}
    html = b.render_html(manifest, [], "app.py", {})
    assert html.strip().startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_build_stlite.py -q`
Expected: FAIL (`AttributeError: render_html`).

- [ ] **Step 3: Write minimal implementation**

Add to `deploy/build_stlite.py`:
```python
_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>IVIVC Level Selector</title>
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/@stlite/browser@{version}/build/stlite.css" />
  <style>
    #stlite-loading {{
      position: fixed; inset: 0; display: flex; flex-direction: column;
      align-items: center; justify-content: center; gap: 1rem;
      font-family: sans-serif; color: #333; background: #ffffff; z-index: 9999;
      transition: opacity .4s ease;
    }}
    #stlite-loading .spinner {{
      width: 44px; height: 44px; border: 4px solid #e0e0e0;
      border-top-color: #2196F3; border-radius: 50%;
      animation: spin 1s linear infinite;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    #stlite-loading small {{ color: #888; max-width: 22rem; text-align: center; }}
  </style>
</head>
<body>
  <div id="stlite-loading">
    <div class="spinner"></div>
    <div>💊 Loading IVIVC Level Selector…</div>
    <small>First load downloads the Python runtime in your browser (~20–30s).
    It then runs entirely offline — no server, never sleeps.</small>
  </div>
  <div id="root"></div>
  <script type="module">
    import {{ mount }} from
      "https://cdn.jsdelivr.net/npm/@stlite/browser@{version}/build/stlite.js";

    const APP = {payload};

    mount(
      {{
        requirements: APP.requirements,
        entrypoint: APP.entrypoint,
        files: APP.files,
        streamlitConfig: APP.streamlitConfig,
      }},
      document.getElementById("root"),
    );

    // Hide the loading overlay once Streamlit paints into #root.
    const overlay = document.getElementById("stlite-loading");
    const root = document.getElementById("root");
    const obs = new MutationObserver(() => {{
      if (root.querySelector("iframe, .stApp, [data-testid='stAppViewContainer']")) {{
        overlay.style.opacity = "0";
        setTimeout(() => overlay.remove(), 500);
        obs.disconnect();
      }}
    }});
    obs.observe(root, {{ childList: true, subtree: true }});
    // Safety net: never trap the user behind the overlay.
    setTimeout(() => {{ overlay.style.opacity = "0";
      setTimeout(() => overlay.remove(), 500); }}, 90000);
  </script>
</body>
</html>
"""


def render_html(files: dict[str, str], requirements: list[str],
                entrypoint: str, config: dict[str, str]) -> str:
    payload = json.dumps(
        {"files": files, "requirements": requirements,
         "entrypoint": entrypoint, "streamlitConfig": config},
        ensure_ascii=True,
    )
    return _HTML_TEMPLATE.format(version=STLITE_VERSION, payload=payload)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_build_stlite.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add deploy/build_stlite.py tests/test_build_stlite.py
git commit -m "feat(deploy): render self-contained stlite index.html"
```

### Task 1.6: `main()` — write `dist/index.html`

**Behavior:** Orchestrate collect → derive → config → render, write `dist/index.html`, print a short summary (file count, byte size). Add `if __name__ == "__main__": main()`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_build_stlite.py`:
```python
def test_main_writes_dist_index(tmp_path, monkeypatch):
    # build into a temp dist by pointing main at the real repo but temp out
    out = tmp_path / "dist"
    b.build(REPO, out)
    index = out / "index.html"
    assert index.is_file()
    text = index.read_text(encoding="utf-8")
    assert text.startswith("<!DOCTYPE html>")
    assert "mount(" in text
    assert len(text) > 5000  # embeds real app source → not trivial
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_build_stlite.py::test_main_writes_dist_index -q`
Expected: FAIL (`AttributeError: build`).

- [ ] **Step 3: Write minimal implementation**

Add to `deploy/build_stlite.py`:
```python
def build(repo_root: Path, out_dir: Path) -> Path:
    repo_root, out_dir = Path(repo_root), Path(out_dir)
    files = collect_app_files(repo_root)
    reqs = derive_requirements(repo_root / "requirements.txt")
    cfg = streamlit_config(repo_root / ".streamlit" / "config.toml")
    html = render_html(files, reqs, ENTRYPOINT, cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    index = out_dir / "index.html"
    index.write_text(html, encoding="utf-8")
    print(f"[build_stlite] {len(files)} files, "
          f"{len(html):,} bytes -> {index}")
    return index


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    build(repo_root, repo_root / "dist")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run full test suite**

Run: `python3 -m pytest -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Generate the real bundle + sanity-check**

Run: `python3 deploy/build_stlite.py && ls -la dist/ && head -c 200 dist/index.html`
Expected: prints `[build_stlite] N files, … bytes -> …/dist/index.html`; `dist/index.html` exists; starts with `<!DOCTYPE html>`.

- [ ] **Step 6: verify build output is gitignored + commit**

Confirm `dist/` is already in `.gitignore` (it is — repo already ignores `dist/`,
`build/`, `__pycache__/`, `*.pyc`). No `.gitignore` edit needed.
Run: `grep -q '^dist/' .gitignore && echo "dist/ already ignored"`
```bash
git add deploy/build_stlite.py tests/test_build_stlite.py
git commit -m "feat(deploy): build dist/index.html (stlite bundle entrypoint)"
```

---

## Chunk 2: Local in-browser validation = Phase 0 gates

No new code unless a gate fails. Serve the built bundle locally and validate every Phase 0 gate in a real browser **before** wiring CI. This is where "does THIS app actually run in stlite" is proven. Use the browser MCP tools (chrome-devtools or Claude_Preview).

**Gate decisions (from spec §7):** plotly+scipy compute = hard gate (fail → escalate, stlite is wrong tool); multipage nav; emoji pages; `file_uploader`; `query_params`; first-load time. Each gate: PASS → continue; FAIL → apply the spec's named fallback in a follow-up task, re-build, re-test.

### Task 2.1: Serve the bundle locally

- [ ] **Step 1: Start a static server (background)**

Run (background): `cd "/Users/harsh/Desktop items/work/ivivc-level-selector" && python3 -m http.server 8000 -d dist`
Note: stlite needs `http://`, not `file://`. GitHub Pages-equivalent; no COOP/COEP needed.

- [ ] **Step 2: Open in a browser via MCP**

Navigate the browser MCP to `http://localhost:8000`. Wait for the loading overlay to disappear (first load downloads Pyodide + packages; allow up to ~60s).

### Task 2.2: Validate gates + capture evidence

- [ ] **Step 1: HARD GATE — app renders, plotly draws, scipy computes**

Navigate to the Level A demo page. Confirm: page renders, a Plotly chart is visible, no uncaught errors in the browser console (check console logs via MCP). Wagner–Nelson/Level-A uses numpy+scipy; a rendered correlation plot proves scipy ran.
Expected: PASS. **If FAIL (packages won't load / charts blank): STOP and escalate — record the console error; the stlite approach needs rethinking (see spec §9).**

- [ ] **Step 2: GATE — multipage nav**

Click through all pages in the stlite sidebar (Home, Level Selector, Level A/B/C). Confirm each loads.
Expected: PASS. Fallback if FAIL: single-page `st.navigation`/selectbox switcher (new task; spec §7).

- [ ] **Step 3: GATE — emoji filenames served**

Confirm the emoji-prefixed pages appear with correct labels and load without 404/parse errors in console.
Expected: PASS (files are embedded, not fetched). Fallback if FAIL: ASCII filenames + `st.Page` titles.

- [ ] **Step 4: GATE — `st.file_uploader` works in-browser**

In the browser console (via MCP `evaluate_script`), or by temporarily adding a probe page, confirm a `st.file_uploader` widget renders and accepts a small CSV without error. (Minimal probe: see Step 6.)
Expected: PASS. Fallback if FAIL: paste-CSV `st.text_area` path (drives the same `data_io` parser in Phase 3).

- [ ] **Step 5: GATE — `st.query_params` round-trips**

Append `?probe=42` to the URL, reload, and confirm a probe widget can read it back (see probe page). 
Expected: PASS. Fallback if FAIL: copyable scenario-code string instead of URL state (Phase 3).

- [ ] **Step 6: (Helper) temporary probe page for gates 4–5**

If needed, create `pages/9_🧷_Probe.py` (TEMPORARY — deleted at end of chunk):
```python
import streamlit as st
st.title("stlite probe")
st.write("query_params:", dict(st.query_params))
up = st.file_uploader("upload test CSV", type="csv")
if up is not None:
    st.success(f"received {up.name} ({len(up.getvalue())} bytes)")
```
Rebuild (`python3 deploy/build_stlite.py`), reload `http://localhost:8000`, exercise gates 4–5, then **delete the probe page** and rebuild before committing.

- [ ] **Step 7: GATE — first-load time + capture screenshot**

Hard-reload with an empty cache; record seconds until the app is interactive. Capture a screenshot of a working page (e.g., Level A with its Plotly chart) via the browser MCP for the user.
Expected: load within a tolerable window (target <45s cold). If far worse, apply spec first-load mitigations (trim numpy/pandas from requirements per Task 1.3 note; rebuild).

- [ ] **Step 8: Record gate results**

Create `docs/superpowers/plans/phase0-gate-results.md` with a short PASS/FAIL + notes table for the 6 gates and the measured load time. Commit:
```bash
git add docs/superpowers/plans/phase0-gate-results.md
git commit -m "docs: record Phase 0 in-browser gate results"
```

- [ ] **Step 9: Stop the local server**

Terminate the background `http.server`.

> **Gate exit condition:** proceed to Chunk 3 only when every gate is PASS or has its fallback recorded as a follow-up task. The hard gate (Step 1) must be PASS.

---

## Chunk 3: Auto-deploy to GitHub Pages + go live

Wire CI so every push to `main` rebuilds and publishes — the "stays live with zero babysitting" payoff. **The push/merge and Pages-enable steps touch the user's GitHub repo and require the user's explicit go-ahead before running.**

**Files:**
- Create: `.github/workflows/deploy.yml`
- Modify: `README.md` (new URL + architecture + how to build locally)

### Task 3.1: GitHub Actions workflow

- [ ] **Step 1: Create the workflow**

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy IVIVC app to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Build stlite bundle
        run: python deploy/build_stlite.py
      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Validate the workflow file**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/deploy.yml')); print('yaml ok')"`
(If PyYAML missing, visually confirm indentation; CI will validate on push.)
Expected: `yaml ok`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: build stlite bundle and deploy to GitHub Pages on push to main"
```

### Task 3.2: Update README

- [ ] **Step 1: Update the Live Demo + add deploy/architecture notes**

In `README.md`: change the Live Demo URL to `https://harsh9005.github.io/ivivc-level-selector`, note it runs fully in-browser via stlite (always-on, never sleeps), and add a short "Build the static bundle locally" section:
```markdown
## Live Demo

🚀 **[Launch the App](https://harsh9005.github.io/ivivc-level-selector)** — runs
entirely in your browser via [stlite](https://github.com/whitphx/stlite)
(Pyodide/WebAssembly). Always-on, no server, never sleeps.

## Build & preview the static bundle locally

```bash
python3 deploy/build_stlite.py        # writes dist/index.html
python3 -m http.server 8000 -d dist   # open http://localhost:8000
```
```
(Keep the existing Streamlit `streamlit run app.py` instructions for dev.)

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: point README at GitHub Pages stlite deploy"
```

### Task 3.3: Go live (REQUIRES USER GO-AHEAD — do not run unprompted)

- [ ] **Step 1: Merge the branch to `main`**

Confirm with the user, then:
```bash
git checkout main && git merge --no-ff feat/v2-stlite-cited-interactive
git push origin main
```

- [ ] **Step 2: Enable GitHub Pages (one-time, manual in GitHub UI)**

Repo → Settings → Pages → Build and deployment → **Source: GitHub Actions**. (No branch selection needed with the Actions deploy flow.)

- [ ] **Step 3: Verify the deploy**

Watch the Actions run finish (`gh run watch` or the Actions tab). Then load `https://harsh9005.github.io/ivivc-level-selector` in a browser; confirm the app boots and a Plotly chart renders. Capture a screenshot for the user.

- [ ] **Step 4: Confirm "stays live"**

Note for the user: GitHub Pages serves static files from a CDN with no idle/sleep state — no wake step is ever required. Re-deploys happen automatically on push to `main`.

---

## Done-When (Phase 0 + Phase 1 acceptance)
- `python3 -m pytest -q` passes (build-pipeline tests green).
- `python3 deploy/build_stlite.py` produces a `dist/index.html` that, served over HTTP, boots the full multipage app in-browser with working Plotly charts and no console errors (Chunk 2 evidence captured).
- All Phase 0 gates PASS or have a recorded fallback; hard gate PASS.
- Pushing to `main` triggers the Actions workflow and publishes to `https://harsh9005.github.io/ivivc-level-selector`, which is reachable with no manual wake step.
- README reflects the new URL + local build instructions.

## Out of scope (later phases — separate plans)
- Phase 2: cited evidence layer (`content/references.json`, References page, inline citations) — research via Consensus + scite + refchecker.
- Phase 3: interactivity (upload-your-own-data, save/share, guided mode/quizzes, richer widgets) + science-core unit tests.
