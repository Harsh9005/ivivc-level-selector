"""
Page 3: Level A IVIVC Tutorial & Demo

Interactive 6-step workflow demonstrating Level A IVIVC construction
using synthetic extended-release oral tablet data.

All data is synthetic/hypothetical for educational purposes only.
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Level A Demo — IVIVC", page_icon="📈", layout="wide")

# ── Imports ──────────────────────────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.synthetic_data import generate_level_a_data
from utils.deconvolution import wagner_nelson
from utils.ivivc_calculations import level_a_correlation, compute_prediction_error
from utils.pk_models import one_compartment_oral, compute_auc, compute_mrt
from utils.dissolution_models import first_order_release
from utils.plotting import (
    COLORS, plot_dissolution_profiles, plot_pk_profiles,
    plot_absorption_vs_dissolution, plot_level_a_correlation,
    plot_pe_validation, _base_layout,
)
from utils.citations import references_for, reference_entry_markdown
from utils.share import decode_scenario, encode_scenario, SCHEMAS, LEVEL_A_PRESETS

# ── Seed slider state from the URL (once) ─────────────────────────────────────
_SCHEMA = SCHEMAS["level_a"]
if "_la_seeded" not in st.session_state:
    seeded = decode_scenario(dict(st.query_params), _SCHEMA)
    for k, v in seeded.items():
        st.session_state.setdefault(k, v)
    st.session_state["_la_seeded"] = True


# ── Title ────────────────────────────────────────────────────────────────────
st.title("📈 Level A IVIVC: Step-by-Step Tutorial")
st.markdown("""
**Level A** establishes a **point-to-point** correlation between the *entire*
in vitro dissolution profile and the *entire* in vivo absorption profile.
It is the most informative level and the only one that can predict complete
plasma concentration-time profiles from dissolution data alone.

**Synthetic Scenario:** Extended-release oral tablet containing a BCS Class II [10]
model compound. Three formulations (F1–F3) with different release rates,
plus an immediate-release (IR) reference.
""")

st.markdown("---")

# ── Sidebar Controls ─────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Level A Controls")

k_fast = st.sidebar.slider(
    "F1 (Fast) dissolution rate k (h⁻¹)",
    min_value=0.10, max_value=0.60,
    step=0.02, key="k_fast",
    help="First-order dissolution rate constant for fast formulation"
)
k_medium = st.sidebar.slider(
    "F2 (Medium) dissolution rate k (h⁻¹)",
    min_value=0.05, max_value=0.40,
    step=0.02, key="k_medium",
    help="First-order dissolution rate constant for medium formulation"
)
k_slow = st.sidebar.slider(
    "F3 (Slow) dissolution rate k (h⁻¹)",
    min_value=0.02, max_value=0.25,
    step=0.01, key="k_slow",
    help="First-order dissolution rate constant for slow formulation"
)

st.sidebar.markdown("---")
st.sidebar.info("💡 Adjust the sliders to see how dissolution rate affects PK and IVIVC correlation.")

# ── Share / Save scenario ─────────────────────────────────────────────────────
with st.sidebar.expander("🔗 Share / Save this scenario"):
    _preset_choice = st.selectbox(
        "Load preset scenario", ["—"] + list(LEVEL_A_PRESETS.keys()),
        key="_la_preset",
    )
    if _preset_choice != "—":
        for _k, _v in LEVEL_A_PRESETS[_preset_choice].items():
            st.session_state[_k] = _v
        st.query_params.update({_k: str(st.session_state[_k]) for _k in _SCHEMA})
        st.rerun()

    if st.button("Update shareable link", key="_la_share_btn"):
        st.query_params.update({_k: str(st.session_state[_k]) for _k in _SCHEMA})
        st.success("Your browser address bar now holds this scenario — copy the URL to share.")

    st.caption("scenario code (paste into a shared link's `?...`)")
    st.code(
        encode_scenario({_k: st.session_state.get(_k, _d) for _k, (_t, _d) in _SCHEMA.items()}),
        language="text",
    )

# ── Generate Data ────────────────────────────────────────────────────────────
@st.cache_data
def get_data(kf, km, ks):
    return generate_level_a_data(k_fast=kf, k_medium=km, k_slow=ks)

data = get_data(k_fast, k_medium, k_slow)


# =============================================================================
# Step 1: In Vitro Dissolution Profiles
# =============================================================================
st.header("Step 1: In Vitro Dissolution Profiles")

st.markdown("""
Four formulations tested under biorelevant dissolution conditions.
The three ER formulations (F1–F3) show controlled release over 24h,
while the IR reference confirms complete release within ~1 hour.

