"""
Page 6: Analyze Your Own Data

Run REAL Level A / B / C IVIVC analysis on the user's own dissolution + PK data,
entirely client-side (everything runs in the browser via stlite/Pyodide — no data
is uploaded to any server). The science is reused verbatim from utils/.

Unlike the demo pages, the data analyzed here is the USER's (which may be real).
The app itself ships no real data; results depend entirely on the data quality
the user provides.
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Analyze Your Data — IVIVC", page_icon="🧪", layout="wide")

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.data_io import (
    DataValidationError, parse_profile_csv, align_dissolution_to_pk,
    estimate_ke, dissolution_template_csv, pk_template_csv,
    example_dissolution_csv, example_pk_csv,
)
from utils.deconvolution import wagner_nelson
from utils.ivivc_calculations import (
    level_a_correlation, level_c_correlation, build_correlation_matrix,
)
from utils.dissolution_models import compute_mdt, compute_de, compute_f1_f2
from utils.pk_models import compute_auc, compute_mrt
from utils.plotting import (
    COLORS, plot_level_a_correlation, plot_correlation_heatmap,
    plot_level_c_scatter, _base_layout,
)


# ── Title & intro ─────────────────────────────────────────────────────────────
st.title("🧪 Analyze Your Own Data")

st.markdown("""
Run **real Level A, B, and C IVIVC analysis** on **your own** dissolution and
pharmacokinetic (PK) data. Upload or paste two CSVs — a **dissolution** profile
and a **PK** profile — and this page deconvolves, correlates, and validates them
using the same peer-reviewed methods documented in the demo pages.

