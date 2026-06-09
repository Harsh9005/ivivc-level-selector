"""Pure citation/reference helpers for the IVIVC app.

Reads the verified reference corpus from ``content/references.json`` and exposes
stable display numbers, inline citation markers, and markdown formatting. No
network access, no third-party deps — stdlib + json only — so it imports cleanly
both locally and inside stlite's Pyodide virtual filesystem (where ``utils/`` and
``content/`` sit at the same repo-relative paths the build manifest embeds).

Display numbering is 1-based by FILE ORDER (regulatory entries first, then
papers) and is the canonical, stable reference identifier used throughout the
app — e.g. Wagner–Nelson (1963) is reference [8].
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

# Default corpus location: repo-relative, resolved from this file. Works locally
# AND in stlite's virtual FS, where utils/citations.py and content/references.json
# are embedded at "utils/citations.py" / "content/references.json".
_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "content" / "references.json"


def _resolve(path: str | Path | None) -> Path:
    return Path(path) if path is not None else _DEFAULT_PATH


@lru_cache(maxsize=None)
def _load_cached(path_str: str) -> dict:
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def load_references(path: str | Path | None = None) -> dict:
    """Load and return the parsed references.json corpus as a dict.

    Result is cached per resolved path; the returned dict is the shared parsed
    structure (treat as read-only).
    """
    return _load_cached(str(_resolve(path)))


def numbered_references(path: str | Path | None = None) -> list[dict]:
    """References list in file order, each augmented with a 1-based ``"n"``.

    Returns fresh shallow copies so callers may add fields (e.g. display
    formatting) without mutating the cached corpus.
    """
    refs = load_references(path)["references"]
    out: list[dict] = []
    for i, ref in enumerate(refs, start=1):
        item = dict(ref)
        item["n"] = i
        out.append(item)
    return out


def key_to_number(path: str | Path | None = None) -> dict[str, int]:
    """Map each reference ``key`` to its 1-based display number (stable)."""
    return {ref["key"]: ref["n"] for ref in numbered_references(path)}


def cite(*keys: str, path: str | Path | None = None) -> str:
    """Inline citation marker for one or more reference keys.

    ``cite("wagner_nelson_1963")`` -> ``"[8]"``;
    ``cite("fda_ivivc_1997", "usp_1088")`` -> ``"[1, 3]"`` (numbers sorted
    ascending, comma-separated, in square brackets).

    Raises ``KeyError(key)`` for any unknown key — a typo'd citation must fail
    loud rather than silently render nothing.
    """
    k2n = key_to_number(path)
    numbers = []
    for key in keys:
        if key not in k2n:
            raise KeyError(key)
        numbers.append(k2n[key])
    return "[" + ", ".join(str(n) for n in sorted(numbers)) + "]"


def format_authors(authors: list[str], max_n: int = 6) -> str:
    """Join authors with ", "; if more than ``max_n``, show first ``max_n`` + " et al."."""
    authors = list(authors)
    if len(authors) > max_n:
        return ", ".join(authors[:max_n]) + " et al."
    return ", ".join(authors)


def reference_entry_markdown(ref: dict) -> str:
    """Format one (already-numbered) reference as a markdown line.

    Layout: ``**[n]** Authors (Year). *Title*. Venue. [link text](url) ✅`` where
    the ✅ appears only when ``verification.verified`` is true, and the link text
    is ``https://doi.org/...`` when a DOI is present, else "Official document".
    """
    n = ref.get("n", "")
    authors = format_authors(ref.get("authors", []))
    year = ref.get("year", "")
    title = ref.get("title", "")
    venue = ref.get("venue", "")
    url = ref.get("url", "")
    doi = ref.get("doi")
    verified = bool(ref.get("verification", {}).get("verified"))

    link_text = f"https://doi.org/{doi}" if doi else "Official document"
    check = " ✅" if verified else ""

    parts = [f"**[{n}]**"]
    if authors:
        parts.append(authors)
    if year != "":
        parts[-1] = f"{parts[-1]} ({year})." if len(parts) > 1 else f"({year})."
    else:
        if len(parts) > 1:
            parts[-1] = f"{parts[-1]}."
    if title:
        parts.append(f"*{title}*.")
    if venue:
        parts.append(f"{venue}.")
    parts.append(f"[{link_text}]({url}){check}")
    return " ".join(parts)
