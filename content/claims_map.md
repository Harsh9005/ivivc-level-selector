# Claims → Reference Map (Phase 2A)

Every citable scientific/regulatory claim in the app, with the page it appears on
and the reference key(s) it should map to. Reference keys are filled + verified in
Phase 2B (`references.json`). **No claim ships with an unverified citation; no
reference is reconstructed from memory** (per project citation rules: Consensus
discovery → scite/refchecker verification).

Legend: page codes — H=Home, LS=Level Selector, A=Level A, B=Level B, C=Level C.

## General IVIVC concept & regulatory framework
| # | Claim | Pages | Candidate ref key(s) |
|---|---|---|---|
| G1 | IVIVC = predictive mathematical relationship between in vitro dissolution and in vivo response (bioavailability/plasma conc) | H, LS | fda_ivivc_1997, usp_1088 |
| G2 | IVIVC can reduce/replace bioequivalence studies and support **biowaivers** for formulation/manufacturing changes | H, LS | fda_ivivc_1997, fda_supac_mr_1997 |
| G3 | Three correlation levels (A/B/C) defined by the type of relationship | H, LS | fda_ivivc_1997, usp_1088 |
| G4 | IVIVC supports **dissolution specification setting** (clinically relevant specs) | H, LS, C | fda_ivivc_1997 |
| G5 | IVIVC supports **QbD** (linking CQAs to clinical outcomes) | H | ich_q8r2 |
| G6 | Post-approval (SUPAC-MR) changes supported by IVIVC/dissolution | LS | fda_supac_mr_1997 |

## Level A (point-to-point) & deconvolution
| # | Claim | Pages | Candidate ref key(s) |
|---|---|---|---|
| A1 | Level A = point-to-point correlation of entire dissolution vs entire absorption; highest regulatory value; only level that predicts the full plasma profile | H, LS, A | fda_ivivc_1997 |
| A2 | **Wagner–Nelson** extracts fraction absorbed Fa from plasma data using only ke; assumes 1-compartment; needs no IV reference | A, LS | wagner_nelson_1963 |
| A3 | **Loo–Riegelman** deconvolution for 2-compartment models (requires IV data) | (A/LS context) | loo_riegelman_1968 |
| A4 | Numerical/model-independent deconvolution (most rigorous; uses unit impulse / IV reference) | LS, A | langenbucher_1982_or_equiv |
| A5 | FDA Level A internal predictability: **mean \|%PE\| ≤ 10%** for Cmax & AUC; **individual ≤ 15%** | A, LS | fda_ivivc_1997 |
| A6 | External validation recommended (formulation not used in model development) | LS | fda_ivivc_1997 |

## BCS
| # | Claim | Pages | Candidate ref key(s) |
|---|---|---|---|
| BCS1 | BCS classifies drugs into 4 classes by solubility & permeability | LS | amidon_bcs_1995 |
| BCS2 | Dissolution rate-limited absorption is typical for **BCS Class II** → best IVIVC candidate | A, LS | amidon_bcs_1995, fda_ivivc_1997 |
| BCS3 | BCS Class I rarely needs IVIVC (dissolution not rate-limiting) | LS | fda_bcs_biowaiver, amidon_bcs_1995 |
| BCS4 | Class III (permeability-limited) & IV make IVIVC challenging | LS | amidon_bcs_1995 |

## Level B (statistical moments)
| # | Claim | Pages | Candidate ref key(s) |
|---|---|---|---|
| B1 | Level B compares **MDT vs MRT** (summary moments); cannot predict plasma profile; limited regulatory value | H, LS, B | fda_ivivc_1997 |
| B2 | **MRT = AUMC/AUC** (statistical moment theory) | B | yamaoka_1978 |
| B3 | MDT = mean dissolution time (first moment of the dissolution curve) | B | (textbook/USP) brockmeier_or_usp1088 |
| B4 | Level B's key weakness: different profiles can share the same MDT/MRT → can be misleading | H, B | fda_ivivc_1997, cardot_ivivc_review |

## Level C (single-point) & f1/f2
| # | Claim | Pages | Candidate ref key(s) |
|---|---|---|---|
| C1 | Level C = single-point correlation; useful for formulation screening & mechanistic insight | H, LS, C | fda_ivivc_1997 |
| C2 | Multiple Level C correlations (across several time points) | (H/LS context) | fda_ivivc_1997 |
| C3 | **f2 similarity factor** ≥ 50 → similar (avg difference ≤ ~10%); **f1 difference factor** ≤ 15 → similar | C | moore_flanner_1996, fda_dissolution_ir_1997 |
| C4 | IVIVC generally requires **≥ 3 formulations** with different release rates (n=2 gives trivial R²=1) | LS, C | fda_ivivc_1997 |
| C5 | **Weibull** function models (depot) dissolution; burst + sustained phases for PLGA microsphere depots | C | langenbucher_1972_weibull, plga_lai_review |

## Models (methodological, lower citation priority)
| # | Claim | Pages | Candidate ref key(s) |
|---|---|---|---|
| M1 | First-order dissolution model F(t)=Fmax(1−e^{−kt}) | A, B | (kinetics textbook) — optional |
| M2 | 1-compartment oral PK model | A | (PK textbook) — optional |
| M3 | Bi-exponential depot PK | C | plga_lai_review — optional |

## Regulatory anchor documents (verify official URLs in Phase 2B)
- **fda_ivivc_1997** — FDA Guidance for Industry: *Extended Release Oral Dosage Forms: Development, Evaluation, and Application of In Vitro/In Vivo Correlations* (Sept 1997).
- **ema_mr_2014** — EMA: *Guideline on quality of oral modified release products* (EMA/CHMP/QWP/428693/2013, 2014).
- **usp_1088** — USP General Chapter **<1088>** *In Vitro and In Vivo Evaluation of Dosage Forms*.
- **ich_q8r2** — ICH **Q8(R2)** *Pharmaceutical Development*.
- **fda_dissolution_ir_1997** — FDA Guidance: *Dissolution Testing of Immediate Release Solid Oral Dosage Forms* (Aug 1997) — f2 method.
- **fda_supac_mr_1997** — FDA **SUPAC-MR** guidance (1997).
- **fda_bcs_biowaiver** — FDA Guidance: *Waiver of In Vivo BA/BE Studies … Based on a BCS* (current revision).

## Notes
- ~22 distinct references projected (7 regulatory + ~12-15 primary literature).
- Foundational papers (Wagner–Nelson 1963, Loo–Riegelman 1968, Amidon 1995, Moore–Flanner 1996, Langenbucher 1972, Yamaoka 1978) MUST be verified via Consensus + scite/refchecker / CrossRef — not asserted from memory.
- Model claims (M1–M3) are standard methodology; cite only if a clean source is verified, else leave uncited (they're clearly framed as the app's synthetic model choices).
