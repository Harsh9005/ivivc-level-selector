"""Tests for utils.quiz — the pure Guided-Mode curriculum + grading module.

The curriculum is 5 lessons carrying 7 self-check questions total. Lesson bodies
embed the app's canonical citation markers (e.g. "[8]" for Wagner–Nelson) as
literal text so the guided content shares the verified numbering used elsewhere.
This module is pure stdlib — no streamlit, no I/O — so it imports cleanly both
locally and inside stlite's Pyodide virtual FS.
"""
import pytest

from utils import quiz as q

LESSON_REQUIRED_FIELDS = ("id", "title", "body", "questions")
QUESTION_REQUIRED_FIELDS = ("q", "options", "answer_index", "explanation")

EXPECTED_LESSON_IDS = [
    "what-is-ivivc",
    "level-a",
    "level-b",
    "level-c",
    "bcs-and-choosing",
]


# ── Shape & integrity ───────────────────────────────────────────────────────
def test_lessons_is_list_of_five():
    assert isinstance(q.LESSONS, list)
    assert len(q.LESSONS) == 5


def test_lesson_ids_in_order():
    assert [lesson["id"] for lesson in q.LESSONS] == EXPECTED_LESSON_IDS


def test_lesson_ids_are_unique():
    ids = [lesson["id"] for lesson in q.LESSONS]
    assert len(set(ids)) == len(ids)


def test_every_lesson_has_required_fields_with_correct_types():
    for lesson in q.LESSONS:
        for field in LESSON_REQUIRED_FIELDS:
            assert field in lesson, f"{lesson.get('id', '?')} missing {field}"
        assert isinstance(lesson["id"], str) and lesson["id"]
        assert isinstance(lesson["title"], str) and lesson["title"]
        assert isinstance(lesson["body"], str) and lesson["body"]
        assert isinstance(lesson["questions"], list) and lesson["questions"]


def test_every_question_has_required_fields_and_valid_answer_index():
    for lesson in q.LESSONS:
        for qi, question in enumerate(lesson["questions"]):
            for field in QUESTION_REQUIRED_FIELDS:
                assert field in question, (
                    f"{lesson['id']} q{qi} missing {field}"
                )
            assert isinstance(question["q"], str) and question["q"]
            assert isinstance(question["options"], list)
            assert len(question["options"]) >= 2
            assert all(isinstance(o, str) and o for o in question["options"])
            ai = question["answer_index"]
            assert isinstance(ai, int)
            # answer_index must be a valid index into options
            assert 0 <= ai < len(question["options"]), (
                f"{lesson['id']} q{qi} answer_index {ai} out of range"
            )
            assert isinstance(question["explanation"], str) and question["explanation"]


def test_total_questions_is_seven():
    assert q.total_questions() == 7
    # and matches the sum of per-lesson question counts
    assert q.total_questions() == sum(len(l["questions"]) for l in q.LESSONS)


# ── Citation markers in lesson bodies ────────────────────────────────────────
def _body(lesson_id):
    return next(l["body"] for l in q.LESSONS if l["id"] == lesson_id)


def test_what_is_ivivc_body_has_fda_marker():
    assert "[1]" in _body("what-is-ivivc")


def test_level_a_body_has_wagner_nelson_and_loo_riegelman_markers():
    body = _body("level-a")
    assert "[8]" in body   # Wagner–Nelson
    assert "[9]" in body   # Loo–Riegelman
    assert "[1]" in body   # FDA %PE criteria


def test_level_b_body_has_yamaoka_and_fda_markers():
    body = _body("level-b")
    assert "[12]" in body  # Yamaoka statistical moments
    assert "[1]" in body   # FDA


def test_level_c_body_has_f2_and_min_formulation_markers():
    body = _body("level-c")
    assert "[13]" in body  # Shah f2
    assert "[5]" in body   # FDA dissolution IR
    assert "[1]" in body   # FDA min-formulations
    assert "[14]" in body  # andhariya PLGA microspheres


