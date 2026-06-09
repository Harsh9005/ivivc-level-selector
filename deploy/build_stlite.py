"""Build a self-contained stlite (Pyodide/WASM) static bundle for GitHub Pages.

Collects the Streamlit app's Python files into an in-memory manifest and renders
a single dist/index.html that boots @stlite/browser and mount()s the multipage
app with the files embedded. Pure stdlib.
"""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

STLITE_VERSION = "0.85.1"
ENTRYPOINT = "app.py"

# Directories whose .py files make up the app (relative to repo root).
APP_DIRS = ("pages", "utils")
# Directories whose runtime data files (JSON only) are bundled into the app's
# virtual FS — e.g. content/references.json read by utils.citations at runtime.
DATA_DIRS = ("content",)
# Names/paths to never include.
EXCLUDE_PARTS = ("__pycache__", ".git", "tests", "deploy", "docs")


def collect_app_files(repo_root: Path) -> dict[str, str]:
    """Return {posix_relpath: text} for app.py + pages/**.py + utils/**.py.

    Also bundles runtime data (content/*.json, e.g. the verified reference
    corpus) keyed by its repo-relative posix path. Dev-only markdown artifacts
    such as content/claims_map.md are deliberately excluded.
    """
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

    # Bundle runtime JSON data (e.g. content/references.json). Only *.json —
    # *.md files are dev artifacts, not needed in the browser runtime.
    for d in DATA_DIRS:
        base = repo_root / d
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.json")):
            rel = path.relative_to(repo_root)
            if any(part in EXCLUDE_PARTS for part in rel.parts):
                continue
            manifest[rel.as_posix()] = path.read_text(encoding="utf-8")
    return manifest


# Provided by the stlite runtime or unused → never request via micropip.
_OMIT_PACKAGES = {"streamlit", "matplotlib"}
# Phase-0 tuning point (Chunk 2): if the in-browser load shows a micropip version
# conflict, add "numpy"/"pandas" here — stlite's Streamlit runtime pins them.


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
    ).replace("</", "<\\/")  # prevent </script> breakout when embedding in <script>
    return _HTML_TEMPLATE.format(version=STLITE_VERSION, payload=payload)


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