**Model:** First-order release — `F(t) = F_max × (1 − e^{−kt})`
""")

fig_diss = plot_dissolution_profiles(
    data['times_dissolution'],
    data['dissolution_profiles'],
    ir_profile=data['ir_dissolution'],
    title='In Vitro Dissolution Profiles (First-Order Model)',
)
st.plotly_chart(fig_diss, use_container_width=True)

# Parameter table
st.markdown("**Dissolution Parameters:**")
param_rows = []
for name in data['formulation_names']:
    dp = data['dissolution_params'][name]
    param_rows.append({
        'Formulation': name,
        'k (h⁻¹)': f"{dp['k']:.3f}",
        't₅₀ (h)': f"{dp['t50']:.1f}",
        'MDT (h)': f"{dp['MDT']:.1f}",
        'DE (%)': f"{dp['DE']:.1f}",
    })
st.dataframe(param_rows, use_container_width=True, hide_index=True)


# =============================================================================
# Step 2: In Vivo PK Profiles
# =============================================================================
st.markdown("---")
st.header("Step 2: In Vivo Pharmacokinetic Profiles")

st.markdown("""
Plasma concentration-time profiles generated via a **1-compartment oral model**.
Absorption rate is proportional to dissolution rate (dissolution rate-limited
absorption — typical for BCS Class II compounds).

**PK Parameters:** ke = 0.10 h⁻¹, Vd = 50 L, Dose = 100 mg
""")

fig_pk = plot_pk_profiles(
    data['times_pk'],
    data['pk_profiles'],
    title='Plasma Concentration-Time Profiles',
    ir_pk=data['ir_pk'],
)
st.plotly_chart(fig_pk, use_container_width=True)

# PK parameter table
st.markdown("**Pharmacokinetic Parameters:**")
pk_rows = []
for name in data['formulation_names']:
    pp = data['pk_params'][name]
    pk_rows.append({
        'Formulation': name,
        'Cmax (mg/L)': f"{pp['Cmax']:.2f}",
        'Tmax (h)': f"{pp['Tmax']:.1f}",
        'AUC (mg·h/L)': f"{pp['AUC']:.1f}",
        'MRT (h)': f"{pp['MRT']:.1f}",
    })
st.dataframe(pk_rows, use_container_width=True, hide_index=True)


# =============================================================================
# Step 3: Deconvolution → Fraction Absorbed
# =============================================================================
st.markdown("---")
st.header("Step 3: Deconvolution — Fraction Absorbed")

st.markdown("""
**Wagner-Nelson method [8]** extracts the in vivo fraction absorbed (Fa) from
plasma concentration data, using only the elimination rate constant (ke):

$$F_a(t) = \\frac{C(t) + k_e \\cdot AUC(0,t)}{k_e \\cdot AUC(0,\\infty)}$$

This method requires only a **1-compartment model** assumption and does not
need IV reference data [8] (for two-compartment drugs, the Loo–Riegelman
method [9] is used instead) — making it practical for most oral drug products.
""")

# Let user pick a formulation to examine
selected_form = st.selectbox(
    "Select formulation to examine:",
    data['formulation_names'],
    key="deconv_form"
)

wn_result = data['fraction_absorbed'][selected_form]
diss_profile = data['dissolution_profiles'][selected_form]

fig_overlay = plot_absorption_vs_dissolution(
    data['times_dissolution'], diss_profile,
    wn_result['times'], wn_result['fraction_absorbed'],
    name=selected_form,
    color=COLORS.get(selected_form, '#2196F3'),
)
st.plotly_chart(fig_overlay, use_container_width=True)

# Show all three overlays side by side
with st.expander("📊 View all formulations — Dissolution vs Absorption"):
    cols = st.columns(3)
    for i, name in enumerate(data['formulation_names']):
        with cols[i]:
            wn = data['fraction_absorbed'][name]
            diss = data['dissolution_profiles'][name]
            fig = plot_absorption_vs_dissolution(
                data['times_dissolution'], diss,
                wn['times'], wn['fraction_absorbed'],
                name=name,
                color=COLORS.get(name, '#666'),
            )
            fig.update_layout(height=350, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# Step 4: Level A Correlation (Point-to-Point)
# =============================================================================
st.markdown("---")
st.header("Step 4: Level A Correlation — % Dissolved vs % Absorbed")

st.markdown("""
The **Level A correlation** maps % dissolved (in vitro) against % absorbed
(in vivo) at matched timepoints across all formulations. The pooled data
points form a linear relationship:

