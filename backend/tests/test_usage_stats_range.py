"""用量汇总：since / until 时间范围过滤。"""
from datetime import datetime, timedelta, timezone

import pytest

import usage_stats


def _row(feature, prompt, completion, ts_utc, call_id="c", teacher_id=None):
    total = prompt + completion
    meta = {}
    if teacher_id is not None:
        meta["teacher_id"] = teacher_id
    return usage_stats._slim_record({
        "call_id": call_id,
        "feature": feature,
        "task_meta": meta,
        "success": True,
        "elapsed_seconds": 1,
        "ts_utc": ts_utc,
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
        },
    }, "mem")


def _fixture_rows():
    """3 天前 / 1 天前 / 现在各一条，feature 与 token 互不相同。"""
    now = datetime(2026, 10, 24, 12, 0, 0, tzinfo=timezone.utc)
    return now, [
        _row("ocr", 100, 50, (now - timedelta(days=3)).isoformat().replace("+00:00", "Z"), "old", 1),
        _row("grade", 200, 80, (now - timedelta(days=1)).isoformat().replace("+00:00", "Z"), "mid", 1),
        _row("lessonplan", 300, 120, now.isoformat().replace("+00:00", "Z"), "new", 2),
    ]


def test_since_filters_calls_and_tokens():
    now, rows = _fixture_rows()
    since = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    filtered = usage_stats.filter_records(rows, since=since)
    summary = usage_stats.summarize(filtered)
    # 只剩 1 天前 + 现在：grade 280 + lessonplan 420 = 700，calls=2
    assert summary["overview"]["calls"] == 2
    assert summary["overview"]["total_tokens"] == 280 + 420
    assert summary["overview"]["prompt_tokens"] == 200 + 300
    assert summary["overview"]["completion_tokens"] == 80 + 120


def test_until_alone_and_combined_with_since():
    now, rows = _fixture_rows()
    until = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    only_until = usage_stats.summarize(usage_stats.filter_records(rows, until=until))
    assert only_until["overview"]["calls"] == 1
    assert only_until["overview"]["total_tokens"] == 150  # ocr only

    since = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    until2 = (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    both = usage_stats.summarize(usage_stats.filter_records(rows, since=since, until=until2))
    # 落在 (now-2d, now-1h] → 仅 mid（1 天前）
    assert both["overview"]["calls"] == 1
    assert both["overview"]["total_tokens"] == 280


def test_by_feature_totals_match_overview():
    _, rows = _fixture_rows()
    summary = usage_stats.summarize(rows)
    feature_calls = sum(item["calls"] for item in summary["by_feature"])
    feature_tokens = sum(item["total_tokens"] for item in summary["by_feature"])
    assert feature_calls == summary["overview"]["calls"] == 3
    assert feature_tokens == summary["overview"]["total_tokens"] == 150 + 280 + 420

    modules = {item["module"]: item for item in summary["by_module"]}
    assert modules["ocr"]["calls"] == 1 and modules["ocr"]["total_tokens"] == 150
    assert modules["grade"]["calls"] == 1 and modules["grade"]["total_tokens"] == 280
    assert modules["lessonplan"]["calls"] == 1 and modules["lessonplan"]["total_tokens"] == 420
    assert sum(modules[m]["total_tokens"] for m in ("ocr", "grade", "lessonplan", "notebook", "variant", "probe", "other")) == summary["overview"]["total_tokens"]


def test_empty_range_returns_zero_not_error():
    _, rows = _fixture_rows()
    future = "2099-01-01T00:00:00Z"
    summary = usage_stats.summarize(usage_stats.filter_records(rows, since=future))
    assert summary["overview"]["calls"] == 0
    assert summary["overview"]["total_tokens"] == 0
    assert summary["by_feature"] == []
    assert all(item["calls"] == 0 for item in summary["by_module"])


@pytest.mark.asyncio
async def test_invalid_since_until_return_422(make_teacher):
    admin = await make_teacher(role="admin")
    for params in (
        {"since": "not-a-date"},
        {"until": "2026-13-99"},
        {"since": "abc", "until": "2026-10-01T00:00:00Z"},
    ):
        r = await admin.get("/api/usage/summary", params=params)
        assert r.status_code == 422, params
        detail = r.json().get("detail")
        assert detail, params
        # FastAPI HTTPException 用字符串 detail；保持可读
        text = detail if isinstance(detail, str) else str(detail)
        assert "时间格式无效" in text or "since" in text.lower() or "until" in text.lower()