def test_bcs_body_has_bcs_marker():
    body = _body("bcs-and-choosing")
    assert "[10]" in body  # Amidon BCS
    assert "[1]" in body


# ── grade ─────────────────────────────────────────────────────────────────────
def test_grade_correct_choice():
    question = q.LESSONS[1]["questions"][0]  # Wagner–Nelson question, answer 1
    result = q.grade(question, 1)
    assert result["correct"] is True
    assert result["answer_index"] == 1
    assert result["selected_index"] == 1
    assert result["explanation"] == question["explanation"]
    assert result["correct_option"] == question["options"][1]


def test_grade_incorrect_choice():
    question = q.LESSONS[1]["questions"][0]  # answer 1
    result = q.grade(question, 0)
    assert result["correct"] is False
    assert result["answer_index"] == 1
    assert result["selected_index"] == 0
    assert result["explanation"] == question["explanation"]
    # correct_option always reflects the RIGHT answer, regardless of selection
    assert result["correct_option"] == question["options"][1]


def test_grade_every_lessons_designated_answer_is_correct():
    for lesson in q.LESSONS:
        for question in lesson["questions"]:
            res = q.grade(question, question["answer_index"])
            assert res["correct"] is True
            assert res["correct_option"] == question["options"][question["answer_index"]]


# ── score_summary ──────────────────────────────────────────────────────────────
def _all_correct_answers():
    answers = {}
    for lesson in q.LESSONS:
        for qi, question in enumerate(lesson["questions"]):
            answers[f"{lesson['id']}:{qi}"] = question["answer_index"]
    return answers


def test_score_summary_full_correct():
    summary = q.score_summary(_all_correct_answers())
    total = q.total_questions()
    assert summary["total"] == total
    assert summary["answered"] == total
    assert summary["correct"] == total
    assert summary["pct"] == 100.0


def test_score_summary_empty():
    summary = q.score_summary({})
    assert summary["answered"] == 0
    assert summary["correct"] == 0
    assert summary["total"] == q.total_questions()
    assert summary["pct"] == 0.0


def test_score_summary_partial_mixed():
    # Answer 3 questions: 2 correct, 1 wrong.
    l0 = q.LESSONS[0]               # 1 question
    l1 = q.LESSONS[1]               # 2 questions
    q0_correct = l0["questions"][0]["answer_index"]
    q1_correct = l1["questions"][0]["answer_index"]
    # pick a wrong index for the second question of lesson 1
    q2 = l1["questions"][1]
    q2_wrong = (q2["answer_index"] + 1) % len(q2["options"])
    answers = {
        f"{l0['id']}:0": q0_correct,    # correct
        f"{l1['id']}:0": q1_correct,    # correct
        f"{l1['id']}:1": q2_wrong,      # wrong
    }
    summary = q.score_summary(answers)
    assert summary["answered"] == 3
    assert summary["correct"] == 2
    assert summary["total"] == q.total_questions()
    # 2/7 = 28.57 → rounded 0dp = 29.0
    assert summary["pct"] == round(2 / q.total_questions() * 100, 0)


def test_score_summary_pct_rounded_zero_dp():
    # one correct out of 7 → 14.2857 → 14.0
    l0 = q.LESSONS[0]
    answers = {f"{l0['id']}:0": l0["questions"][0]["answer_index"]}
    summary = q.score_summary(answers)
    assert summary["correct"] == 1
    assert summary["pct"] == 14.0


def test_score_summary_ignores_unparseable_or_missing_keys_gracefully():
    # robustness: an answer key that doesn't map to a real lesson:q is simply
    # not counted as correct (and must never raise).
    answers = {"nonexistent-lesson:0": 0, "what-is-ivivc:99": 0}
    summary = q.score_summary(answers)
    assert summary["correct"] == 0
    assert summary["total"] == q.total_questions()
    # answered counts the entries provided
    assert summary["answered"] == 2