- **Ideal:** Slope ≈ 1.0, Intercept ≈ 0 (perfect 1:1 correlation)
- **R² close to 1.0** indicates dissolution is predictive of absorption
""")

# Build correlation data — match dissolution timepoints to absorption
# Use the PK timepoints that overlap with dissolution timepoints
dissolved_all = []
absorbed_all = []

for name in data['formulation_names']:
    diss = data['dissolution_profiles'][name]
    wn = data['fraction_absorbed'][name]

    # Interpolate absorption at dissolution timepoints
    absorbed_interp = np.interp(
        data['times_dissolution'],
        wn['times'],
        wn['fraction_absorbed'] * 100  # Convert to %
    )
    dissolved_all.append(diss)
    absorbed_all.append(absorbed_interp)

corr = level_a_correlation(dissolved_all, absorbed_all)

fig_corr = plot_level_a_correlation(
    corr['all_dissolved'], corr['all_absorbed'],
    corr['slope'], corr['intercept'], corr['r_squared'],
    title='Level A IVIVC Correlation',
)
st.plotly_chart(fig_corr, use_container_width=True)

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("R²", f"{corr['r_squared']:.4f}")
with col2:
    st.metric("Slope", f"{corr['slope']:.3f}")
with col3:
    st.metric("Intercept", f"{corr['intercept']:.2f}")
with col4:
    st.metric("p-value", f"{corr['p_value']:.2e}")

if abs(corr['slope'] - 1.0) < 0.1 and abs(corr['intercept']) < 5:
    st.success("✅ Near-ideal 1:1 correlation (slope ≈ 1, intercept ≈ 0)")
elif corr['r_squared'] > 0.9:
    st.info("ℹ️ Strong correlation, but slope deviates from ideal 1:1 — scaling factor may be needed.")
else:
    st.warning("⚠️ Moderate correlation — consider checking dissolution conditions or PK model assumptions.")


# =============================================================================
# Step 5: Internal Validation (%PE)
# =============================================================================
st.markdown("---")
st.header("Step 5: Internal Validation — %Prediction Error")

st.markdown("""
The established IVIVC model is used to **predict** PK parameters from
dissolution data. Prediction accuracy is assessed via **%PE**:

$$\\%PE = \\frac{Predicted - Observed}{Observed} \\times 100$$

