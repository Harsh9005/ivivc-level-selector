"""
Page 7: Guided Mode — a self-paced IVIVC walkthrough with self-checks

A short, linear learning path (5 lessons) with instant-feedback multiple-choice
self-checks. Progress and score live only in this browser session — nothing is
stored or sent anywhere. Lesson text carries the same verified citation numbers
(e.g. [8] = Wagner–Nelson) used everywhere else in the app.
"""

import streamlit as st

st.set_page_config(page_title="Guided Mode — IVIVC", page_icon="🧭", layout="wide")

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.quiz import LESSONS, grade, score_summary, total_questions
from utils.citations import references_for, reference_entry_markdown

# References cited across the walkthrough (rendered in the sources expander).
SOURCE_KEYS = [
    "fda_ivivc_1997",
    "wagner_nelson_1963",
    "loo_riegelman_1968",
    "yamaoka_1978",
    "shah_f2_1998",
    "fda_dissolution_ir_1997",
    "amidon_bcs_1995",
    "andhariya_2019",
]

N_LESSONS = len(LESSONS)


# ── Session state ───────────────────────────────────────────────────────────
def _reveal_key(lesson_id: str, qi: int) -> str:
    """Session-state key for whether a question's feedback is currently shown."""
    return f"gm_reveal:{lesson_id}:{qi}"


def _radio_key(lesson_id: str, qi: int) -> str:
    """Session-state / widget key for a question's radio selection."""
    return f"gm_radio:{lesson_id}:{qi}"


def _init_state() -> None:
    st.session_state.setdefault("gm_step", 0)
    st.session_state.setdefault("gm_answers", {})


def _reset_state() -> None:
    """Clear all Guided-Mode progress: step, answers, and per-question flags."""
    st.session_state["gm_step"] = 0
    st.session_state["gm_answers"] = {}
    # Drop every reveal flag and radio selection so the walkthrough truly restarts.
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and (
            key.startswith("gm_reveal:") or key.startswith("gm_radio:")
        ):
            del st.session_state[key]


_init_state()

# Keep the step in range even if state was tampered with.
st.session_state["gm_step"] = max(0, min(st.session_state["gm_step"], N_LESSONS - 1))


# ── Intro ───────────────────────────────────────────────────────────────────
st.title("🧭 Guided Mode")
st.markdown(
    "A **self-paced walkthrough** of In Vitro–In Vivo Correlation (IVIVC). Five "
    "short lessons take you from *what IVIVC is* to *how to choose a correlation "
    "level*, each followed by a quick **self-check** with instant feedback."
)
st.info(
    "Your progress and score are kept **only in this browser session** — nothing "
    "is stored, saved, or sent anywhere. Refreshing the page starts you over.",
    icon="🔒",
)

st.markdown("---")


# ── Progress ────────────────────────────────────────────────────────────────
step = st.session_state["gm_step"]
st.progress((step + 1) / N_LESSONS, text=f"Lesson {step + 1} of {N_LESSONS}")

lesson = LESSONS[step]


# ── Current lesson ──────────────────────────────────────────────────────────
st.header(lesson["title"])
st.markdown(lesson["body"])

st.markdown("#### Self-check")

for qi, question in enumerate(lesson["questions"]):
    options = question["options"]
    rkey = _radio_key(lesson["id"], qi)
    revkey = _reveal_key(lesson["id"], qi)

    st.markdown(f"**Q{qi + 1}. {question['q']}**")

    selected = st.radio(
        "Choose one:",
        options=list(range(len(options))),
        format_func=lambda i, _opts=options: _opts[i],
        index=None,  # nothing preselected → "not answered yet"
        key=rkey,
        label_visibility="collapsed",
    )

    if st.button("Check answer", key=f"gm_check:{lesson['id']}:{qi}"):
        if selected is None:
            st.warning("Pick an option first, then press **Check answer**.", icon="⚠️")
        else:
            result = grade(question, selected)
            # Persist the choice + reveal so feedback survives reruns.
            st.session_state["gm_answers"][f"{lesson['id']}:{qi}"] = selected
            st.session_state[revkey] = True

    # Re-render feedback on every rerun while this question is "revealed".
    if st.session_state.get(revkey) and st.session_state["gm_answers"].get(
        f"{lesson['id']}:{qi}"
    ) is not None:
        chosen = st.session_state["gm_answers"][f"{lesson['id']}:{qi}"]
        result = grade(question, chosen)
        if result["correct"]:
            st.success(f"✅ Correct. {result['explanation']}")
        else:
            st.error(
                f"❌ Not quite. The correct answer is "
                f"**{result['correct_option']}**. {result['explanation']}"
            )

    st.markdown("")  # breathing room between questions


# ── Navigation ──────────────────────────────────────────────────────────────
st.markdown("---")
nav_prev, nav_spacer, nav_next = st.columns([1, 2, 1])

with nav_prev:
    if st.button("⬅️ Previous", disabled=(step == 0), use_container_width=True):
        st.session_state["gm_step"] = max(0, step - 1)
        st.rerun()

is_last = step == N_LESSONS - 1

with nav_next:
    if not is_last:
        if st.button("Next ➡️", use_container_width=True):
            st.session_state["gm_step"] = min(N_LESSONS - 1, step + 1)
            st.rerun()
    else:
        if st.button("🎉 Finish", use_container_width=True, type="primary"):
            st.session_state["gm_finished"] = True
            st.rerun()


# ── Finish screen ───────────────────────────────────────────────────────────
if is_last and st.session_state.get("gm_finished"):
    st.markdown("---")
    summary = score_summary(st.session_state["gm_answers"])
    st.subheader("🎉 Walkthrough complete!")
    st.markdown(
        f"You scored **{summary['correct']}/{summary['total']}** "
        f"(**{summary['pct']:.0f}%**) on the self-checks "
        f"— you answered {summary['answered']} of {summary['total']} questions."
    )
    if summary["answered"] < summary["total"]:
        st.caption(
            "Tip: scroll back through the lessons to attempt any questions you skipped."
        )

    if st.button("🔄 Restart walkthrough"):
        _reset_state()
        st.session_state.pop("gm_finished", None)
        st.rerun()


# ── Sources ─────────────────────────────────────────────────────────────────
with st.expander("📚 Sources behind this walkthrough"):
    st.markdown(
        "The inline numbers (e.g. **[8]**) above are this app's canonical, "
        "independently verified references. The sources cited in this walkthrough:"
    )
    for ref in references_for(SOURCE_KEYS):
        st.markdown(reference_entry_markdown(ref))
    st.caption(
        "See the **📚 References** page for the full verified corpus, verification "
        "method, and the claims each source supports."
    )


# ── Disclaimer ──────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "**Disclaimer:** This walkthrough is educational. All demonstrations elsewhere "
    "in this app use synthetic/hypothetical data from mathematical models. "
    "Regulatory submissions require a validated IVIVC built on real experimental "
    "data — consult the relevant FDA/EMA guidance."
)
