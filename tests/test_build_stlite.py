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


def test_derive_requirements_excludes_streamlit_and_matplotlib():
    reqs = b.derive_requirements(REPO / "requirements.txt")
    assert "streamlit" not in reqs
    assert "matplotlib" not in reqs
    # scipy + plotly are NOT streamlit deps → must be explicitly present
    assert "scipy" in reqs
    assert "plotly" in reqs
    # version specifiers stripped to bare names
    assert all("=" not in r and ">" not in r and "<" not in r for r in reqs)
