"""
Page 5: Level C IVIVC Tutorial & Demo

Interactive single-point correlations with PLGA depot scenario.

All data is synthetic/hypothetical for educational purposes only.
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Level C Demo — IVIVC", page_icon="📉", layout="wide")

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.synthetic_data import generate_level_c_data
from utils.ivivc_calculations import level_c_correlation, build_correlation_matrix
from utils.dissolution_models import compute_f1_f2
from utils.plotting import (
    COLORS, plot_level_c_scatter, plot_correlation_heatmap,
    plot_f1_f2_bars, _base_layout,
)

# ── Title ────────────────────────────────────────────────────────────────────
st.title("📉 Level C IVIVC: Single-Point Correlations")

st.markdown("""
**Level C** correlates **individual** dissolution parameters (e.g., % released
at 24h, dissolution efficiency) with **individual** PK parameters (e.g., AUC,
MRT, Tmax). While it cannot predict the entire plasma profile, it provides:

- **Mechanistic insight** into how formulation variables drive PK outcomes
- **Practical formulation screening** during early development
- A basis for **clinically relevant dissolution specifications**

**Synthetic Scenario:** Hypothetical PLGA microsphere depot (IM injection)
with three formulations differing in polymer molecular weight.
""")

st.markdown("---")

# ── Generate Data ────────────────────────────────────────────────────────────
@st.cache_data
def get_data():
    return generate_level_c_data()

data = get_data()


# =============================================================================
# Step 1: Source Profiles
# =============================================================================
st.header("Step 1: In Vitro and In Vivo Profiles")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Dissolution Profiles (30 days)")
    fig_diss = go.Figure()
    for name in data['formulations']:
        color = COLORS.get(name, '#666')
        fig_diss.add_trace(go.Scatter(
            x=data['iv_times_d'], y=data['dissolution'][name],
            mode='lines+markers', name=name,
            line=dict(color=color, width=2.5),
            marker=dict(size=6),
        ))
    fig_diss.add_trace(go.Scatter(
        x=data['iv_times_d'], y=data['dissolution']['Solution'],
        mode='lines+markers', name='Solution',
        line=dict(color=COLORS['Solution'], width=2, dash='dash'),
        marker=dict(size=5, symbol='diamond'),
    ))
    fig_diss.update_layout(
        **_base_layout(title='In Vitro Release Profiles'),
        xaxis=dict(title='Time (days)', gridcolor='#eee'),
        yaxis=dict(title='Cumulative % Released', range=[0, 105], gridcolor='#eee'),
        height=420,
    )
    st.plotly_chart(fig_diss, use_container_width=True)

with col2:
    st.subheader("PK Profiles (C/Cmax normalized)")
    fig_pk = go.Figure()
    for name in data['formulations']:
        color = COLORS.get(name, '#666')
        fig_pk.add_trace(go.Scatter(
            x=data['pk_times_d'], y=data['pk_normalized'][name],
            mode='lines+markers', name=name,
            line=dict(color=color, width=2.5),
            marker=dict(size=6),
        ))
    fig_pk.update_layout(
        **_base_layout(title='Normalized PK Profiles (C/Cmax)'),
        xaxis=dict(title='Time (days)', gridcolor='#eee'),
        yaxis=dict(title='C/Cmax', gridcolor='#eee'),
        height=420,
    )
    st.plotly_chart(fig_pk, use_container_width=True)

# Parameter tables
st.markdown("---")
st.subheader("Derived Parameters")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**In Vitro Parameters:**")
    iv_rows = []
    for name in data['formulations']:
        row = {'Formulation': name}
        row.update({k: f"{v:.1f}" for k, v in data['iv_params'][name].items()})
        iv_rows.append(row)
    st.dataframe(iv_rows, use_container_width=True, hide_index=True)

with col2:
    st.markdown("**In Vivo Parameters:**")
    vivo_rows = []
    for name in data['formulations']:
        row = {'Formulation': name}
        row.update({k: f"{v:.1f}" for k, v in data['vivo_params'][name].items()})
        vivo_rows.append(row)
    st.dataframe(vivo_rows, use_container_width=True, hide_index=True)


# =============================================================================
# Step 2: Interactive Parameter Selector
# =============================================================================
st.markdown("---")
st.header("Step 2: Interactive Level C Correlation")

st.markdown("""
Select any combination of in vitro and in vivo parameters to explore
the correlation. The scatter plot, regression line, and R² update automatically.
""")

# Get parameter names
iv_param_names = list(data['iv_params'][data['formulations'][0]].keys())
vivo_param_names = list(data['vivo_params'][data['formulations'][0]].keys())

col1, col2 = st.columns(2)
with col1:
    selected_iv = st.selectbox(
        "In Vitro Parameter:", iv_param_names,
        index=iv_param_names.index('DE (%)'),
        key="iv_select"
    )
with col2:
    selected_vivo = st.selectbox(
        "In Vivo Parameter:", vivo_param_names,
        index=0,
        key="vivo_select"
    )

# Get values
iv_values = [data['iv_params'][name][selected_iv] for name in data['formulations']]
vivo_values = [data['vivo_params'][name][selected_vivo] for name in data['formulations']]

# Compute correlation
corr = level_c_correlation(iv_values, vivo_values)

# Plot
fig_scatter = plot_level_c_scatter(
    iv_values, vivo_values,
    selected_iv, selected_vivo,
    data['formulations'],
    corr['slope'], corr['intercept'], corr['r_squared'],
)
st.plotly_chart(fig_scatter, use_container_width=True)

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("R²", f"{corr['r_squared']:.4f}")
with col2:
    st.metric("Slope", f"{corr['slope']:.4f}")
with col3:
    slope_dir = "Positive ↑" if corr['slope'] > 0 else "Negative ↓"
    st.metric("Direction", slope_dir)
with col4:
    st.metric("p-value", f"{corr['p_value']:.4f}")

# Mechanistic interpretation
if corr['slope'] > 0:
    st.info(f"**Positive slope:** Higher {selected_iv} → higher {selected_vivo}. This suggests that increased dissolution directly drives the in vivo response.")
else:
    st.info(f"**Negative slope:** Higher {selected_iv} → lower {selected_vivo}. This may indicate that faster release leads to lower sustained exposure (common for depot formulations).")


# =============================================================================
# Step 3: Full Correlation Matrix (Heatmap)
# =============================================================================
st.markdown("---")
st.header("Step 3: Full Correlation Matrix")

st.markdown("""
The **8 × 3 heatmap** maps all in vitro parameters against all in vivo parameters.
Cell values show R² and slope direction (↑ positive, ↓ negative).
Click on any cell's parameter pair above to explore it in detail.
""")

# Build full matrix
in_vitro_dict = {}
for param_name in iv_param_names:
    in_vitro_dict[param_name] = [data['iv_params'][name][param_name]
                                  for name in data['formulations']]

in_vivo_dict = {}
for param_name in vivo_param_names:
    in_vivo_dict[param_name] = [data['vivo_params'][name][param_name]
                                 for name in data['formulations']]

matrix = build_correlation_matrix(
    in_vitro_dict, in_vivo_dict,
    iv_param_names, vivo_param_names,
)

fig_heatmap = plot_correlation_heatmap(
    matrix['r_squared_matrix'],
    matrix['iv_names'],
    matrix['vivo_names'],
    matrix['slope_matrix'],
)
st.plotly_chart(fig_heatmap, use_container_width=True)

# Key observations
st.markdown("""
**Key observations from the heatmap:**
- **MRT** typically shows the strongest correlations across dissolution parameters
- **MDT** is often the only parameter with a **positive slope** — longer dissolution → longer residence
- **Tmax** correlations may be weaker due to non-linear absorption kinetics
""")


# =============================================================================
# Step 4: f1/f2 Dissolution Similarity
# =============================================================================
st.markdown("---")
st.header("Step 4: f1/f2 Dissolution Similarity Analysis")

st.markdown("""
The **f1/f2 framework** (FDA/EMA) quantifies dissolution profile similarity:

| Factor | Formula | Criteria |
|:---:|:---|:---:|
| **f1** (Difference) | Σ\\|Rt − Tt\\| / ΣRt × 100 | f1 ≤ 15 → Similar |
| **f2** (Similarity) | 50 × log₁₀{[1 + (1/n)Σ(Rt−Tt)²]⁻⁰·⁵ × 100} | f2 ≥ 50 → Similar |
""")

# Interactive f1/f2 calculator
st.subheader("f1/f2 Calculator")

col1, col2 = st.columns(2)
with col1:
    ref_form = st.selectbox("Reference formulation:", data['formulations'], key="f1f2_ref")
with col2:
    available_test = [f for f in list(data['formulations']) + ['Solution'] if f != ref_form]
    test_form = st.selectbox("Test formulation:", available_test, key="f1f2_test")

# Get profiles
ref_profile = data['dissolution'][ref_form]
test_profile = data['dissolution'].get(test_form, data['dissolution']['Solution'])

f1, f2 = compute_f1_f2(ref_profile, test_profile)

col1, col2 = st.columns(2)
with col1:
    if f1 <= 15:
        st.success(f"**f1 = {f1:.1f}** ≤ 15 → **SIMILAR** ✅")
    else:
        st.error(f"**f1 = {f1:.1f}** > 15 → **DIFFERENT** ❌")
with col2:
    if f2 >= 50:
        st.success(f"**f2 = {f2:.1f}** ≥ 50 → **SIMILAR** ✅")
    else:
        st.error(f"**f2 = {f2:.1f}** < 50 → **DIFFERENT** ❌")

# Pre-computed f1/f2 summary
st.markdown("---")
st.subheader("Pre-Computed f1/f2 Summary")

fig_f1f2 = plot_f1_f2_bars(data['f1_f2'])
st.plotly_chart(fig_f1f2, use_container_width=True)


# =============================================================================
# Step 5: Statistical Considerations — n=2 vs n=3
# =============================================================================
st.markdown("---")
st.header("Step 5: Why n ≥ 3 Formulations Matters")

st.markdown("""
With **n = 2** formulations, any Level C correlation yields **R² = 1.00 trivially**
(two points always define a perfect line). The scientific value is limited to slope
direction and magnitude.

