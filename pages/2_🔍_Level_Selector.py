"""
Page 2: Level Selector — Interactive Decision Questionnaire
"""

import streamlit as st

st.set_page_config(page_title="Level Selector — IVIVC", page_icon="🔍", layout="wide")

st.title("🔍 IVIVC Level Selector")
st.markdown("### Answer 6 questions to find the most appropriate IVIVC level for your project")
st.markdown("---")

# ─── Question 1 ─────────────────────────────────────────────────────────────
st.subheader("1. What is your primary regulatory goal?")
q1 = st.radio(
    "Select the main objective:",
    [
        "Biowaiver for formulation/manufacturing changes",
        "Setting clinically relevant dissolution specifications",
        "Formulation screening during development",
        "Mechanistic understanding of release–PK relationship",
    ],
    key="q1",
    index=None,
)

# ─── Question 2 ─────────────────────────────────────────────────────────────
st.subheader("2. What in vivo data is available?")
q2 = st.radio(
    "Select data availability:",
    [
        "Full plasma concentration-time profiles (≥8 timepoints per subject)",
        "Summary PK parameters only (AUC, Cmax, Tmax, MRT)",
        "Limited data (fewer than 6 timepoints per subject)",
    ],
    key="q2",
    index=None,
)

# ─── Question 3 ─────────────────────────────────────────────────────────────
st.subheader("3. How many formulations were tested in vivo?")
q3 = st.radio(
    "Select number of formulations:",
    [
        "≥ 3 formulations",
        "2 formulations",
        "1 formulation + literature/reference data",
    ],
    key="q3",
    index=None,
)

# ─── Question 4 ─────────────────────────────────────────────────────────────
st.subheader("4. What is the dosage form type?")
q4 = st.radio(
    "Select dosage form:",
    [
        "Extended-release oral tablet/capsule",
        "Depot injectable (PLGA, ISFI, microspheres)",
        "Transdermal patch",
        "Other modified-release system",
    ],
    key="q4",
    index=None,
)

# ─── Question 5 ─────────────────────────────────────────────────────────────
st.subheader("5. Is IV or IR reference data available?")
q5 = st.radio(
    "Reference data for deconvolution:",
    [
        "Yes — IV bolus data available",
        "Yes — Oral IR/solution data available",
        "No reference data available",
    ],
    key="q5",
    index=None,
)

# ─── Question 6 ─────────────────────────────────────────────────────────────
st.subheader("6. What is the BCS classification of the drug?")
q6 = st.radio(
    "Biopharmaceutics Classification System:",
    [
        "Class I — High solubility, High permeability",
        "Class II — Low solubility, High permeability",
        "Class III — High solubility, Low permeability",
        "Class IV — Low solubility, Low permeability",
    ],
    key="q6",
    index=None,
)

st.markdown("---")

