# IVIVC Level Selector v2 — Design Spec

**Date:** 2026-06-09
**Author:** Harshvardhan Modh (with Claude Code)
**Status:** Approved (design), pending spec review
**Repo:** https://github.com/Harsh9005/ivivc-level-selector
**Branch:** `feat/v2-stlite-cited-interactive`

---

## 1. Problem & Goals

The existing app is a scientifically solid, well-architected Streamlit multipage
educational tool for In Vitro–In Vivo Correlation (IVIVC) methodology, using
entirely synthetic data. It is currently deployed on **Streamlit Community
Cloud**, which **sleeps apps after ~7 days of inactivity** and forces a manual
"wake up." It also has shallow citations (regulatory docs name-dropped, no
verified inline references) and is demo-only (no user data input).

The user wants three things:

1. **Stay live with zero babysitting** — never sleeps, no manual intervention,
   ideally free. *(Highest priority — the explicit pain point.)*
2. **Highly informative + reliable + cited** — rigorous, verified citations
   throughout, researched via the `writing-orchestrator` skill's research +
   citation-verification discipline.
3. **Interactive "sessions"** — all four chosen: upload-your-own-data, save &
   share scenarios, guided walkthrough/quizzes, richer live widgets.

### Success criteria
- App is reachable 24/7 at a stable URL with **no sleep state** and **no manual
  redeploy/wake step ever required**.
- Every scientific claim that carries a citation maps to a **verified** source
  (DOI / exact regulatory document), with **no fabricated references** and **no
  use of the banned `semanticSearch` tool** for citations.
- A user can run a real Level A/B/C analysis **on their own data**, entirely in
  the browser, and share a scenario via URL.
- The scientific core has unit tests; each deployed build is smoke-tested in a
  real browser.

### Non-goals
- Not a regulatory-grade submission tool; it remains educational/illustrative.
- Not rewriting the science in JavaScript.
- Not building a backend/server, auth, or any data persistence on a server
  (all user data stays client-side).

---

## 2. Chosen Approach (and rejected alternatives)

**Develop in the existing Streamlit Python codebase; deploy the same code as a
static bundle via stlite (Pyodide/WebAssembly) to GitHub Pages.**

- Keeps ~all existing Python; fast local dev loop (`streamlit run`); the
  "stay-live" win comes from the deployment layer, not a rewrite.

**Rejected:**
- *Build directly in stlite* — slow iteration, awkward debugging.
- *Rewrite in HTML/JS (Plotly.js)* — discards good code, large effort.
- *Always-on managed Streamlit host* — free tiers (HF Spaces, Render) also
  sleep; "never sleeps" then means recurring cost.
- *Keep-alive cron pinger on Streamlit Cloud* — fragile, against the spirit of
  the platform, still sleeps after 7 days inactivity. Rejected.

### stlite feasibility (verified 2026-06-09 against stlite docs)
- ✅ Multipage apps via `entrypoint` + `pages/*.py`.
- ✅ numpy / scipy / pandas (scipy is prebuilt for Pyodide).
- ✅ plotly (caveat: do not combine with altair — app does not use altair).
- ✅ Static GitHub Pages hosting by design (runs fully in-browser).
- ⚠️ **To verify in Phase 0 spike:** `st.file_uploader` and `st.query_params`
  in-browser (both standard; expected to work but not explicitly confirmed in
  docs).
- ⚠️ Known constraints to design around: significant **first-load time**
  (Pyodide bootstrap); `time.sleep()` is a no-op (use `asyncio.sleep`);
  binary-extension packages not built for Pyodide cannot install (none needed);
  `st.bokeh_chart` unsupported (app uses plotly).
- ✅ `matplotlib` confirmed unused in the codebase → drop from requirements to
  reduce first-load size.

---

## 3. Architecture

### 3.1 Components (each with one clear purpose)