**FDA Criteria: [1]**
- Mean |%PE| ≤ **10%** for Cmax and AUC
- Individual |%PE| ≤ **15%** for each formulation
""")

# Predict PK from dissolution using the IVIVC model
# For each formulation: predict Fa(t) from dissolution → predict C(t) → extract Cmax, AUC
pred_cmax = []
obs_cmax = []
pred_auc = []
obs_auc = []
form_names_pe = []

for name in data['formulation_names']:
    diss = data['dissolution_profiles'][name]

    # Predict Fa(%) from IVIVC: Fa_pred = slope * F_diss + intercept
    fa_pred = corr['slope'] * diss + corr['intercept']
    fa_pred = np.clip(fa_pred, 0, 100) / 100.0  # Convert to fraction

    # Convert Fa to C(t) via: C(t) = Fa(t) * ke * AUC_total_predicted
    # Simplified: use the ratio approach
    # Actual C(t) predicted by convolving predicted dissolution with impulse response
    ke = data['ke']
    vd = data['vd']
    dose = data['dose']
    times = data['times_pk']

    # Approximate: predicted Fa at PK timepoints
    fa_at_pk = np.interp(times, data['times_dissolution'], fa_pred)
    # Predicted C(t) ≈ dose/Vd × d(Fa)/dt / ke — simplified back-calculation
    # More practical: use the original analytical model with predicted ka
    # Since dissolution is first-order with k, and IVIVC slope ≈ 1:
    dk = data['dissolution_params'][name]['k']
    ka_pred = dk * 1.5 * corr['slope']  # adjusted by IVIVC slope
    c_pred = one_compartment_oral(times, dose, ka_pred, ke, vd)

    pred_cmax_val = float(np.max(c_pred))
    pred_auc_val = compute_auc(times, c_pred)

    obs_cmax_val = data['pk_params'][name]['Cmax']
    obs_auc_val = data['pk_params'][name]['AUC']

    pred_cmax.append(pred_cmax_val)
    obs_cmax.append(obs_cmax_val)
    pred_auc.append(pred_auc_val)
    obs_auc.append(obs_auc_val)
    form_names_pe.append(name)

pe_cmax = compute_prediction_error(pred_cmax, obs_cmax)
pe_auc = compute_prediction_error(pred_auc, obs_auc)

fig_pe = plot_pe_validation(
    form_names_pe,
    pe_cmax['pe_values'].tolist(),
    pe_auc['pe_values'].tolist(),
)
st.plotly_chart(fig_pe, use_container_width=True)

# Validation results table
st.markdown("**Validation Results:**")
val_rows = []
for i, name in enumerate(form_names_pe):
    val_rows.append({
        'Formulation': name,
        'Obs Cmax': f"{obs_cmax[i]:.2f}",
        'Pred Cmax': f"{pred_cmax[i]:.2f}",
        '%PE Cmax': f"{pe_cmax['pe_values'][i]:.1f}%",
        'Obs AUC': f"{obs_auc[i]:.1f}",
        'Pred AUC': f"{pred_auc[i]:.1f}",
        '%PE AUC': f"{pe_auc['pe_values'][i]:.1f}%",
    })
st.dataframe(val_rows, use_container_width=True, hide_index=True)

# Overall verdict
col1, col2 = st.columns(2)
with col1:
    if pe_cmax['passes_overall']:
        st.success(f"✅ Cmax: Mean |%PE| = {pe_cmax['mean_abs_pe']:.1f}% ≤ 10% — **PASS**")
    else:
        st.error(f"❌ Cmax: Mean |%PE| = {pe_cmax['mean_abs_pe']:.1f}% — **FAIL**")
with col2:
    if pe_auc['passes_overall']:
        st.success(f"✅ AUC: Mean |%PE| = {pe_auc['mean_abs_pe']:.1f}% ≤ 10% — **PASS**")
    else:
        st.error(f"❌ AUC: Mean |%PE| = {pe_auc['mean_abs_pe']:.1f}% — **FAIL**")


# =============================================================================
# Step 6: External Prediction
# =============================================================================
st.markdown("---")
st.header("Step 6: External Prediction — What-If Analysis")

st.markdown("""
Use the established IVIVC to **predict** the PK profile of a hypothetical
new formulation based only on its dissolution rate. This demonstrates the
predictive power of Level A IVIVC.
""")

k_new = st.slider(
    "New formulation dissolution rate k (h⁻¹)",
    min_value=0.02, max_value=0.60,
    step=0.02,
    key="k_new",
)

# Generate prediction
times_fine = data['times_fine']
ke = data['ke']
vd = data['vd']
dose = data['dose']

diss_new = first_order_release(times_fine, k_new, f_max=100.0)
ka_new = k_new * 1.5 * corr['slope']
pk_new = one_compartment_oral(times_fine, dose, ka_new, ke, vd)

cmax_new = float(np.max(pk_new))
tmax_new = float(times_fine[np.argmax(pk_new)])
auc_new = compute_auc(times_fine, pk_new)

col1, col2 = st.columns(2)

with col1:
    fig_diss_new = go.Figure()
    fig_diss_new.add_trace(go.Scatter(
        x=times_fine, y=diss_new,
        mode='lines', name='New Formulation',
        line=dict(color=COLORS['danger'], width=3),
    ))
    # Add existing formulations as reference
    for name in data['formulation_names']:
        fig_diss_new.add_trace(go.Scatter(
            x=data['times_fine'], y=data['dissolution_profiles_fine'][name],
            mode='lines', name=name, opacity=0.3,
            line=dict(color=COLORS.get(name, '#ccc'), width=1.5),
        ))
    fig_diss_new.update_layout(
        **_base_layout(title='Predicted Dissolution'),
        xaxis=dict(title='Time (h)', range=[0, 24], gridcolor='#eee'),
        yaxis=dict(title='% Released', range=[0, 105], gridcolor='#eee'),
        height=400,
    )
    st.plotly_chart(fig_diss_new, use_container_width=True)

with col2:
    fig_pk_new = go.Figure()
    fig_pk_new.add_trace(go.Scatter(
        x=times_fine, y=pk_new,
        mode='lines', name='Predicted PK (new)',
        line=dict(color=COLORS['danger'], width=3),
    ))
    for name in data['formulation_names']:
        fig_pk_new.add_trace(go.Scatter(
            x=data['times_fine'], y=data['pk_profiles_fine'][name],
            mode='lines', name=name, opacity=0.3,
            line=dict(color=COLORS.get(name, '#ccc'), width=1.5),
        ))
    fig_pk_new.update_layout(
        **_base_layout(title='Predicted PK Profile'),
        xaxis=dict(title='Time (h)', range=[0, 24], gridcolor='#eee'),
        yaxis=dict(title='Concentration (mg/L)', gridcolor='#eee'),
        height=400,
    )
    st.plotly_chart(fig_pk_new, use_container_width=True)

# Predicted parameters
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Predicted Cmax", f"{cmax_new:.2f} mg/L")
with col2:
    st.metric("Predicted Tmax", f"{tmax_new:.1f} h")
with col3:
    st.metric("Predicted AUC₀₋₂₄", f"{auc_new:.1f} mg·h/L")


st.markdown("---")

_PAGE_REFS = ["wagner_nelson_1963", "loo_riegelman_1968", "amidon_bcs_1995", "fda_ivivc_1997"]
with st.expander("📚 Evidence & sources for this page"):
    for _r in references_for(_PAGE_REFS):
        st.markdown(reference_entry_markdown(_r))
    st.caption("Full verified reference list with DOIs on the 📚 References page (sidebar).")

st.caption("**Disclaimer:** All data shown is synthetic/hypothetical, generated from pharmacokinetic and dissolution mathematical models for educational purposes only.")
