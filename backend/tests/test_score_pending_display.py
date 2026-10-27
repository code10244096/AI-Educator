"""待复核作业：分数仍入库，展示与统计不当成真 0 分。"""
import json

from class_service import (
    _submission_to_student,
    is_scored,
    is_score_pending,
    score_display,
)
from jobs import compute_score
from models import HomeworkSubmission


def test_compute_score_all_needs_review_is_pending():
    out = compute_score([
        {"is_correct": False, "needs_review": True},
        {"is_correct": False, "needs_review": True},
    ])
    assert out["score"] == 0
    assert out["score_pending"] is True


def test_score_pending_shown_as_review_not_zero():
    sub = HomeworkSubmission(
        student_name="甲",
        status="completed",
        grading_status="已批改",
        score=0,
        wrong_count=2,
        file_count=1,
        needs_review=True,
        review_status="pending_review",
        grading_result=json.dumps({
            "score": 0,
            "score_pending": True,
            "needs_review": True,
            "questions": [
                {"is_correct": False, "needs_review": True},
                {"is_correct": False, "needs_review": True},
            ],
        }),
    )
    assert is_score_pending(sub) is True
    assert is_scored(sub) is False
    row = _submission_to_student(sub, 1)
    assert row["score"] == 0
    assert row["score_pending"] is True
    assert score_display(row) == "待复核"
    assert score_display(sub) == "待复核"


def test_confirmed_zero_still_counts_as_score():
    sub = HomeworkSubmission(
        student_name="乙",
        status="completed",
        grading_status="已批改",
        score=0,
        grading_result=json.dumps({"score": 0, "score_pending": False, "questions": []}),
    )
    assert is_scored(sub) is True
    assert score_display(_submission_to_student(sub, 1)) == "0 分"
