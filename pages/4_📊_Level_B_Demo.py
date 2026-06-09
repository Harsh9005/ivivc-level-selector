"""
Page 4: Level B IVIVC Tutorial & Demo

Statistical moment comparison (MDT vs MRT) with pathological example.

All data is synthetic/hypothetical for educational purposes only.
"""

import streamlit as st
import numpy as np

st.set_page_config(page_title="Level B Demo — IVIVC", page_icon="📊", layout="wide")

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.synthetic_data import generate_level_b_data
from utils.plotting import (
    COLORS, plot_mdt_vs_mrt, plot_pathological_example,
    plot_dissolution_profiles, plot_pk_profiles, _base_layout,
)
from utils.citations import references_for, reference_entry_markdown
from utils.share import decode_scenario, encode_scenario, SCHEMAS, LEVEL_B_PRESETS

# ── Seed slider state from the URL (once) ─────────────────────────────────────
_SCHEMA = SCHEMAS["level_b"]
if "_lb_seeded" not in st.session_state:
    seeded = decode_scenario(dict(st.query_params), _SCHEMA)
    for k, v in seeded.items():
        st.session_state.setdefault(k, v)
    st.session_state["_lb_seeded"] = True

# ── Title ────────────────────────────────────────────────────────────────────
st.title("📊 Level B IVIVC: Statistical Moment Comparison")

st.markdown("""
**Level B** correlates **summary statistical moments** of the dissolution
and plasma profiles — specifically, **Mean Dissolution Time (MDT)** versus
**Mean Residence Time (MRT)**.

Unlike Level A, Level B does **not** map the entire time course.
It reduces each profile to a single number, which means:
- It **cannot predict** the shape of the plasma profile
- It has **limited regulatory value** for biowaivers [1]
- It is mainly useful as **supporting evidence** alongside other IVIVC levels
""")

st.markdown("---")

# ── Sidebar Controls ─────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Level B Controls")

st.sidebar.subheader("ER Formulations")
k_fast = st.sidebar.slider(
    "F1 (Fast) dissolution k (h⁻¹)",
    min_value=0.10, max_value=0.60,
    step=0.02,
    key="b_kf",
    help="First-order dissolution rate constant"
)
k_medium = st.sidebar.slider(
    "F2 (Medium) dissolution k (h⁻¹)",
    min_value=0.05, max_value=0.40,
    step=0.02,
    key="b_km",
)
k_slow = st.sidebar.slider(
    "F3 (Slow) dissolution k (h⁻¹)",
    min_value=0.02, max_value=0.25,
    step=0.01,
    key="b_ks",
)

st.sidebar.markdown("---")
st.sidebar.subheader("Pathological Example")
p1_burst = st.sidebar.slider(
    "P1 burst fraction (%)",
    min_value=10.0, max_value=70.0,
    step=5.0,
    key="p1_burst",
    help="Fraction of dose released in the burst phase of biphasic P1"
)
p1_burst_k = st.sidebar.slider(
    "P1 burst rate (h⁻¹)",
    min_value=0.5, max_value=5.0,
    step=0.25,
    key="p1_bk",
    help="Rate constant for the burst phase"
)
p2_k = st.sidebar.slider(
    "P2 steady dissolution k (h⁻¹)",
    min_value=0.05, max_value=0.40,
    step=0.01,
    key="p2_k",
    help="First-order rate for the steady-release P2"
)

st.sidebar.markdown("---")
st.sidebar.info("💡 Adjust the sliders to explore how dissolution rate affects MDT/MRT, and how different profile shapes can yield similar MDT values.")

