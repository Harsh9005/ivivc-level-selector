"""Tests for utils.citations — the pure citation/reference module.

The reference corpus lives at content/references.json (15 verified entries,
file order = regulatory (7) then papers (8)). Display numbers are 1-based by
file order and must be stable.
"""
import json
from pathlib import Path

import pytest

from utils import citations as c

REPO = Path(__file__).resolve().parents[1]
REFS_JSON = REPO / "content" / "references.json"

REQUIRED_FIELDS = ("key", "type", "title", "url", "authors", "verification")


def test_load_references_returns_15():
    data = c.load_references()
    assert isinstance(data, dict)
    assert "references" in data and "_meta" in data
    assert len(data["references"]) == 15


def test_load_references_default_path_matches_repo_file():
    data = c.load_references()
    on_disk = json.loads(REFS_JSON.read_text(encoding="utf-8"))
    assert data == on_disk


def test_numbered_references_assigns_unique_1_to_15():
    refs = c.numbered_references()
    nums = [r["n"] for r in refs]
    assert nums == list(range(1, 16))  # 1..15 in file order, no gaps/dupes
    assert len(set(nums)) == 15
    # first entry (file order) is the FDA IVIVC guidance → number 1
    assert refs[0]["key"] == "fda_ivivc_1997"
    assert refs[0]["n"] == 1


def test_key_to_number_is_stable_and_bijective():
    k2n = c.key_to_number()
    data = c.load_references()
    keys = [r["key"] for r in data["references"]]
    assert set(k2n.keys()) == set(keys)
    assert sorted(k2n.values()) == list(range(1, 16))
    # bijective: each number used exactly once
    assert len(set(k2n.values())) == 15
    # stable across calls
    assert c.key_to_number() == k2n
    # known anchors
    assert k2n["fda_ivivc_1997"] == 1
    assert k2n["usp_1088"] == 3
    assert k2n["wagner_nelson_1963"] == 8


def test_cite_single_key():
    assert c.cite("wagner_nelson_1963") == "[8]"
    assert c.cite("fda_ivivc_1997") == "[1]"


def test_cite_multiple_keys_sorted_comma_form():
    assert c.cite("fda_ivivc_1997", "usp_1088") == "[1, 3]"
    # order of arguments does not matter — numbers are sorted ascending
    assert c.cite("usp_1088", "fda_ivivc_1997") == "[1, 3]"
    assert c.cite("wagner_nelson_1963", "fda_ivivc_1997") == "[1, 8]"


def test_cite_unknown_key_raises_keyerror():
    with pytest.raises(KeyError):
        c.cite("bogus")
    with pytest.raises(KeyError):
        c.cite("fda_ivivc_1997", "definitely_not_a_key")


def test_every_reference_has_required_fields():
    data = c.load_references()
    for ref in data["references"]:
        for field in REQUIRED_FIELDS:
            assert field in ref, f"{ref.get('key', '?')} missing {field}"
        assert isinstance(ref["authors"], list) and ref["authors"]
        assert ref["type"] in ("regulatory", "paper")
        assert "verified" in ref["verification"]


def test_reference_entry_markdown_contains_url_and_check_for_verified():
    refs = c.numbered_references()
    by_key = {r["key"]: r for r in refs}

    wn = by_key["wagner_nelson_1963"]  # verified paper, has DOI
    md = c.reference_entry_markdown(wn)
    assert wn["url"] in md            # clickable link target present
    assert "✅" in md                  # verified marker
    assert "**[8]**" in md            # display number
    assert "1963" in md               # year
    assert "https://doi.org/" in md   # DOI link text for a paper with a doi


def test_reference_entry_markdown_regulatory_uses_official_document_link_text():
    refs = c.numbered_references()
    by_key = {r["key"]: r for r in refs}
    reg = by_key["fda_ivivc_1997"]  # regulatory, doi is null
    md = c.reference_entry_markdown(reg)
    assert reg["url"] in md
    assert "Official document" in md  # no DOI → "Official document" link text
    assert "✅" in md


def test_format_authors_truncates_over_six():
    many = [f"Author{i}, X." for i in range(1, 9)]  # 8 authors
    out = c.format_authors(many)
    assert "et al." in out
    # exactly first 6 names shown
    assert out.count(",") >= 6  # 6 names each "Surname, X." plus joins
    assert out.startswith("Author1, X.")
    assert "Author7" not in out and "Author8" not in out


def test_format_authors_no_truncation_at_or_below_six():
    six = [f"Author{i}, X." for i in range(1, 7)]
    out = c.format_authors(six)
    assert "et al." not in out
    assert "Author6, X." in out