```
ivivc-level-selector/
├── app.py                       # Streamlit entrypoint (unchanged role)
├── pages/                       # Multipage UI (existing + new)
│   ├── 1_🏠_Home.py             # + inline citations, evidence callouts
│   ├── 2_🔍_Level_Selector.py   # + query-param save/share, citations
│   ├── 3_📈_Level_A_Demo.py     # + richer widgets, citations
│   ├── 4_📊_Level_B_Demo.py     # + richer widgets, citations
│   ├── 5_📉_Level_C_Demo.py     # + richer widgets, citations
│   ├── 6_🧪_Analyze_Your_Data.py # NEW — upload-your-own-data mode
│   ├── 7_🧭_Guided_Mode.py      # NEW — guided walkthrough + quizzes
│   └── 8_📚_References.py        # NEW — verified reference library
│   # Existing pages use emoji filename prefixes (Streamlit derives nav
│   # label/order from the filename); v2 KEEPS this convention. Phase 0 MUST
│   # confirm stlite bundles/serves non-ASCII (emoji) filenames cleanly; if not,
│   # fall back to ASCII filenames + st.Page title overrides.
├── utils/                       # Science core (pure functions, testable)
│   ├── dissolution_models.py    # (existing) dissolution models + f1/f2 + MDT (compute_f1_f2, compute_mdt, compute_de)
│   ├── pk_models.py             # (existing) PK models + moments (compute_mrt, compute_auc, compute_aumc)
│   ├── deconvolution.py         # (existing) Wagner–Nelson (wagner_nelson)
│   ├── ivivc_calculations.py    # (existing) Level A/C correlation, %PE, Level C matrix — NOT Level B / f1f2
│   ├── synthetic_data.py        # (existing)
│   ├── plotting.py              # (existing)
│   ├── data_io.py               # NEW — CSV parse/validate for upload mode
│   ├── session_state.py         # NEW — encode/decode scenario <-> query params
│   └── citations.py             # NEW — load references.json, render inline cites
├── content/
│   ├── references.json          # NEW — verified citation corpus (single source of truth)
│   └── claims_map.md            # NEW — claim -> reference traceability (dev artifact)
├── tests/                       # NEW — pytest unit tests for the science core
├── deploy/
│   ├── index.html               # NEW — stlite boot + mount config + loading screen
│   └── build_stlite.py          # NEW — assembles files dict / static bundle
├── .github/workflows/
│   └── deploy.yml               # NEW — build + publish to GitHub Pages on push to main
├── requirements.txt             # drop matplotlib; pin plotly/scipy for Pyodide
└── README.md                    # updated: new URL, architecture, citation policy
```

### 3.2 Data flow
- **Demo pages:** `synthetic_data` → `*_models` → `deconvolution`/`ivivc_calculations`
  → `plotting` → Streamlit widgets. (Unchanged core; widgets enriched.)
- **Upload mode:** user CSV → `data_io` (parse + validate) → same
  `deconvolution`/`ivivc_calculations` functions → `plotting`. **No data leaves
  the browser** (stlite runs client-side).
- **Save/share:** widget state ⇄ `session_state` ⇄ `st.query_params` (URL is the
  scenario). On load, query params hydrate widget defaults.
- **Citations:** `references.json` (verified corpus) → `citations.py` renders
  inline numbered markers + the References page. Claims reference entries by key.

### 3.3 Deployment flow
1. Push to `main`.
2. GitHub Actions (`deploy.yml`) runs `build_stlite.py` → produces a static
   `dist/` (index.html + bundled app files, or files fetched at runtime).
3. Action publishes `dist/` to GitHub Pages → `https://harsh9005.github.io/ivivc-level-selector`.
4. Result: **always-on, $0, never sleeps, zero manual steps.**

> **CLIENT-ONLY INVARIANT (load-bearing — this is what makes "never sleeps" true).**
> There is no server process anywhere. The page is static files on a CDN and the
> entire app runs in the browser via WebAssembly. Therefore **no feature may
> depend on a server round-trip / API call.** Every asset (`references.json`,
> example datasets, app `.py` files) is a **same-origin static file** served by
> GitHub Pages and either bundled into the mount or fetched from the same Pages
> origin at boot. Any "fetched at runtime" file in this spec means *same-origin
> static fetch*, never a backend. Phase 2/3 implementers must not introduce an
> external API; user data in upload mode stays in the browser.

