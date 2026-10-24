"""公测体验额度：第一档用完后，当天有意见才升到第二档。提示里不写具体数字。"""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from config import settings
from trial_quota import (
    MSG_DONE,
    MSG_NEED_FEEDBACK,
    TrialLimited,
    add_tokens,
    before_call,
    consume,
    enforce,
    mark_feedback,
    reset_for_tests,
)


@pytest.fixture
def quota(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "TRIAL_QUOTA_ENABLED", True)
    monkeypatch.setattr(settings, "TRIAL_QUOTA_FILE", str(tmp_path / "quota.json"))
    monkeypatch.setattr(settings, "TRIAL_BASE_TOKENS", 100)
    monkeypatch.setattr(settings, "TRIAL_BASE_GRADE", 2)
    monkeypatch.setattr(settings, "TRIAL_BASE_LESSONPLAN", 1)
    monkeypatch.setattr(settings, "TRIAL_BASE_VARIANT", 1)
    monkeypatch.setattr(settings, "TRIAL_EXT_TOKENS", 250)
    monkeypatch.setattr(settings, "TRIAL_EXT_GRADE", 4)
    monkeypatch.setattr(settings, "TRIAL_EXT_LESSONPLAN", 2)
    monkeypatch.setattr(settings, "TRIAL_EXT_VARIANT", 2)
    monkeypatch.setattr(settings, "TRIAL_CALLS_PER_MINUTE", 2)
    reset_for_tests()
    yield
    reset_for_tests()


def _teacher(uid=7):
    return SimpleNamespace(id=uid, role="teacher")


def _assert_hidden(text: str) -> None:
    for leaked in ("10000", "30000", "100", "250", "token", "Token", "次/天"):
        assert leaked not in text


def test_base_limit_asks_for_feedback_then_extends(quota):
    consume(_teacher(), "grade")
    consume(_teacher(), "grade")
    with pytest.raises(TrialLimited) as caught:
        consume(_teacher(), "grade")
    assert str(caught.value) == MSG_NEED_FEEDBACK
    _assert_hidden(str(caught.value))

    mark_feedback(7)
    consume(_teacher(), "grade")
    consume(_teacher(), "grade")
    with pytest.raises(TrialLimited) as done:
        consume(_teacher(), "grade")
    assert str(done.value) == MSG_DONE
    _assert_hidden(str(done.value))


def test_other_teacher_and_admin_are_separate(quota):
    consume(_teacher(1), "lessonplan")
    with pytest.raises(TrialLimited):
        consume(_teacher(1), "lessonplan")
    consume(_teacher(2), "lessonplan")
    for _ in range(5):
        consume(SimpleNamespace(id=9, role="admin"), "grade")


def test_rate_and_tokens_messages(quota, monkeypatch):
    before_call(7)
    before_call(7)
    with pytest.raises(TrialLimited) as rate:
        before_call(7)
    assert str(rate.value) == MSG_DONE

    reset_for_tests()
    monkeypatch.setattr(settings, "TRIAL_CALLS_PER_MINUTE", 10)
    add_tokens(7, 100)
    with pytest.raises(TrialLimited) as base:
        before_call(7)
    assert str(base.value) == MSG_NEED_FEEDBACK
    mark_feedback(7)
    before_call(7)
    add_tokens(7, 150)
    with pytest.raises(TrialLimited) as done:
        before_call(7)
    assert str(done.value) == MSG_DONE


def test_http_error_uses_the_sentence(quota):
    consume(_teacher(), "variant")
    with pytest.raises(HTTPException) as caught:
        asyncio.run(enforce(_teacher(), "variant"))
    assert caught.value.status_code == 429
    assert caught.value.detail == MSG_NEED_FEEDBACK
