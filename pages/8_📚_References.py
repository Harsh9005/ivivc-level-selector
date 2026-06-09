"""
Page 8: References & Evidence

The verified citation corpus behind every scientific and regulatory claim in
this app. Display numbers (e.g. [8]) are the canonical, stable reference
identifiers used by inline citations throughout the other pages.

Every reference was independently cross-verified; no citation is reconstructed
from memory and no DOI/URL was fabricated.
"""

import streamlit as st

st.set_page_config(page_title="References — IVIVC", page_icon="📚", layout="wide")

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.citations import load_references, numbered_references, reference_entry_markdown

# ── Title & method ─────────────────────────────────────────────────────────────
st.title("📚 References & Evidence")

data = load_references()
meta = data.get("_meta", {})
method = meta.get("method", "")
verified_on = meta.get("verified_on", "")

st.markdown("""
This page lists every regulatory guidance, compendial chapter, and primary
research paper cited in this app. **Reference numbers (e.g. [8]) are the canonical
identifiers** — inline citations elsewhere point here by number.

Every reference was **independently cross-verified**: it was discovered, then
confirmed against original sources. **No citation is reconstructed from memory and
no DOI or URL was fabricated.** Where a source could only be partially confirmed
(e.g. paywalled full text), its confidence is marked accordingly below.
""")

if method:
    caption = f"**Verification method:** {method}"
    if verified_on:
        caption += f"  ·  Verified {verified_on}"
    st.caption(caption)

st.markdown("---")

# ── Filter ─────────────────────────────────────────────────────────────────────
FILTER_ALL = "All"
FILTER_REG = "Regulatory guidance"
FILTER_LIT = "Primary literature"

choice = st.radio(
    "Show",
    [FILTER_ALL, FILTER_REG, FILTER_LIT],
    horizontal=True,
    help="Filter the reference list by source type.",
)

refs = numbered_references()
regulatory = [r for r in refs if r.get("type") == "regulatory"]
papers = [r for r in refs if r.get("type") == "paper"]


def _render_reference(ref: dict) -> None:
    """Render one numbered reference with its verification badge, sources, and claims."""
    st.markdown(reference_entry_markdown(ref))

    verification = ref.get("verification", {})
    bits = []
    if verification.get("verified"):
        confidence = verification.get("confidence", "")
        bits.append(f"✅ Verified ({confidence})" if confidence else "✅ Verified")
    sources = verification.get("sources") or []
    if sources:
        bits.append("Sources: " + ", ".join(sources))
    claims = ref.get("claims") or []
    if claims:
        bits.append("Supports claims: " + ", ".join(claims))
    if bits:
        st.caption("  ·  ".join(bits))


def _render_group(header: str, group: list[dict]) -> None:
    if not group:
        return
    st.header(header)
    for ref in group:
        _render_reference(ref)
        st.markdown("")  # small breathing room between entries


# ── Render grouped references ──────────────────────────────────────────────────
if choice in (FILTER_ALL, FILTER_REG):
    _render_group("Regulatory guidance & compendia", regulatory)

if choice in (FILTER_ALL, FILTER_LIT):
    _render_group("Primary literature", papers)

st.markdown("---")
st.caption("**Disclaimer:** All data and demonstrations elsewhere in this app are "
           "synthetic/hypothetical, generated from pharmacokinetic and dissolution "
           "mathematical models for educational purposes only. The references on this "
           "page, however, are real, independently verified scientific and regulatory sources.")