---

## 4. Cited Evidence Layer (Requirement 2)

### Research + verification pipeline (faithful to user's CRITICAL citation rules)
1. **Discover** primary literature with **Consensus** (`consensus` MCP) — the
   approved academic source. **`semanticSearch` is banned** for citations.
2. **Extract exact metadata** (authors, title, journal, year, DOI) from source
   output — never reconstruct from memory.
3. **Verify** each reference independently via **scite** MCP and the
   **refchecker** MCP; check for retractions/corrections.
4. Persist to `content/references.json`: `{key, authors, title, journal, year,
   doi, url, verified: true/false, verification_source, claim_keys[]}`.
5. **Citation QC pass** before ship: every reference resolves, no fabrications,
   each inline claim maps to a verified entry (`claims_map.md`).

> The Phase 2 plan MUST build `claims_map.md` (claim → reference key) **alongside
> the writing**, so a reference *count* (e.g., "37 refs") can never substitute for
> claim *coverage*. "Verified citations" is success criterion #2 and a CRITICAL
> user rule — coverage is the bar, not volume.

The `writing-orchestrator` skill is used for its **research + citation-quality
discipline**, not its DOCX/manuscript output stage.

### Citation topic scope (~30–40 verified references)
IVIVC definition/purpose; Level A point-to-point + deconvolution methods
(Wagner–Nelson, Loo–Riegelman, numerical/model-dependent vs independent);
Level B moment analysis (MDT/MRT) and **why it is regulatorily insufficient**;
Level C single-point + **multiple Level C**; BCS framework; f1/f2 dissolution
similarity factors and their limits; the dissolution & PK model forms used;
long-acting/PLGA depot IVIVC challenges; regulatory basis (FDA 1997 ER IVIVC
guidance, EMA 2014 modified-release guideline, USP <1088>, ICH Q8(R2));
biowaiver / SUPAC-MR.

### Surfacing in the app
- Inline numbered citation markers on claims across all content pages.
- A dedicated **References** page: sortable/filterable, DOI links, "verified"
  badges, grouped by topic.
- Expandable **"Evidence & why it matters"** callouts on key claims.

---

## 5. Interactivity (Requirement 3 — all four)

### 5.1 Upload-your-own-data mode (`6_Analyze_Your_Data.py` + `utils/data_io.py`)
- Inputs: dissolution CSV (`time`, one `%released` column per formulation) and
  PK CSV (`time`, one `conc` column per formulation). Deconvolution path is
  pinned in the Phase 3 plan: Wagner–Nelson (`wagner_nelson(times, conc, ke)`)
  needs only `ke` (no IV reference required, per its docstring); the numerical
  path needs an impulse response. Upload mode collects whichever the chosen path
  requires. Downloadable templates + example datasets included.
- Runs the **real** existing science on user data: Wagner–Nelson deconvolution,
  Level A regression + %PE (FDA criteria), Level B MDT/MRT, Level C heatmap +
  f1/f2.
- Robust validation with clear, friendly error messages (missing columns,
  non-monotonic time, unit hints). Entirely client-side (privacy by design).

### 5.2 Save & share scenarios (`utils/session_state.py`)
- Encode every relevant widget value into `st.query_params` (compact, URL-safe).
- "Copy shareable link" button; on load, hydrate widgets from the URL.
- Curated **example-scenario presets** (e.g., "Fast vs slow ER tablet",
  "PLGA depot Level C").

### 5.3 Guided walkthrough + quizzes (`7_Guided_Mode.py`)
- Step-by-step guided path through each level: concept → worked example →
  short self-check **MCQ** with instant feedback and explanation.
- In-session progress tracking (`st.session_state`); no server, no accounts.