With **n = 3** formulations (as shown here), R² values range from ~0.77 to ~0.97,
providing genuine statistical power to distinguish strong from weak correlations.
""")

show_n2 = st.toggle("Show n=2 comparison (remove Formulation C)", value=False)

if show_n2:
    # Take only first 2 formulations
    iv_2 = iv_values[:2]
    vivo_2 = vivo_values[:2]
    corr_2 = level_c_correlation(iv_2, vivo_2)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**n=3 formulations:** R² = {corr['r_squared']:.4f}")
    with col2:
        st.markdown(f"**n=2 formulations:** R² = {corr_2['r_squared']:.4f} (trivially perfect)")

    st.warning("⚠️ With n=2, R² is always 1.00 regardless of the biological reality. This demonstrates why ≥3 formulations are needed for meaningful Level C IVIVC.")

# Slope direction guide
st.markdown("---")
st.subheader("Slope Direction as Mechanistic Indicator")

st.markdown("""
| Slope | Interpretation | Example |
|:---:|:---|:---|
| **Negative (↓)** | Faster/higher release → shorter exposure or faster peak | %Released vs AUC |
| **Positive (↑)** | Longer dissolution → longer residence | MDT vs MRT |

Slope direction provides **mechanistic insight** into how the formulation
variable influences the pharmacokinetic outcome.
""")

st.markdown("---")
st.caption("**Disclaimer:** All data shown is synthetic/hypothetical, generated from pharmacokinetic and dissolution mathematical models for educational purposes only.")