# ── Share / Save scenario ─────────────────────────────────────────────────────
with st.sidebar.expander("🔗 Share / Save this scenario"):
    _preset_choice = st.selectbox(
        "Load preset scenario", ["—"] + list(LEVEL_B_PRESETS.keys()),
        key="_lb_preset",
    )
    if _preset_choice != "—":
        for _k, _v in LEVEL_B_PRESETS[_preset_choice].items():
            st.session_state[_k] = _v
        st.query_params.update({_k: str(st.session_state[_k]) for _k in _SCHEMA})
        st.rerun()

    if st.button("Update shareable link", key="_lb_share_btn"):
        st.query_params.update({_k: str(st.session_state[_k]) for _k in _SCHEMA})
        st.success("Your browser address bar now holds this scenario — copy the URL to share.")

    st.caption("scenario code (paste into a shared link's `?...`)")
    st.code(
        encode_scenario({_k: st.session_state.get(_k, _d) for _k, (_t, _d) in _SCHEMA.items()}),
        language="text",
    )

# ── Generate Data ────────────────────────────────────────────────────────────
@st.cache_data
def get_data(kf, km, ks, p1b, p1bk, p2k):
    return generate_level_b_data(k_fast=kf, k_medium=km, k_slow=ks,
                                  p1_burst_frac=p1b, p1_burst_k=p1bk,
                                  p2_k=p2k)

data = get_data(k_fast, k_medium, k_slow, p1_burst, p1_burst_k, p2_k)

# =============================================================================
# Concept: MDT and MRT
# =============================================================================
st.header("Key Concepts")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### MDT — Mean Dissolution Time
    **In vitro** summary parameter.

    $$MDT = \\frac{\\sum_{i} t_{mid,i} \\cdot \\Delta F_i}{\\sum_{i} \\Delta F_i}$$

    Represents the **average time** for drug to dissolve from the dosage form.

    - Faster release → lower MDT
    - Slower release → higher MDT
    """)

with col2:
    st.markdown("""
    ### MRT — Mean Residence Time
    **In vivo** summary parameter.

    $$MRT = \\frac{AUMC}{AUC} = \\frac{\\int_0^\\infty t \\cdot C(t) \\, dt}{\\int_0^\\infty C(t) \\, dt}$$

    Represents the **average time** drug molecules spend in the body. [12]

    - Faster absorption/elimination → lower MRT
    - Sustained release → higher MRT
    """)

st.markdown("---")

# =============================================================================
# Step 1: Source Profiles
# =============================================================================
st.header("Step 1: Source Profiles")
st.markdown("Three ER oral formulations with adjustable dissolution rates (use sidebar controls).")

level_a_data = data['level_a_data']

col1, col2 = st.columns(2)

with col1:
    fig_diss = plot_dissolution_profiles(
        level_a_data['times_dissolution'],
        level_a_data['dissolution_profiles'],
        ir_profile=level_a_data['ir_dissolution'],
        title='Dissolution Profiles',
    )
    fig_diss.update_layout(height=400)
    st.plotly_chart(fig_diss, use_container_width=True)

with col2:
    fig_pk = plot_pk_profiles(
        level_a_data['times_pk'],
        level_a_data['pk_profiles'],
        title='PK Profiles',
        ir_pk=level_a_data['ir_pk'],
    )
    fig_pk.update_layout(height=400)
    st.plotly_chart(fig_pk, use_container_width=True)

# =============================================================================
# Step 2: Moment Extraction
# =============================================================================
st.markdown("---")
st.header("Step 2: Extract Statistical Moments")

st.markdown("**Computed parameters for each formulation:**")

moment_rows = []
for name in data['formulation_names']:
    moment_rows.append({
        'Formulation': name,
        'MDT (h)': f"{data['mdt_values'][name]:.2f}",
        'MRT (h)': f"{data['mrt_values'][name]:.2f}",
        'VDT (h²)': f"{data['vdt_values'][name]:.1f}",
    })
st.dataframe(moment_rows, use_container_width=True, hide_index=True)

st.info("""
**VDT (Variance of Dissolution Time)** is an additional moment that can be
compared to **VRT (Variance of Residence Time)** for further Level B analysis.
""")

# =============================================================================
# Step 3: MDT vs MRT Correlation
# =============================================================================
st.markdown("---")
st.header("Step 3: Level B Correlation — MDT vs MRT")

fig_mdt_mrt = plot_mdt_vs_mrt(
    data['formulation_names'],
    data['mdt_values'],
    data['mrt_values'],
)
st.plotly_chart(fig_mdt_mrt, use_container_width=True)

st.markdown("""
The positive correlation confirms that **longer mean dissolution time**
corresponds to **longer mean residence time** — a pharmacologically
logical relationship for dissolution rate-limited absorption.
""")

# =============================================================================
# Step 4: Comparison with Level A
# =============================================================================
st.markdown("---")
st.header("Step 4: What Level B Loses Compared to Level A")

st.markdown("""
Level B reduces the entire dissolution and PK profiles to **single numbers**.
This means:

