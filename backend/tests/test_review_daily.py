"""review_daily 每日题库审核：隔离 / 低质量 / Jev 降级 / 报告结构。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from crawler import review_daily
from crawler.review_daily import (
    decide_status,
    format_summary_line,
    merge_quarantine_backup,
    review_once,
    write_report,
)
from models import Base, QuestionBank

BJ = ZoneInfo("Asia/Shanghai")

DIRTY_HTM = (
    "7006319. htm下文是2024年北京高考各科试卷及答案解析："
    "请考生结合自身情况合理安排复习。"
)
CLEAN_TEXT = (
    "已知函数 f(x)=x+1，则 f(1)=（　）\n"
    "A. 1\nB. 2\nC. 3\nD. 4"
)


@pytest.fixture
async def review_env(tmp_path, monkeypatch):  # asyncio_mode=auto
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    log_dir = tmp_path / "logs"
    backup_dir = tmp_path / "backups"
    log_dir.mkdir()
    backup_dir.mkdir()

    monkeypatch.setattr(review_daily, "AsyncSessionLocal", Session)
    monkeypatch.setattr(review_daily, "LOG_DIR", log_dir)
    monkeypatch.setattr(review_daily, "BACKUP_DIR", backup_dir)

    async def _add(**kwargs) -> QuestionBank:
        now = datetime.now(BJ)
        payload = {
            "question_text": CLEAN_TEXT,
            "answer": "B",
            "solution": "代入得 2",
            "question_type": "选择题",
            "subject": "数学",
            "education_level": "高中",
            "created_at": now,
            "updated_at": now,
        }
        payload.update(kwargs)
        async with Session() as db:
            q = QuestionBank(**payload)
            db.add(q)
            await db.commit()
            await db.refresh(q)
            return q

    try:
        yield {
            "Session": Session,
            "log_dir": log_dir,
            "backup_dir": backup_dir,
            "add": _add,
            "day": datetime.now(BJ).strftime("%Y-%m-%d"),
        }
    finally:
        await engine.dispose()


class _FailJev:
    enabled = True

    class _Logger:
        async def log_call(self, **kwargs):
            return None

    def __init__(self):
        self.logger = self._Logger()

    async def rank_candidates(self, **kwargs):
        raise RuntimeError("jev unavailable")


async def test_dirty_row_quarantined_and_backed_up(review_env, monkeypatch):
    env = review_env
    dirty = await env["add"](question_text=DIRTY_HTM, answer="", solution="")
    clean = await env["add"]()

    async def _skip_jev(candidates, *, token_usage):
        return {"sampled": 0, "passed": 0, "failed_ids": [], "skipped": True}

    monkeypatch.setattr(review_daily, "run_jev_sample", _skip_jev)

    report = await review_once(day=env["day"], dry_run=False)
    assert any(item["id"] == dirty.id for item in report["quarantined"])
    assert report["status"] == "warn"

    async with env["Session"]() as db:
        from sqlalchemy import select

        ids = set((await db.execute(select(QuestionBank.id))).scalars().all())
    assert dirty.id not in ids
    assert clean.id in ids

    backup_path = env["backup_dir"] / f"review_quarantined_{env['day']}.json"
    assert backup_path.exists()
    backed = json.loads(backup_path.read_text(encoding="utf-8"))
    assert any(row["id"] == dirty.id for row in backed)
    assert any(DIRTY_HTM[:20] in (row.get("question_text") or "") for row in backed)


async def test_empty_answer_marked_low_quality_not_deleted(review_env, monkeypatch):
    env = review_env
    text = "这是一道超过十五个字的填空题题干用于质量检查"
    q = await env["add"](question_text=text, answer="", solution="", question_type="填空题")

    async def _skip_jev(candidates, *, token_usage):
        return {"sampled": 0, "passed": 0, "failed_ids": [], "skipped": True}

    monkeypatch.setattr(review_daily, "run_jev_sample", _skip_jev)

    report = await review_once(day=env["day"], dry_run=False)
    assert report["quarantined"] == []
    assert any(item["id"] == q.id for item in report["low_quality"])

    async with env["Session"]() as db:
        from sqlalchemy import select

        still = (
            await db.execute(select(QuestionBank).where(QuestionBank.id == q.id))
        ).scalar_one_or_none()
    assert still is not None


async def test_jev_failure_skipped_status_not_error(review_env, monkeypatch):
    env = review_env
    await env["add"]()

    import jev_client

    monkeypatch.setattr(jev_client, "get_jev_client", lambda: _FailJev())

    report = await review_once(day=env["day"], dry_run=False)
    assert report["jev_sample"]["skipped"] is True
    assert report["status"] != "error"
    assert report["status"] in ("ok", "warn")


async def test_report_json_structure_complete(review_env, monkeypatch):
    env = review_env
    await env["add"]()
    # summary 标注路径
    (env["log_dir"] / f"{env['day']}-summary.json").write_text(
        json.dumps({"date": env["day"], "total_new": 0, "status": "success"}),
        encoding="utf-8",
    )

    async def _skip_jev(candidates, *, token_usage):
        token_usage["calls"] = 0
        return {"sampled": 0, "passed": 0, "failed_ids": [], "skipped": True}

    monkeypatch.setattr(review_daily, "run_jev_sample", _skip_jev)

    report = await review_once(day=env["day"], dry_run=False)
    path = write_report(env["day"], report)
    loaded = json.loads(Path(path).read_text(encoding="utf-8"))

    for key in (
        "date",
        "scope_total",
        "quarantined",
        "low_quality",
        "anomaly",
        "jev_sample",
        "token_usage",
        "status",
    ):
        assert key in loaded
    jev = loaded["jev_sample"]
    for key in ("sampled", "passed", "failed_ids", "skipped"):
        assert key in jev
    usage = loaded["token_usage"]
    for key in ("calls", "input_tokens", "output_tokens"):
        assert key in usage
    assert loaded["status"] in ("ok", "warn", "error")
    assert "total_new=0" in (loaded.get("notes") or "")

    line = format_summary_line(loaded)
    assert line.startswith(f"[review] {env['day']}")
    assert "scope=" in line
    assert "status=" in line


def test_decide_status_rules():
    assert decide_status(quarantined=[], jev_failed=[], jev_skipped=True, fatal=False) == "ok"
    assert decide_status(quarantined=[{"id": 1}], jev_failed=[], jev_skipped=False, fatal=False) == "warn"
    assert decide_status(quarantined=[], jev_failed=[2], jev_skipped=False, fatal=False) == "warn"
    assert decide_status(quarantined=[], jev_failed=[], jev_skipped=False, fatal=True) == "error"


def test_merge_quarantine_backup_merges_by_id(tmp_path):
    path = tmp_path / "review_quarantined_2026-11-06.json"
    merge_quarantine_backup(path, [{"id": 1, "question_text": "a"}])
    merge_quarantine_backup(path, [{"id": 2, "question_text": "b"}, {"id": 1, "question_text": "a2"}])
    data = json.loads(path.read_text(encoding="utf-8"))
    assert [row["id"] for row in data] == [1, 2]
    assert data[0]["question_text"] == "a2"


async def test_old_rows_outside_24h_not_in_scope(review_env, monkeypatch):
    env = review_env
    old = datetime.now(BJ) - timedelta(hours=30)
    await env["add"](created_at=old, updated_at=old, question_text=DIRTY_HTM, answer="")
    await env["add"]()

    async def _skip_jev(candidates, *, token_usage):
        return {"sampled": 0, "passed": 0, "failed_ids": [], "skipped": True}

    monkeypatch.setattr(review_daily, "run_jev_sample", _skip_jev)
    report = await review_once(day=env["day"], dry_run=False)
    assert report["scope_total"] == 1
    assert report["quarantined"] == []