# ─── Scoring Logic ───────────────────────────────────────────────────────────
if st.button("🎯 Get Recommendation", type="primary", use_container_width=True):

    if None in [q1, q2, q3, q4, q5, q6]:
        st.warning("⚠️ Please answer all 6 questions before getting a recommendation.")
    else:
        # Initialize scores
        score_A = 0
        score_B = 0
        score_C = 0

        reasons_A = []
        reasons_B = []
        reasons_C = []
        caveats = []

        # ── Q1: Regulatory goal ──
        if "Biowaiver" in q1:
            score_A += 4
            reasons_A.append("Biowaiver applications strongly favor Level A (FDA guidance)")
        elif "dissolution specifications" in q1:
            score_A += 2
            score_C += 2
            reasons_A.append("Dissolution spec setting benefits from Level A")
            reasons_C.append("Level C can support spec setting for individual parameters")
        elif "screening" in q1:
            score_C += 3
            reasons_C.append("Formulation screening is the primary use case for Level C")
        elif "Mechanistic" in q1:
            score_A += 2
            score_C += 2
            reasons_A.append("Level A provides the most mechanistic detail")
            reasons_C.append("Level C offers mechanistic insight for specific parameter pairs")

        # ── Q2: Data availability ──
        if "Full plasma" in q2:
            score_A += 3
            reasons_A.append("Full PK profiles enable deconvolution for Level A")
        elif "Summary PK" in q2:
            score_B += 2
            score_C += 2
            reasons_B.append("Summary parameters are sufficient for Level B (MDT vs MRT)")
            reasons_C.append("Summary PK parameters are ideal for Level C correlations")
            caveats.append("Without full PK profiles, Level A deconvolution is not feasible")
        elif "Limited data" in q2:
            score_C += 3
            reasons_C.append("Level C works with minimal data availability")
            caveats.append("Limited data restricts analysis to Level C only")

        # ── Q3: Number of formulations ──
        if "≥ 3" in q3:
            score_A += 2
            score_C += 1
            reasons_A.append("≥3 formulations provide robust validation for Level A")
        elif q3 == "2 formulations":
            score_A += 1
            score_C += 1
            caveats.append("With only 2 formulations: Level A has limited internal validation; Level C gives trivial R²=1.00 (2 points always define a perfect line)")
        elif "1 formulation" in q3:
            score_A += 1
            score_C += 1
            caveats.append("Single formulation limits validation — external data needed for Level A; Level C requires ≥3 formulations for meaningful R²")

        # ── Q4: Dosage form ──
        if "oral" in q4.lower():
            score_A += 2
            reasons_A.append("Extended-release oral forms have the most established Level A methodology (FDA 1997 guidance)")
        elif "Depot" in q4:
            score_C += 2
            score_A += 1
            reasons_C.append("Depot injectables often use Level C due to complex absorption mechanisms")
            caveats.append("Depot formulations have multi-phasic absorption that complicates Level A deconvolution")
        elif "Transdermal" in q4:
            score_A += 2
            reasons_A.append("Transdermal systems can achieve Level A with appropriate deconvolution")
        else:
            score_A += 1
            score_C += 1

        # ── Q5: Reference data ──
        if "IV bolus" in q5:
            score_A += 3
            reasons_A.append("IV reference enables numerical deconvolution (most rigorous Level A approach)")
        elif "IR/solution" in q5:
            score_A += 2
            reasons_A.append("Oral IR data enables Wagner-Nelson deconvolution (assumes 1-compartment model)")
            caveats.append("Wagner-Nelson assumes 1-compartment PK — verify with appropriate model selection")
        elif "No reference" in q5:
            score_C += 2
            score_B += 1
            caveats.append("Without reference data, deconvolution (Level A) is not feasible")
            reasons_C.append("Level C does not require reference data")

        # ── Q6: BCS class ──
        if "Class I" in q6:
            score_C += 1
            caveats.append("BCS Class I drugs (high sol/high perm) rarely need IVIVC — dissolution is usually not rate-limiting")
        elif "Class II" in q6:
            score_A += 2
            reasons_A.append("BCS Class II is the best candidate for IVIVC (dissolution is rate-limiting for absorption)")
        elif "Class III" in q6:
            score_C += 1
            caveats.append("BCS Class III (permeability-limited) makes IVIVC challenging — dissolution may not predict absorption")
        elif "Class IV" in q6:
            score_C += 1
            caveats.append("BCS Class IV drugs are the most challenging for IVIVC — both dissolution and permeability are limiting")

        # ── Determine recommendation ──
        scores = {'Level A': score_A, 'Level B': score_B, 'Level C': score_C}
        max_score = max(scores.values())
        recommended = max(scores, key=scores.get)

        # Confidence
        total = sum(scores.values())
        if total > 0:
            confidence_pct = (max_score / total) * 100
        else:
            confidence_pct = 33

        if confidence_pct >= 55:
            confidence = "🟢 Strong"
        elif confidence_pct >= 40:
            confidence = "🟡 Moderate"
        else:
            confidence = "🔴 Weak"

        # ── Display Results ──
        st.markdown("---")
        st.header("📋 Recommendation")

        # Score bars
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Level A Score", f"{score_A}")
            st.progress(score_A / max(max_score, 1))
        with col2:
            st.metric("Level B Score", f"{score_B}")
            st.progress(score_B / max(max_score, 1))
        with col3:
            st.metric("Level C Score", f"{score_C}")
            st.progress(score_C / max(max_score, 1))

        st.markdown("---")

        # Main recommendation
        level_emoji = {'Level A': '📈', 'Level B': '📊', 'Level C': '📉'}
        st.success(f"""
        ### {level_emoji[recommended]} Recommended: **{recommended}**

        **Confidence:** {confidence} ({confidence_pct:.0f}%)
        """)

        # Reasons
        reasons_map = {'Level A': reasons_A, 'Level B': reasons_B, 'Level C': reasons_C}
        reasons = reasons_map.get(recommended, [])
        if reasons:
            st.markdown("#### Why this level?")
            for r in reasons:
                st.markdown(f"- ✅ {r}")

        # Caveats
        if caveats:
            st.markdown("#### ⚠️ Key Considerations")
            for c in caveats:
                st.markdown(f"- {c}")

        # Alternative
        sorted_levels = sorted(scores, key=scores.get, reverse=True)
        if len(sorted_levels) > 1:
            alt = sorted_levels[1]
            alt_reasons = reasons_map.get(alt, [])
            if scores[alt] > 0:
                with st.expander(f"Alternative: {alt} (score: {scores[alt]})"):
                    if alt_reasons:
                        for r in alt_reasons:
                            st.markdown(f"- {r}")

        # Navigation to demo
        st.markdown("---")
        demo_pages = {
            'Level A': '📈 Level A Demo',
            'Level B': '📊 Level B Demo',
            'Level C': '📉 Level C Demo',
        }
        st.info(f"👉 **Try the {recommended} tutorial** — navigate to **{demo_pages[recommended]}** in the sidebar to see a step-by-step demonstration with synthetic data.")

        # FDA guidance reference
        with st.expander("📚 Regulatory References"):
            st.markdown("""
            - **FDA Guidance (1997):** Extended Release Oral Dosage Forms — Development, Evaluation, and Application of IVIVC
            - **EMA Guideline (2014):** Quality of Oral Modified Release Products
            - **USP <1088>:** In Vitro and In Vivo Evaluation of Dosage Forms
            - **ICH Q8(R2):** Pharmaceutical Development — supports QbD approach with IVIVC

            **Key FDA criteria for Level A validation:**
            - Internal predictability: Mean |%PE| ≤ 10% for Cmax and AUC
            - Individual |%PE| ≤ 15% for each formulation
            - External validation recommended with a formulation not used in model development
            """)

st.markdown("---")
st.caption("**Disclaimer:** All data and recommendations are for educational purposes only. Regulatory submissions require validated IVIVC using real experimental data. Consult relevant FDA/EMA guidance documents for specific regulatory requirements.")