### 5.4 Richer live widgets (in existing demo pages)
- More real-time controls + comparison overlays: toggle formulations on/off,
  predicted-vs-observed overlay, live %PE recompute, adjustable BCS/ke/ka,
  fraction-absorbed build-up. Avoid `time.sleep` (stlite no-op) — use reactive
  recompute or `asyncio.sleep`.

---

## 6. Testing & Verification ("would a staff engineer approve")
- **Unit tests (`tests/`, pytest):** the science core currently has **no
  tests**. Add tests with known analytical checks for: Wagner–Nelson
  deconvolution, Level A regression + %PE, f1/f2 factors, MDT/MRT moments,
  CSV parse/validate, and scenario encode/decode round-trip.
- **In-browser smoke test:** after each stlite build, load in a real browser
  (preview/chrome tools); verify pages render, plotly draws, upload + share work,
  no console errors. Capture screenshot proof.
- **Citation QC:** automated pass that every `references.json` entry resolves and
  every inline claim references a verified entry.

---

## 7. Phasing (each phase ends in a verified, live deploy)
- **Phase 0 — Feasibility spike:** mount current app in stlite; confirm scipy +
  plotly + multipage in-browser. *(de-risk)* **Explicit pass/fail gates + named
  fallbacks** (each capability is a hard gate before the feature that needs it):
  - *plotly renders & scipy/numpy compute in-browser* — **hard gate**; no
    fallback (if this fails the whole stlite approach is wrong → escalate).
  - *multipage nav works* — gate; fallback = single-page app with a radio/selectbox
    page switcher.
  - *emoji (non-ASCII) filenames bundle/serve cleanly* — gate; fallback = ASCII
    filenames + `st.Page` title overrides.
  - *`st.file_uploader` works in-browser* — gate for §5.1 upload mode; **fallback
    = paste-CSV-into-`st.text_area`** (same `data_io` parser downstream).
  - *`st.query_params` round-trips* — gate for §5.2 save/share; **fallback =
    encode scenario to a copyable code string the user pastes into a "Load
    scenario" box** (no URL dependency).
  Phase 0 exits only when every gate is either PASS or has its fallback chosen
  and recorded; record results in the Phase 0 plan/notes.
- **Phase 1 — Re-platform + auto-deploy:** stlite bundle + GitHub Actions →
  **permanently live on GitHub Pages.** *(solves the #1 pain immediately)*
- **Phase 2 — Cited evidence layer:** research → verify → `references.json` →
  References page + inline citations + evidence callouts.
- **Phase 3 — Interactivity:** the four features; add unit tests; redeploy.

Each phase gets its own spec→plan→implement cycle as needed; this document is
the umbrella vision. Implementation begins with Phase 0 + Phase 1.

---

## 8. Open decisions (resolved defaults)
- **URL:** default to `harsh9005.github.io/ivivc-level-selector` (GitHub Pages).
  Custom domain can be added later. Streamlit Cloud app may remain as an
  optional mirror or be retired.
- **First-load UX:** branded loading screen + dependency trimming accepted as the
  cost of "never sleeps." If load time proves unacceptable in Phase 0, revisit.

---

## 9. Risks & mitigations
| Risk | Mitigation |
|---|---|
| stlite first-load too slow | Trim deps (drop matplotlib), pin versions, loading screen; measure in Phase 0 |
| `file_uploader` / `query_params` unsupported in stlite | Phase 0 hard gate; fallbacks = paste-CSV `text_area` / copyable scenario-code string |
| Emoji / non-ASCII page filenames break stlite bundling or static fetch | Verify in Phase 0; fallback = ASCII filenames + `st.Page` title overrides |
| Citation fabrication / unreliable refs | Consensus + scite + refchecker verification; QC gate; no semanticSearch |
| plotly/altair version clash in Pyodide | App uses plotly only; pin compatible versions |
| Large synthetic computations slow in-browser | Keep timeframes/point counts modest; cache with `st.cache_data` |
