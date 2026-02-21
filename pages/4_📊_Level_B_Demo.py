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

# ── Title ────────────────────────────────────────────────────────────────────
st.title("📊 Level B IVIVC: Statistical Moment Comparison")

st.markdown("""
**Level B** correlates **summary statistical moments** of the dissolution
and plasma profiles — specifically, **Mean Dissolution Time (MDT)** versus
**Mean Residence Time (MRT)**.

Unlike Level A, Level B does **not** map the entire time course.
It reduces each profile to a single number, which means:
- It **cannot predict** the shape of the plasma profile
- It has **limited regulatory value** for biowaivers
- It is mainly useful as **supporting evidence** alongside other IVIVC levels
""")

st.markdown("---")

# ── Generate Data ────────────────────────────────────────────────────────────
@st.cache_data
def get_data():
    return generate_level_b_data()

data = get_data()

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

    Represents the **average time** drug molecules spend in the body.

    - Faster absorption/elimination → lower MRT
    - Sustained release → higher MRT
    """)

st.markdown("---")

# =============================================================================
# Step 1: Source Profiles
# =============================================================================
st.header("Step 1: Source Profiles")
st.markdown("The same three formulations from the Level A scenario (ER oral tablet).")

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
**This is the key weakness of Level B.** Two formulations can have
nearly identical MDT values but very different dissolution profiles
and consequently different PK behavior.

Below: **P1** (biphasic — fast burst then slow) and **P2** (steady release)
have similar MDT values, but their plasma profiles are visually distinct.
Level B would rate them as equivalent — a misleading conclusion.
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

st.warning("""
⚠️ **Takeaway:** Level B correlation (MDT vs MRT) can be misleading because
different dissolution profile shapes can produce the same mean value.
This is why Level A (time-course mapping) is preferred for regulatory submissions.
""")

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
st.caption("**Disclaimer:** All data shown is synthetic/hypothetical, generated from pharmacokinetic and dissolution mathematical models for educational purposes only.")
