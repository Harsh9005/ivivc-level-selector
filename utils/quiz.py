"""Pure curriculum + grading logic for the Guided Mode walkthrough.

Encodes a short, scientifically-vetted IVIVC learning path as data (5 lessons,
7 self-check MCQs) and provides stateless grading/scoring helpers. No streamlit,
no I/O — stdlib only — so it imports cleanly both locally and inside stlite's
Pyodide virtual FS.

Lesson bodies embed the app's CANONICAL inline citation markers (e.g. "[8]" for
Wagner–Nelson) so the guided content shares the same verified reference numbers
shown everywhere else in the app. The markers are derived from
``utils.citations.cite`` at import time, which means a typo'd citation key fails
loud (KeyError) rather than silently rendering the wrong number.
"""
from __future__ import annotations

from utils.citations import cite

# Resolve the canonical inline markers from the verified corpus. If any key were
# wrong, cite() would raise KeyError here at import — citations stay honest.
_FDA = cite("fda_ivivc_1997")               # "[1]"
_DISS_IR = cite("fda_dissolution_ir_1997")  # "[5]"
_WN = cite("wagner_nelson_1963")            # "[8]"
_LR = cite("loo_riegelman_1968")            # "[9]"
_BCS = cite("amidon_bcs_1995")              # "[10]"
_MOMENTS = cite("yamaoka_1978")             # "[12]"
_F2 = cite("shah_f2_1998")                  # "[13]"
_PLGA = cite("andhariya_2019")              # "[14]"


