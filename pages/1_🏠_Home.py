"""
Page 1: Home — IVIVC Overview and Introduction
"""

import streamlit as st

st.set_page_config(page_title="Home — IVIVC", page_icon="🏠", layout="wide")

st.title("🏠 In Vitro–In Vivo Correlation (IVIVC)")
st.markdown("### A Framework for Linking Dissolution to Pharmacokinetics")

st.markdown("---")

# What is IVIVC?
st.header("What is IVIVC?")
st.markdown("""
**In Vitro–In Vivo Correlation (IVIVC)** establishes a predictive mathematical
relationship between an *in vitro* property of a dosage form (typically the
dissolution rate) and a relevant *in vivo* response (typically plasma drug
concentration or bioavailability).

IVIVC is a cornerstone of pharmaceutical development because it:
- Reduces the need for costly and time-consuming bioequivalence studies
- Enables **biowaivers** for formulation and manufacturing changes
- Supports **Quality by Design (QbD)** by linking critical quality attributes to clinical outcomes
- Provides a scientific basis for **dissolution specification setting**
""")

st.markdown("---")

# Comparison Table
st.header("IVIVC Levels at a Glance")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 📈 Level A
    **Point-to-point correlation**

    Maps the *entire* in vitro dissolution profile to the *entire*
    in vivo absorption profile at matched timepoints.

    | Aspect | Detail |
    |:---|:---|
    | **Correlation** | Time-course mapping |
    | **Method** | Deconvolution (Wagner-Nelson, numerical) |
    | **Regulatory value** | ⭐⭐⭐ Highest — enables biowaiver |
    | **Data needed** | Full PK profiles, reference data |
    | **Predictive power** | Can predict entire plasma profile |
    """)

with col2:
    st.markdown("""
    ### 📊 Level B
    **Statistical moment comparison**

    Compares summary statistics: Mean Dissolution Time (MDT)
    vs Mean Residence Time (MRT).

    | Aspect | Detail |
    |:---|:---|
    | **Correlation** | Summary parameters |
    | **Method** | Moment analysis (MDT vs MRT) |
    | **Regulatory value** | ⭐ Limited — single metric |
    | **Data needed** | Summary PK parameters |
    | **Predictive power** | Cannot predict plasma profile |
    """)

with col3:
    st.markdown("""
    ### 📉 Level C
    **Single-point correlation**

    Correlates one dissolution parameter (e.g., % released at 24h)
    with one PK parameter (e.g., AUC, Tmax).

    | Aspect | Detail |
    |:---|:---|
    | **Correlation** | Individual parameter pairs |
    | **Method** | Linear regression |
    | **Regulatory value** | ⭐⭐ Useful for screening |
    | **Data needed** | Minimal — summary values |
    | **Predictive power** | Partial — one parameter at a time |
    """)

st.markdown("---")

# When is IVIVC Needed?
st.header("When is IVIVC Needed?")

st.markdown("""
| Application | Description | Recommended Level |
|:---|:---|:---:|
| **Biowaiver for formulation changes** | Avoid new BE studies when changing excipients, equipment, or manufacturing site | Level A |
| **Setting dissolution specifications** | Define clinically meaningful acceptance criteria | Level A or C |
| **Formulation screening** | Rank-order candidates during early development | Level C |
| **Process understanding (QbD)** | Link critical process parameters to PK outcomes | Level A |
| **Post-approval changes** | Support SUPAC changes with dissolution data | Level A |
| **Mechanistic insight** | Understand how formulation variables drive PK | Level C |
""")

st.markdown("---")

# Regulatory Context
st.header("Regulatory Context")

st.info("""
**FDA Guidance:** [Extended Release Oral Dosage Forms: IVIVC (1997)](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/extended-release-oral-dosage-forms-development-evaluation-and-application-vitroin-in-vivo-correlations)

**EMA Guideline:** [Quality of Oral Modified Release Products (2014)](https://www.ema.europa.eu/en/documents/scientific-guideline/guideline-quality-oral-modified-release-products_en.pdf)

These guidelines describe the development, evaluation, and application of IVIVC
for modified-release dosage forms.
""")

# Navigation
st.markdown("---")
st.header("Get Started")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    #### 🔍 Find Your Level
    Answer 6 questions to get a personalized
    recommendation for your project.

    *Navigate to* **Level Selector** *in the sidebar.*
    """)

with col2:
    st.markdown("""
    #### 📈 Try the Tutorials
    Interactive step-by-step demonstrations
    of Level A, B, and C with synthetic data.

    *Navigate to any* **Demo** *page in the sidebar.*
    """)

with col3:
    st.markdown("""
    #### ℹ️ About This Tool
    Built with Streamlit and Python. All data is
    synthetic — safe for educational use.

    *Developed by Harshvardhan Modh.*
    """)

st.markdown("---")
st.caption("**Disclaimer:** All data shown is synthetic/hypothetical, generated from pharmacokinetic and dissolution mathematical models for educational purposes only. No real experimental data is included.")
