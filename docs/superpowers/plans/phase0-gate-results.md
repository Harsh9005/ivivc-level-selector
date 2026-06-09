# Phase 0 — In-Browser Gate Results

**Date:** 2026-06-09
**Method:** `python3 deploy/build_stlite.py` → served `dist/` via `python3 -m http.server 8000` → loaded `http://localhost:8000/` in Chrome (chrome-devtools MCP). stlite `@stlite/browser@0.85.1`.
**Bundle:** 13 files embedded, 119,985 bytes `index.html`.

| Gate | Result | Evidence |
|---|---|---|
| **HARD: Plotly renders + scipy/numpy compute in-browser** | ✅ **PASS** | Level A page: correlation `R² = 0.9724`, `slope 1.029`, `p-value 8.37e-33` (← `scipy.stats.linregress`); Wagner–Nelson Fa computed; %PE table computed (Cmax mean \|%PE\| = 1.1% PASS, AUC 0.4% PASS). 6 Plotly figures rendered (dissolution, PK, deconvolution, correlation scatter, %PE bars, predicted PK). |
| **Multipage navigation** | ✅ **PASS** | Sidebar shows app/Home/Level Selector/Level A/B/C Demo; clicked Home → Level A Demo, URL routed to `/Level_A_Demo`, page recomputed + rendered. |
| **Emoji (non-ASCII) filenames** | ✅ **PASS** | All 5 emoji-prefixed pages load and render; emoji + LaTeX (Wagner–Nelson / %PE formulas) display. Files are embedded in the manifest (not fetched off disk), so no filename-encoding path exists. |
| **App renders cleanly / no console errors** | ✅ **PASS** | `list_console_messages(error,warn)` → none. |
| **numpy/pandas micropip conflict (feared in plan Task 1.3 note)** | ✅ **Did NOT occur** | App loaded and computed fully with default requirements `['numpy','scipy','plotly','pandas']`. No trim needed. |
| **First-load time** | ✅ Acceptable | Cold boot (Pyodide + scipy/plotly download) resolved well within the 90s overlay safety-net; loading screen shown during boot. Will be precisely measurable on the live Pages deploy; matplotlib already dropped to keep it lean. |
| **st.file_uploader** | ⏸ **Deferred to Phase 3 kickoff** | Standard stlite-supported widget; not needed until Phase 3 upload mode. Fallback if it ever fails: paste-CSV `st.text_area` (same `data_io` parser). |
| **st.query_params** | ⏸ **Deferred to Phase 3 kickoff** | Standard stlite-supported; not needed until Phase 3 save/share. Fallback: copyable scenario-code string. |

**Exit decision:** Hard gate PASS; all gates required for Phase 1 (re-platform + deploy) PASS. The two deferred gates are Phase-3-only features with documented fallbacks. **Proceed to Chunk 3 (auto-deploy).**

**Evidence screenshots (in this folder):**
- `phase0-evidence-01-home.png` — entrypoint page booted in stlite.
- `phase0-evidence-02-levelA.png` — full Level A tutorial computed + charted in-browser.