🔒 **Everything runs in your browser.** This app is a static page powered by
[stlite](https://github.com/whitphx/stlite) (Pyodide/WebAssembly). Your data is
**never uploaded to any server** — parsing and computation happen entirely on
your own machine.

> ℹ️ This tool is for **methodological / educational** use. The quality of any
> IVIVC depends on the quality of your data (number of formulations, time-point
> spacing, PK model assumptions). At least **3 formulations** are recommended for
> a meaningful correlation.
""")

st.markdown("---")

# =============================================================================
# Inputs
# =============================================================================
st.header("1. Provide your data")

st.markdown("""
Each CSV needs a **time** column first (named `time`, `Time`, or `t`), then one
column per **formulation** (the header is the formulation name).

- **Dissolution CSV** — values are cumulative **% released** at each time.
- **PK CSV** — values are **plasma concentration** at each time.
""")

# Session-state buffers so the "Load example" button can populate the text areas.
if "diss_text" not in st.session_state:
    st.session_state["diss_text"] = ""
if "pk_text" not in st.session_state:
    st.session_state["pk_text"] = ""

# --- example loader + template downloads ------------------------------------
btn_cols = st.columns([1, 1, 1, 1])
with btn_cols[0]:
    if st.button("📥 Load example dataset", use_container_width=True,
                 help="Fill both inputs with a clearly synthetic 3-formulation example"):
        st.session_state["diss_text"] = example_dissolution_csv()
        st.session_state["pk_text"] = example_pk_csv()
with btn_cols[1]:
    st.download_button(
        "⬇️ Dissolution template", dissolution_template_csv(),
        file_name="dissolution_template.csv", mime="text/csv",
        use_container_width=True,
    )
with btn_cols[2]:
    st.download_button(
        "⬇️ PK template", pk_template_csv(),
        file_name="pk_template.csv", mime="text/csv",
        use_container_width=True,
    )
with btn_cols[3]:
    if st.button("🗑️ Clear inputs", use_container_width=True):
        st.session_state["diss_text"] = ""
        st.session_state["pk_text"] = ""

col_d, col_p = st.columns(2)

with col_d:
    st.subheader("Dissolution data")
    diss_upload = st.file_uploader(
        "Upload dissolution CSV", type=["csv"], key="diss_upload",
        help="Time + one column per formulation (% released).",
    )
    st.session_state["diss_text"] = st.text_area(
        "…or paste dissolution CSV",
        value=st.session_state["diss_text"],
        height=180, key="diss_area",
        placeholder="time,F1,F2,F3\n0,0,0,0\n1,35,22,12\n...",
    )

with col_p:
    st.subheader("PK (plasma concentration) data")
    pk_upload = st.file_uploader(
        "Upload PK CSV", type=["csv"], key="pk_upload",
        help="Time + one column per formulation (plasma concentration).",
    )
    st.session_state["pk_text"] = st.text_area(
        "…or paste PK CSV",
        value=st.session_state["pk_text"],
        height=180, key="pk_area",
        placeholder="time,F1,F2,F3\n0,0,0,0\n1,3.1,2.0,1.1\n...",
    )

# --- elimination rate constant ----------------------------------------------
st.subheader("Elimination rate constant (kₑ)")
st.markdown(
    "Wagner-Nelson deconvolution (Level A) needs the first-order elimination "
    "rate constant `ke` (h⁻¹). Enter it, or estimate it from the terminal slope "
    "of your first formulation's PK curve."
)
ke_cols = st.columns([1, 2])
with ke_cols[0]:
    ke_input = st.number_input(
        "ke (h⁻¹)", min_value=0.001, value=0.10, step=0.01, format="%.3f",
        key="ke_input",
    )
with ke_cols[1]:
    estimate_ke_checkbox = st.checkbox(
        "Estimate ke from terminal PK slope",
        value=False, key="ke_estimate",
        help="Log-linear regression over the descending tail of the first "
             "formulation's PK curve.",
    )


def _read_source(upload, pasted_text):
    """Prefer an uploaded file; fall back to pasted text. Return CSV string."""
    if upload is not None:
        return upload.getvalue().decode("utf-8")
    if pasted_text and pasted_text.strip():
        return pasted_text
    return None


# Resolve current sources for the optional ke estimate preview.
_diss_src = _read_source(diss_upload, st.session_state["diss_text"])
_pk_src = _read_source(pk_upload, st.session_state["pk_text"])

ke_value = float(ke_input)
if estimate_ke_checkbox:
    if _pk_src is None:
        st.warning("Provide PK data (upload or paste) to estimate ke.")
    else:
        try:
            _pk_preview = parse_profile_csv(_pk_src, value_label="concentration")
            first = _pk_preview["names"][0]
            ke_value = estimate_ke(_pk_preview["times"], _pk_preview["series"][first])
            st.success(
                f"Estimated ke = **{ke_value:.4f} h⁻¹** "
                f"(from the terminal slope of '{first}'). Used for the analysis below."
            )
        except DataValidationError as exc:
            st.error(f"Could not estimate ke: {exc}")
            st.info("Falling back to the manually entered ke.")
            ke_value = float(ke_input)

st.markdown("---")

# =============================================================================
# Run analysis
# =============================================================================
run = st.button("🔬 Run analysis", type="primary", use_container_width=True)

if not run:
    st.info("Provide your two CSVs (or click **Load example dataset**), set ke, "
            "then press **🔬 Run analysis**.")
    st.stop()

# --- parse + align (all guarded) --------------------------------------------
if _diss_src is None or _pk_src is None:
    st.error("Please provide BOTH a dissolution CSV and a PK CSV "
             "(upload or paste), or click **Load example dataset**.")
    st.stop()

try:
    diss = parse_profile_csv(_diss_src, value_label="% released")
    pk = parse_profile_csv(_pk_src, value_label="concentration")
    aligned = align_dissolution_to_pk(diss, pk)
except DataValidationError as exc:
    st.error(f"⚠️ {exc}")
    st.stop()
except Exception as exc:  # last-resort guard — never crash the page
    st.error(f"⚠️ Unexpected problem reading your data: {exc}")
    st.stop()

names = aligned["names"]
pk_times = aligned["pk_times"]

if aligned["warnings"]:
    for w in aligned["warnings"]:
        st.warning(f"⚠️ {w}")

if len(names) < 2:
    st.error("Need at least 2 matched formulations to build a correlation.")
    st.stop()

if len(names) < 3:
    st.info("ℹ️ Only 2 formulations matched — Level C correlations will be "
            "trivially perfect (R²=1.00 with two points). Add a 3rd formulation "
            "for a meaningful Level C IVIVC.")

st.success(f"Parsed {len(names)} formulation(s): {', '.join(names)} · "
           f"ke = {ke_value:.4f} h⁻¹")


def _color(i, name):
    return COLORS.get(name, ["#2196F3", "#FF9800", "#4CAF50",
                             "#E91E63", "#9C27B0", "#00BCD4"][i % 6])


# =============================================================================
# Level A
# =============================================================================
st.markdown("---")
st.header("Level A — Point-to-Point Correlation")
st.markdown("""
For each formulation: **Wagner-Nelson** deconvolution turns your PK curve into
fraction absorbed Fa(t); dissolution is interpolated onto the PK time grid; then
**% dissolved** is regressed against **% absorbed** across all pooled timepoints.
""")

diss_list = []
abs_list = []
wn_by_name = {}
for name in names:
    conc = aligned["conc"][name]
    wn = wagner_nelson(pk_times, conc, ke_value)
    wn_by_name[name] = wn
    pct_absorbed = wn["fraction_absorbed"] * 100.0
    diss_list.append(aligned["dissolved"][name])
    abs_list.append(pct_absorbed)

level_a = level_a_correlation(diss_list, abs_list)

fig_a = plot_level_a_correlation(
    level_a["all_dissolved"], level_a["all_absorbed"],
    level_a["slope"], level_a["intercept"], level_a["r_squared"],
    title="Your Level A IVIVC Correlation",
)
st.plotly_chart(fig_a, use_container_width=True)

a1, a2, a3, a4 = st.columns(4)
a1.metric("R²", f"{level_a['r_squared']:.4f}")
a2.metric("Slope", f"{level_a['slope']:.3f}")
a3.metric("Intercept", f"{level_a['intercept']:.2f}")
a4.metric("p-value", f"{level_a['p_value']:.2e}")

if level_a["r_squared"] >= 0.9 and abs(level_a["slope"] - 1.0) < 0.15:
    st.success("✅ Strong, near-ideal Level A correlation (R² ≥ 0.9, slope ≈ 1).")
elif level_a["r_squared"] >= 0.9:
    st.info("ℹ️ Strong correlation, but slope deviates from 1:1 — a scaling "
            "factor may be appropriate.")
else:
    st.warning("⚠️ Modest Level A correlation — check time-point spacing, ke, "
               "and the 1-compartment assumption of Wagner-Nelson.")

with st.expander("📋 Per-formulation Wagner-Nelson detail"):
    for name in names:
        wn = wn_by_name[name]
        rows = [
            {
                "Time (h)": f"{t:g}",
                "% Dissolved": f"{aligned['dissolved'][name][i]:.1f}",
                "Conc": f"{aligned['conc'][name][i]:.3f}",
                "% Absorbed (Fa)": f"{wn['fraction_absorbed'][i] * 100:.1f}",
            }
            for i, t in enumerate(pk_times)
        ]
        st.markdown(f"**{name}** — AUC₀₋∞ = {wn['auc_total']:.2f}")
        st.dataframe(rows, use_container_width=True, hide_index=True)


# =============================================================================
# Level B
# =============================================================================
st.markdown("---")
st.header("Level B — MDT vs MRT")
st.markdown("""
Level B compares a **statistical-moment** summary of dissolution (Mean
Dissolution Time, MDT) with one of the PK curve (Mean Residence Time, MRT). It
uses all the data but, unlike Level A, is not a point-to-point map.
""")

mdt_vals = {}
mrt_vals = {}
for name in names:
    mdt_vals[name] = compute_mdt(diss["times"], diss["series"][name])
    mrt_vals[name] = compute_mrt(pk_times, aligned["conc"][name])

b_rows = [
    {"Formulation": name,
     "MDT (h)": f"{mdt_vals[name]:.2f}",
     "MRT (h)": f"{mrt_vals[name]:.2f}"}
    for name in names
]
st.dataframe(b_rows, use_container_width=True, hide_index=True)

fig_b = go.Figure()
for i, name in enumerate(names):
    fig_b.add_trace(go.Scatter(
        x=[mdt_vals[name]], y=[mrt_vals[name]],
        mode="markers+text", name=name,
        text=[name], textposition="top center",
        marker=dict(size=14, color=_color(i, name)),
    ))
mdt_arr = np.array([mdt_vals[n] for n in names])
mrt_arr = np.array([mrt_vals[n] for n in names])
level_b = level_c_correlation(mdt_arr, mrt_arr)  # same single-point regression
if len(names) >= 2 and mdt_arr.max() > mdt_arr.min():
    xfit = np.linspace(mdt_arr.min() * 0.9, mdt_arr.max() * 1.1, 50)
    fig_b.add_trace(go.Scatter(
        x=xfit, y=level_b["slope"] * xfit + level_b["intercept"],
        mode="lines", name=f"R² = {level_b['r_squared']:.3f}",
        line=dict(color="gray", dash="dash", width=1.5),
    ))
fig_b.update_layout(
    **_base_layout(title="Level B: MDT vs MRT"),
    xaxis=dict(title="MDT — Mean Dissolution Time (h)", gridcolor="#eee", zeroline=False),
    yaxis=dict(title="MRT — Mean Residence Time (h)", gridcolor="#eee", zeroline=False),
)
st.plotly_chart(fig_b, use_container_width=True)
st.metric("Level B R² (MDT vs MRT)", f"{level_b['r_squared']:.4f}")


# =============================================================================
# Level C
# =============================================================================
st.markdown("---")
st.header("Level C — Single-Point Correlations")
st.markdown("""
Level C correlates one **in vitro** dissolution parameter with one **in vivo**
PK parameter, across formulations. The heatmap maps every pair; pick a pair below
to inspect the scatter.
""")

in_vitro_params = {
    "% released (final)": [float(diss["series"][n][-1]) for n in names],
    "DE (%)": [compute_de(diss["times"], diss["series"][n]) for n in names],
    "MDT (h)": [mdt_vals[n] for n in names],
}
in_vivo_params = {
    "AUC": [compute_auc(pk_times, aligned["conc"][n]) for n in names],
    "Cmax": [float(np.max(aligned["conc"][n])) for n in names],
    "Tmax": [float(pk_times[int(np.argmax(aligned["conc"][n]))]) for n in names],
    "MRT": [mrt_vals[n] for n in names],
}
iv_names = list(in_vitro_params.keys())
vivo_names = list(in_vivo_params.keys())

matrix = build_correlation_matrix(in_vitro_params, in_vivo_params, iv_names, vivo_names)
fig_heat = plot_correlation_heatmap(
    matrix["r_squared_matrix"], matrix["iv_names"], matrix["vivo_names"],
    matrix["slope_matrix"],
)
st.plotly_chart(fig_heat, use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    sel_iv = st.selectbox("In vitro parameter:", iv_names, index=1, key="user_iv")
with c2:
    sel_vivo = st.selectbox("In vivo parameter:", vivo_names, index=0, key="user_vivo")

iv_vals = in_vitro_params[sel_iv]
vivo_vals = in_vivo_params[sel_vivo]
level_c = level_c_correlation(iv_vals, vivo_vals)

fig_c = plot_level_c_scatter(
    iv_vals, vivo_vals, sel_iv, sel_vivo, names,
    level_c["slope"], level_c["intercept"], level_c["r_squared"],
)
st.plotly_chart(fig_c, use_container_width=True)

cc1, cc2, cc3, cc4 = st.columns(4)
cc1.metric("R²", f"{level_c['r_squared']:.4f}")
cc2.metric("Slope", f"{level_c['slope']:.4f}")
cc3.metric("Direction", "Positive ↑" if level_c["slope"] > 0 else "Negative ↓")
cc4.metric("p-value", f"{level_c['p_value']:.4f}")


# =============================================================================
# f1 / f2 dissolution similarity
# =============================================================================
st.markdown("---")
st.header("f1 / f2 — Dissolution Profile Similarity")
st.markdown("""
The FDA/EMA difference (**f1**) and similarity (**f2**) factors compare a
**reference** dissolution profile against each other formulation, on the
dissolution time grid.

- **f1 ≤ 15** → SIMILAR · **f2 ≥ 50** → SIMILAR
""")

ref_form = st.selectbox("Reference formulation:", names, index=0, key="user_f1f2_ref")
ref_profile = diss["series"][ref_form]

f1f2_rows = []
for name in names:
    if name == ref_form:
        continue
    f1, f2 = compute_f1_f2(ref_profile, diss["series"][name])
    verdict_f1 = "SIMILAR ✅" if f1 <= 15 else "DIFFERENT ❌"
    verdict_f2 = "SIMILAR ✅" if f2 >= 50 else "DIFFERENT ❌"
    f1f2_rows.append({
        "Comparison": f"{ref_form} vs {name}",
        "f1": f"{f1:.1f}",
        "f1 verdict": verdict_f1,
        "f2": f"{f2:.1f}",
        "f2 verdict": verdict_f2,
    })

if f1f2_rows:
    st.dataframe(f1f2_rows, use_container_width=True, hide_index=True)
else:
    st.info("Provide at least 2 formulations to compute f1/f2 comparisons.")

st.caption(
    "Note: f1/f2 are most informative when both profiles share the same "
    "dissolution time points and use comparable sampling; with very few points "
    "the factors are sensitive to spacing."
)

# =============================================================================
# Disclaimer
# =============================================================================
st.markdown("---")
st.caption(
    "**About this page:** Unlike the demo pages (which use synthetic data), this "
    "page analyzes **your own** dissolution and PK data — which may be real. All "
    "parsing and computation run **entirely in your browser** (stlite/Pyodide); "
    "no data is uploaded to any server. Results are for methodological/educational "
    "use and depend on the quality and design of the data you provide."
)
