"""公测体验额度：不限调用次数，只限每日 token 总量（基础档 + 当天提交反馈的奖励档）。提示里不写具体数字。"""
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
    monkeypatch.setattr(settings, "TRIAL_EXT_TOKENS", 250)
    monkeypatch.setattr(settings, "TRIAL_CALLS_PER_MINUTE", 2)
    reset_for_tests()
    yield
    reset_for_tests()


def _teacher(uid=7):
    return SimpleNamespace(id=uid, role="teacher")


def _assert_hidden(text: str) -> None:
    for leaked in ("50000", "100000", "100", "250", "token", "Token", "次/天"):
        assert leaked not in text


def test_unlimited_calls_only_tokens_count(quota):
    """不限调用次数：批改/教案/变式随便调，只按 token 总量卡。"""
    for _ in range(50):
        consume(_teacher(), "grade")
    for _ in range(20):
        consume(_teacher(), "lessonplan")
    for _ in range(20):
        consume(_teacher(), "variant")


def test_token_limit_asks_for_feedback_then_extends(quota, monkeypatch):
    """token 到基础档上限 → 提示填反馈；当天提交反馈后 → 升到奖励档；再到顶 → 明天重置提示。"""
    monkeypatch.setattr(settings, "TRIAL_CALLS_PER_MINUTE", 10)
    add_tokens(7, 100)
    with pytest.raises(TrialLimited) as caught:
        before_call(7)
    assert str(caught.value) == MSG_NEED_FEEDBACK
    _assert_hidden(str(caught.value))

    mark_feedback(7)
    before_call(7)  # 奖励档内可继续
    add_tokens(7, 150)  # 累计 250，到奖励档顶
    with pytest.raises(TrialLimited) as done:
        before_call(7)
    assert str(done.value) == MSG_DONE
    _assert_hidden(str(done.value))


def test_other_teacher_and_admin_are_separate(quota):
    add_tokens(1, 100)
    with pytest.raises(TrialLimited):
        before_call(1)
    before_call(2)  # 其他教师不受影响
    for _ in range(5):
        consume(SimpleNamespace(id=9, role="admin"), "grade")  # 管理员不占额度


def test_rate_limit_still_applies(quota):
    """分钟频率限制保留：防突发刷接口，与每日 token 额度无关。"""
    before_call(7)
    before_call(7)
    with pytest.raises(TrialLimited) as rate:
        before_call(7)
    assert str(rate.value) == MSG_DONE


def test_http_error_uses_the_sentence(quota, monkeypatch):
    monkeypatch.setattr(settings, "TRIAL_CALLS_PER_MINUTE", 10)
    add_tokens(7, 100)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(enforce(_teacher(), "grade"))
    assert caught.value.status_code == 429
    assert caught.value.detail == MSG_NEED_FEEDBACK