LESSONS: list[dict] = [
    {
        "id": "what-is-ivivc",
        "title": "1 · What is IVIVC?",
        "body": (
            "**In Vitro–In Vivo Correlation (IVIVC)** is a predictive mathematical "
            "relationship between an *in vitro* property of a dosage form (usually the "
            "dissolution profile) and a relevant *in vivo* response (usually plasma "
            "drug concentration or fraction absorbed). A validated IVIVC — especially "
            "**Level A** — can act as a surrogate for in vivo bioequivalence, "
            "supporting **biowaivers** and reducing the need for some bioequivalence "
            f"studies {_FDA}. Three correlation *levels* (A, B, C) are defined by how "
            f"much of the data they relate {_FDA}."
        ),
        "questions": [
            {
                "q": "What is the primary regulatory benefit of a validated Level A IVIVC?",
                "options": [
                    "It replaces all clinical safety trials",
                    "It can support a biowaiver, reducing the need for some bioequivalence studies",
                    "It measures a drug's toxicity",
                    "It is legally required for every drug product",
                ],
                "answer_index": 1,
                "explanation": (
                    "A validated IVIVC (especially Level A) can serve as a surrogate for "
                    "in vivo bioequivalence, supporting biowaivers for certain formulation "
                    f"or manufacturing changes {_FDA}. It does not replace safety trials or "
                    "measure toxicity."
                ),
            },
        ],
    },
    {
        "id": "level-a",
        "title": "2 · Level A — point-to-point",
        "body": (
            "**Level A** is a point-to-point correlation between the *entire* in vitro "
            "dissolution profile and the *entire* in vivo absorption profile. It is the "
            "most informative level and the only one that can predict a full plasma "
            "concentration–time profile. The in vivo fraction absorbed is recovered by "
            f"**deconvolution**: the **Wagner–Nelson** method {_WN} assumes a "
            "one-compartment model and needs no IV reference data, while the "
            f"**Loo–Riegelman** method {_LR} handles two-compartment drugs (and needs IV "
            "data). The model is validated by **% prediction error (%PE)**: FDA criteria "
            f"are mean |%PE| ≤ 10% (Cmax and AUC) and individual |%PE| ≤ 15% {_FDA}."
        ),
        "questions": [
            {
                "q": (
                    "Which method extracts the in vivo fraction absorbed from plasma data "
                    "assuming a one-compartment model, with no IV reference data needed?"
                ),
                "options": [
                    "Loo–Riegelman method",
                    "Wagner–Nelson method",
                    "f2 similarity factor",
                    "Higuchi model",
                ],
                "answer_index": 1,
                "explanation": (
                    f"Wagner–Nelson {_WN} uses only the elimination rate constant and a "
                    f"one-compartment assumption — no IV reference required. Loo–Riegelman {_LR} "
                    "is the two-compartment method and needs IV data."
                ),
            },
            {
                "q": "What are the FDA internal-predictability criteria for a Level A IVIVC?",
                "options": [
                    "Mean |%PE| ≤ 10% and individual |%PE| ≤ 15%",
                    "R² ≥ 0.99 only",
                    "f2 ≥ 50",
                    "Slope exactly 1.000",
                ],
                "answer_index": 0,
                "explanation": (
                    "FDA Level A internal validation requires mean absolute prediction error "
                    "≤ 10% for Cmax and AUC, with each individual formulation ≤ 15% "
                    f"{_FDA}."
                ),
            },
        ],
    },
    {
        "id": "level-b",
        "title": "3 · Level B — statistical moments",
        "body": (
            "**Level B** compares a statistical-moment summary of dissolution "
            "(**Mean Dissolution Time, MDT**) with one of the plasma curve "
            f"(**Mean Residence Time, MRT = AUMC/AUC**) {_MOMENTS}. Because it reduces "
            "each entire profile to a single number, Level B **cannot predict the plasma "
            "profile shape** and has the weakest regulatory standing — crucially, two "
            "very different dissolution profiles can share nearly the same MDT, so Level B "
            f"can rate genuinely different formulations as equivalent {_FDA}."
        ),
        "questions": [
            {
                "q": "Why is Level B generally insufficient on its own for a biowaiver?",
                "options": [
                    "It requires intravenous data",
                    "It collapses each profile to a single moment, so different profile shapes can look equivalent",
                    "It can only be used for injectables",
                    "It needs at least 10 formulations",
                ],
                "answer_index": 1,
                "explanation": (
                    f"Level B uses only summary moments (MDT vs MRT) {_MOMENTS}; different "
                    "time-course shapes can yield the same MDT, so it cannot distinguish them "
                    f"and cannot predict the plasma profile {_FDA}."
                ),
            },
        ],
    },
    {
        "id": "level-c",
        "title": "4 · Level C, f1/f2 & study design",
        "body": (
            "**Level C** correlates a single dissolution parameter (e.g., % released at a "
            "time point, dissolution efficiency) with a single PK parameter (e.g., AUC, "
            "Cmax) — useful for formulation screening. Dissolution-profile similarity is "
            "judged with the FDA/EMA **difference factor f1** and **similarity factor f2**: "
            "**f2 ≥ 50** means the profiles are similar (average difference ≤ ~10% across "
            f"time points), and f1 ≤ 15 indicates similarity {_F2}{_DISS_IR}. A meaningful "
            "Level C (and IVIVC generally) needs **at least 3 formulations** with different "
            "release rates — with only two formulations any correlation is trivially perfect "
            f"(R² = 1) {_FDA}. For complex products such as PLGA depot microspheres, "
            f"multiphasic/burst release makes correlation harder {_PLGA}."
        ),
        "questions": [
            {
                "q": "A dissolution similarity factor of f2 = 62 indicates that two profiles are…",
                "options": [
                    "Different (reject)",
                    "Similar",
                    "Identical at every point",
                    "Impossible — f2 cannot exceed 50",
                ],
                "answer_index": 1,
                "explanation": (
                    f"f2 ≥ 50 indicates the two dissolution profiles are similar (average "
                    f"difference ≤ ~10% across time points) {_F2}. f2 ranges up to 100 "
                    "(identical = 100)."
                ),
            },
            {
                "q": (
                    "What is the minimum number of formulations generally needed for a "
                    "meaningful Level C correlation?"
                ),
                "options": ["1", "2", "3", "6"],
                "answer_index": 2,
                "explanation": (
                    "At least 3 formulations with different release rates are needed; with "
                    f"only 2 points any line fits perfectly (trivial R² = 1) {_FDA}."
                ),
            },
        ],
    },
    {
        "id": "bcs-and-choosing",
        "title": "5 · BCS & choosing a level",
        "body": (
            "The **Biopharmaceutics Classification System (BCS)** groups drugs by aqueous "
            f"solubility and intestinal permeability into four classes {_BCS}. IVIVC is most "
            "successful for **BCS Class II** drugs (low solubility, high permeability), "
            "because dissolution is the rate-limiting step for absorption — exactly the "
            f"property an IVIVC exploits {_BCS}{_FDA}. Choosing a level then follows the goal "
            "and data: Level A for biowaivers and spec-setting (needs full profiles + "
            "deconvolution), Level C for early screening, Level B only as supporting "
            "evidence."
        ),
        "questions": [
            {
                "q": "For which BCS class is an IVIVC most likely to succeed, and why?",
                "options": [
                    "Class I, because everything dissolves fast",
                    "Class II, because dissolution is the rate-limiting step for absorption",
                    "Class III, because permeability limits absorption",
                    "Class IV, because both properties are limiting",
                ],
                "answer_index": 1,
                "explanation": (
                    "BCS Class II drugs (low solubility, high permeability) are dissolution "
                    "rate-limited, so in vitro dissolution strongly predicts in vivo "
                    f"absorption — ideal for IVIVC {_BCS}{_FDA}."
                ),
            },
        ],
    },
]


