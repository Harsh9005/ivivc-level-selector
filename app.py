"""
IVIVC Level Selection Dashboard
================================
Interactive decision tool and tutorial for In Vitro–In Vivo Correlation
methodology. Helps pharmaceutical scientists choose the appropriate
IVIVC level (A, B, or C) and demonstrates each with synthetic data.

All data is synthetic/hypothetical for educational purposes only.
No real experimental data is included.

Author: Harshvardhan Modh
Affiliation: National University of Singapore
License: MIT
"""

import streamlit as st

st.set_page_config(
    page_title="IVIVC Level Selector",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar branding
st.sidebar.markdown("""
# 💊 IVIVC Framework

**Interactive Decision Tool & Tutorial**

Navigate using the pages above to:
- 🏠 Learn about IVIVC
- 🔍 Find your recommended level
- 📈 Try Level A demo
- 📊 Try Level B demo
- 📉 Try Level C demo

---
*All data is synthetic/hypothetical.*
""")

# Main page content (redirects to Home)
st.markdown("""
# Welcome to the IVIVC Level Selection Framework

Use the **sidebar** to navigate between pages, or start with:

1. **🏠 Home** — Learn about IVIVC levels
2. **🔍 Level Selector** — Find which level suits your project
3. **📈📊📉 Tutorials** — Interactive demonstrations of each level

---

> **Disclaimer:** All data shown is synthetic/hypothetical, generated from
> pharmacokinetic and dissolution mathematical models for educational
> purposes only. No real experimental data is included.
""")
