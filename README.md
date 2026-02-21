# IVIVC Level Selection Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B.svg)](https://streamlit.io)

> **Interactive decision tool and tutorial for In Vitro–In Vivo Correlation (IVIVC) methodology. Helps pharmaceutical scientists choose the appropriate IVIVC level (A, B, or C) and demonstrates each with entirely synthetic data.**

**Disclaimer:** All data shown is synthetic/hypothetical, generated from pharmacokinetic and dissolution mathematical models for methodological demonstration purposes only. No real experimental data is included.

---

## Live Demo

🚀 **[Launch the App](https://ivivc-level-selector.streamlit.app)** *(Streamlit Community Cloud)*

---

## What Does This Tool Do?

### 1. 🔍 Level Selector — Interactive Questionnaire
Answer 6 scientifically-grounded questions about your project to receive a personalized recommendation:

- **Primary regulatory goal** (biowaiver, dissolution specs, screening)
- **In vivo data availability** (full profiles, summary parameters, limited data)
- **Number of formulations** tested in vivo
- **Dosage form type** (ER oral, depot injectable, transdermal)
- **Reference data availability** (IV bolus, IR/solution, none)
- **BCS classification** of the drug substance

Output includes a recommended IVIVC level with confidence score, reasoning, and regulatory references.

### 2. 📈 Level A Demo — Point-to-Point Correlation
Full 6-step interactive tutorial:

1. **In Vitro Dissolution** — First-order model with adjustable rate constants
2. **In Vivo PK Profiles** — 1-compartment oral model (BCS Class II)
3. **Deconvolution** — Wagner-Nelson method to extract fraction absorbed
4. **Level A Correlation** — % Dissolved vs % Absorbed (pooled across formulations)
5. **%PE Validation** — FDA criteria (mean ≤ 10%, individual ≤ 15%)
6. **External Prediction** — "What-if" slider to predict PK for new formulations

### 3. 📊 Level B Demo — Statistical Moment Comparison
- MDT vs MRT correlation with regression analysis
- **Pathological example**: Two formulations with identical MDT but different dissolution profiles and PK behavior
- Clear explanation of why Level B alone is insufficient for regulatory submissions

### 4. 📉 Level C Demo — Single-Point Correlations
- Interactive parameter selector (8 in vitro × 3 in vivo = 24 possible pairs)
- Full R² heatmap with slope direction indicators
- Interactive f1/f2 dissolution similarity calculator
- n=2 vs n=3 formulations comparison (why ≥3 matters)

---

## IVIVC Levels at a Glance

| Level | Definition | Correlation Type | Regulatory Value |
|:---:|:---|:---|:---|
| **A** | Point-to-point relationship between dissolution and absorption | Time-course mapping | ⭐⭐⭐ Highest — enables biowaiver |
| **B** | Statistical moment comparison (MDT vs MRT) | Summary parameter | ⭐ Limited — single metric |
| **C** | Single-point correlation between dissolution and PK parameters | Individual parameter pairs | ⭐⭐ Useful for formulation screening |

---

## Synthetic Data Scenarios

### Level A: Extended-Release Oral Tablet
- **Drug:** "Compound Y" — BCS Class II, 1-compartment PK (ke = 0.10 h⁻¹)
- **Formulations:** F1 (Fast), F2 (Medium), F3 (Slow) + IR reference
- **Model:** First-order dissolution → analytical 1-compartment oral PK
- **Timeframe:** 0–24 hours

### Level C: PLGA Microsphere Depot
- **Scenario:** Hypothetical PLGA depot (IM injection), 3 formulations (Low/Medium/High MW polymer)
- **Models:** Weibull dissolution + bi-exponential depot PK
- **Timeframe:** 0–30 days

---

## Quick Start

### Local Installation

```bash
# Clone the repository
git clone https://github.com/Harsh9005/ivivc-level-selector.git
cd ivivc-level-selector

# Install dependencies
pip install -r requirements.txt

# Launch the app
streamlit run app.py
```

### Requirements
- Python 3.8+
- streamlit ≥ 1.28
- numpy, scipy, plotly, pandas, matplotlib

---

## Project Structure

```
ivivc-level-selector/
├── app.py                          # Main Streamlit entry point
├── pages/
│   ├── 1_🏠_Home.py                # IVIVC overview and introduction
│   ├── 2_🔍_Level_Selector.py      # Interactive decision questionnaire
│   ├── 3_📈_Level_A_Demo.py        # Level A deconvolution tutorial
│   ├── 4_📊_Level_B_Demo.py        # Level B moment comparison tutorial
│   └── 5_📉_Level_C_Demo.py        # Level C single-point correlation tutorial
├── utils/
│   ├── synthetic_data.py           # All synthetic data generation
│   ├── pk_models.py                # PK model functions
│   ├── dissolution_models.py       # Dissolution model functions
│   ├── deconvolution.py            # Wagner-Nelson deconvolution
│   ├── ivivc_calculations.py       # Level A/B/C correlation computations
│   └── plotting.py                 # Plotly figure generation
├── .streamlit/config.toml          # Theme configuration
├── requirements.txt
├── LICENSE                         # MIT
└── README.md                       # This file
```

---

## Key Mathematical Models

| Component | Method |
|:---|:---|
| Dissolution (oral) | First-order: `F(t) = F_max × (1 − e^{−kt})` |
| Dissolution (depot) | Weibull with burst: `F(t) = burst + F_max(1 − e^{−(t/τ)^β})` |
| PK (oral) | 1-compartment: `C(t) = (D·ka)/(Vd·(ka−ke)) × [e^{−ke·t} − e^{−ka·t}]` |
| PK (depot) | Bi-exponential: `C(t) = A₁e^{−α₁t}(1−e^{−ka·t}) + A₂e^{−α₂t}` |
| Deconvolution | Wagner-Nelson: `Fa(t) = [C(t) + ke·AUC(0,t)] / [ke·AUC(0,∞)]` |
| Level A | Linear regression: % Dissolved vs % Absorbed |
| Level B | MDT vs MRT comparison |
| Level C | Single-point regression: scipy.stats.linregress |
| Validation | %PE = (Predicted − Observed) / Observed × 100 |
| f1/f2 | FDA/EMA standard dissolution similarity factors |

---

## Regulatory Context

This tool is based on methodologies described in:

- **FDA Guidance (1997):** Extended Release Oral Dosage Forms — Development, Evaluation, and Application of IVIVC
- **EMA Guideline (2014):** Quality of Oral Modified Release Products
- **USP <1088>:** In Vitro and In Vivo Evaluation of Dosage Forms
- **ICH Q8(R2):** Pharmaceutical Development

---

## Related Project

📊 **[Level C IVIVC Visualization Framework](https://github.com/Harsh9005/ivivc-level-c-viz)** — Publication-quality static visualizations of Level C IVIVC methodology with synthetic PLGA depot data.

---

## Citation

If you use this tool in your work:

```bibtex
@software{modh2025ivivc_selector,
  author = {Modh, Harshvardhan},
  title = {IVIVC Level Selection Framework},
  year = {2025},
  url = {https://github.com/Harsh9005/ivivc-level-selector},
  note = {Interactive Streamlit dashboard with synthetic data}
}
```

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <i>Developed at the National University of Singapore, Department of Pharmacy and Pharmaceutical Sciences</i>
</p>