def total_questions() -> int:
    """Total number of self-check questions across all lessons."""
    return sum(len(lesson["questions"]) for lesson in LESSONS)


def grade(question: dict, selected_index: int) -> dict:
    """Grade a single multiple-choice answer.

    Returns a dict describing the outcome:
      * ``correct``        – whether ``selected_index`` matches the answer.
      * ``answer_index``   – the index of the correct option.
      * ``selected_index`` – the index the learner chose (echoed back).
      * ``explanation``    – the question's explanation text.
      * ``correct_option`` – the text of the correct option (always the RIGHT
        answer, regardless of the learner's choice).
    """
    answer_index = question["answer_index"]
    options = question["options"]
    return {
        "correct": selected_index == answer_index,
        "answer_index": answer_index,
        "selected_index": selected_index,
        "explanation": question["explanation"],
        "correct_option": options[answer_index],
    }


def total_questions_index() -> dict[str, int]:
    """Map each ``"<lesson_id>:<q_index>"`` key to its correct answer index.

    Used internally by :func:`score_summary` to grade an answers dict without
    re-walking the lesson tree per key. Unknown keys simply won't appear here.
    """
    index: dict[str, int] = {}
    for lesson in LESSONS:
        lid = lesson["id"]
        for qi, question in enumerate(lesson["questions"]):
            index[f"{lid}:{qi}"] = question["answer_index"]
    return index


def score_summary(answers: dict) -> dict:
    """Summarise a set of answers.

    ``answers`` maps ``"<lesson_id>:<q_index>" -> selected_index``. Returns:
      * ``answered`` – number of entries provided (questions attempted).
      * ``correct``  – number whose selected index matches the correct answer.
      * ``total``    – total questions in the whole curriculum.
      * ``pct``      – correct / total * 100, rounded to 0 decimal places
        (``0.0`` when there are no questions).

    Robust to unknown / malformed keys: an entry that does not correspond to a
    real ``lesson:q`` is counted as "answered" but never as "correct", and never
    raises.
    """
    correct_index = total_questions_index()
    total = total_questions()
    answered = len(answers)
    correct = 0
    for key, selected in answers.items():
        if correct_index.get(key) == selected and key in correct_index:
            correct += 1
    pct = round(correct / total * 100, 0) if total else 0.0
    return {
        "answered": answered,
        "correct": correct,
        "total": total,
        "pct": pct,
    }