| Feature | Level A | Level B |
|:---|:---:|:---:|
| Predict plasma profile shape | ✅ Yes | ❌ No |
| Distinguish biphasic vs zero-order release | ✅ Yes | ❌ No |
| Set dissolution specifications | ✅ Yes | ❌ No |
| Support biowaiver | ✅ Yes | ⚠️ Rarely alone |
| Data requirement | Full profiles | Summary only |
| Computational complexity | Higher | Lower |
""")

# =============================================================================
# Step 5: Pathological Example
# =============================================================================
st.markdown("---")
st.header("Step 5: Limitation — Same MDT, Different PK")

st.markdown("""
**This is the key weakness of Level B. [1]** Two formulations can have
nearly identical MDT values but very different dissolution profiles
and consequently different PK behavior.

Below: **P1** (biphasic — fast burst then slow) and **P2** (steady release)
may have similar MDT values, but their plasma profiles are visually distinct.
Level B would rate them as equivalent — a misleading conclusion.

*Adjust the P1 burst fraction and P2 dissolution rate in the sidebar
to explore when MDT values converge despite different profile shapes.*
""")

path = data['pathological']
fig_path = plot_pathological_example(path)
st.plotly_chart(fig_path, use_container_width=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("P1 MDT", f"{path['MDT_P1']:.1f} h")
with col2:
    st.metric("P2 MDT", f"{path['MDT_P2']:.1f} h")
with col3:
    st.metric("P1 MRT", f"{path['MRT_P1']:.1f} h")
with col4:
    st.metric("P2 MRT", f"{path['MRT_P2']:.1f} h")

mdt_diff = abs(path['MDT_P1'] - path['MDT_P2'])
if mdt_diff < 1.0:
    st.warning(f"⚠️ **MDT difference = {mdt_diff:.1f} h** — nearly identical! Yet the profiles look very different. This demonstrates why Level B can be misleading.")
elif mdt_diff < 2.0:
    st.info(f"ℹ️ **MDT difference = {mdt_diff:.1f} h** — close but distinguishable. Try adjusting sliders to make them converge.")
else:
    st.info(f"ℹ️ **MDT difference = {mdt_diff:.1f} h** — clearly different. Adjust the P2 rate or P1 burst fraction in the sidebar to bring them closer and see the limitation.")

# =============================================================================
# Summary
# =============================================================================
st.markdown("---")
st.header("Summary: When to Use Level B")

st.markdown("""
| Situation | Level B Appropriate? |
|:---|:---:|
| Quick screening with limited data | ✅ Yes |
| Supporting evidence alongside Level A or C | ✅ Yes |
| Standalone for biowaiver application | ❌ Rarely |
| When only summary PK parameters are available | ✅ Yes |
| When profile shape matters (e.g., Cmax-driven efficacy) | ❌ No |
| Process understanding / QbD | ⚠️ Limited |

**Bottom line:** Level B provides useful directional information but should
almost never be used in isolation for regulatory purposes. Combine with
Level A or C for a complete IVIVC strategy.
""")

st.markdown("---")

_PAGE_REFS = ["yamaoka_1978", "fda_ivivc_1997", "usp_1088"]
with st.expander("📚 Evidence & sources for this page"):
    for _r in references_for(_PAGE_REFS):
        st.markdown(reference_entry_markdown(_r))
    st.caption("Full verified reference list with DOIs on the 📚 References page (sidebar).")

st.caption("**Disclaimer:** All data shown is synthetic/hypothetical, generated from pharmacokinetic and dissolution mathematical models for educational purposes only.")
