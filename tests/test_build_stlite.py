import json
from pathlib import Path

import pytest

from deploy import build_stlite as b

REPO = Path(__file__).resolve().parents[1]


def test_collect_includes_entrypoint_and_emoji_pages():
    files = b.collect_app_files(REPO)
    assert "app.py" in files
    # all existing emoji-prefixed pages must be present, exact names
    expected_pages = [
        "pages/1_🏠_Home.py",
        "pages/2_🔍_Level_Selector.py",
        "pages/3_📈_Level_A_Demo.py",
        "pages/4_📊_Level_B_Demo.py",
        "pages/5_📉_Level_C_Demo.py",
        "pages/8_📚_References.py",
    ]
    for p in expected_pages:
        assert p in files, f"missing {p}"
    # util modules present (incl. the new citations module)
    for u in ["utils/deconvolution.py", "utils/ivivc_calculations.py",
              "utils/dissolution_models.py", "utils/pk_models.py",
              "utils/synthetic_data.py", "utils/plotting.py",
              "utils/citations.py"]:
        assert u in files, f"missing {u}"
    # file contents are real source, not empty
    assert "import streamlit" in files["app.py"]


def test_collect_bundles_reference_corpus_json():
    files = b.collect_app_files(REPO)
    # the verified citation corpus must be embedded at its repo-relative posix path
    assert "content/references.json" in files
    parsed = json.loads(files["content/references.json"])
    assert isinstance(parsed.get("references"), list)
    assert parsed["references"]  # non-empty


def test_collect_excludes_content_markdown():
    files = b.collect_app_files(REPO)
    # dev-only artifacts (claims_map.md) are NOT shipped to the runtime
    assert "content/claims_map.md" not in files
    assert not any(k.endswith(".md") for k in files)


def test_collect_excludes_pycache_and_pyc():
    files = b.collect_app_files(REPO)
    assert not any("__pycache__" in k for k in files)
    assert not any(k.endswith(".pyc") for k in files)


def test_derive_requirements_excludes_streamlit_and_matplotlib():
    reqs = b.derive_requirements(REPO / "requirements.txt")
    assert "streamlit" not in reqs
    assert "matplotlib" not in reqs
    # scipy + plotly are NOT streamlit deps → must be explicitly present
    assert "scipy" in reqs
    assert "plotly" in reqs
    # version specifiers stripped to bare names
    assert all("=" not in r and ">" not in r and "<" not in r for r in reqs)


def test_streamlit_config_maps_theme():
    cfg = b.streamlit_config(REPO / ".streamlit" / "config.toml")
    assert cfg.get("client.toolbarMode") == "viewer"
    assert cfg.get("theme.primaryColor") == "#2196F3"
    assert cfg.get("theme.base", "light") in ("light", "dark")


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


def test_render_html_escapes_script_breakout():
    manifest = {"app.py": "import streamlit as st\nst.markdown('</script><b>x</b>')\n"}
    html = b.render_html(manifest, [], "app.py", {})
    # the raw closing-script sequence must NOT appear inside the embedded payload
    assert "</script><b>" not in html
    assert "<\\/script>" in html  # escaped form is present
    # and the real module script tag still closes exactly once at the end
    assert html.count("</script>") == 1


def test_render_html_is_valid_standalone():
    manifest = {"app.py": "x = 1\n"}
    html = b.render_html(manifest, [], "app.py", {})
    assert html.strip().startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")


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
