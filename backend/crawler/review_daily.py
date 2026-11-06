"""每日题库数据审核：规则隔离脏数据 + 质量标记 + Jev 语义抽检。

由 cron 在爬虫窗口结束后运行（建议北京时间 08:40 / 容器 UTC 00:40）：

  docker exec ai-teaching-backend python /app/crawler/review_daily.py \\
    >> /opt/ai-teaching/logs/crawler/review.log 2>&1

用法：
  python backend/crawler/review_daily.py
  python backend/crawler/review_daily.py --date 2026-11-06
  python backend/crawler/review_daily.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import select


_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from crawler.daily_crawl import looks_like_dirty_row  # noqa: E402
from database import AsyncSessionLocal, init_db  # noqa: E402
from models import QuestionBank  # noqa: E402

BJ = ZoneInfo("Asia/Shanghai")

VALID_QUESTION_TYPES = frozenset({"选择题", "填空题", "解答题", "判断题"})
JEV_SAMPLE_LIMIT = 10
JEV_PASS_THRESHOLD = 0.5
JEV_REVIEW_KEYWORD = "完整可作答的题目"
SAMPLE_CHARS = 60

_log_dir_env = (os.environ.get("CRAWLER_LOG_DIR") or "").strip()
LOG_DIR = Path(_log_dir_env) if _log_dir_env else (_BACKEND / "logs" / "crawler")

_backup_dir_env = (os.environ.get("REVIEW_BACKUP_DIR") or "").strip()
BACKUP_DIR = (
    Path(_backup_dir_env) if _backup_dir_env else (_BACKEND / "data" / "backups")
)


def now_bj() -> datetime:
    return datetime.now(BJ)


def review_day(explicit: Optional[str] = None) -> str:
    """默认审核「当日」凌晨爬取批次（与 daily_crawl summary 日期一致）。"""
    if explicit:
        return explicit.strip()
    return now_bj().strftime("%Y-%m-%d")


def _sample_text(text: str, limit: int = SAMPLE_CHARS) -> str:
    s = " ".join(str(text or "").split())
    return s[:limit]


def question_to_backup_dict(q: QuestionBank) -> dict:
    """与手工清洗备份一致：完整行字段 JSON。"""
    def _dt(v: Any) -> Any:
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)

    return {
        "id": q.id,
        "question_text": q.question_text,
        "answer": q.answer,
        "solution": q.solution,
        "question_type": q.question_type,
        "subject": q.subject,
        "education_level": q.education_level,
        "grade": q.grade,
        "exam_type": q.exam_type,
        "year": q.year,
        "region": q.region,
        "knowledge_points": q.knowledge_points,
        "difficulty": q.difficulty,
        "score": q.score,
        "source_url": q.source_url,
        "is_verified": q.is_verified,
        "teaching_tips": q.teaching_tips,
        "common_mistakes": q.common_mistakes,
        "created_at": _dt(q.created_at),
        "updated_at": _dt(q.updated_at),
    }


def load_crawl_summary(day: str) -> Tuple[Optional[dict], List[str]]:
    """读取爬虫 summary；缺失或异常时仍继续审核，notes 标注。"""
    notes: List[str] = []
    path = LOG_DIR / f"{day}-summary.json"
    if not path.exists():
        notes.append(f"summary 缺失: {path.name}")
        return None, notes
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        notes.append(f"summary 无法解析: {exc}")
        return None, notes
    status = data.get("status")
    total_new = data.get("total_new")
    if status != "success":
        notes.append(f"summary status={status!r}（非 success，兜底审核）")
    if total_new == 0:
        notes.append("summary total_new=0（兜底审核）")
    return data, notes


def merge_quarantine_backup(path: Path, rows: Sequence[dict]) -> None:
    """写入/合并隔离备份；同 id 覆盖，避免重跑冲掉已备份行。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    by_id: Dict[int, dict] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                for item in existing:
                    if isinstance(item, dict) and item.get("id") is not None:
                        by_id[int(item["id"])] = item
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            by_id = {}
    for row in rows:
        by_id[int(row["id"])] = row
    ordered = [by_id[k] for k in sorted(by_id)]
    path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(day: str, report: dict) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"review-{day}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def decide_status(
    *,
    quarantined: Sequence[dict],
    jev_failed: Sequence[int],
    jev_skipped: bool,
    fatal: bool,
) -> str:
    if fatal:
        return "error"
    if quarantined or jev_failed:
        return "warn"
    # Jev 跳过不抬 error
    _ = jev_skipped
    return "ok"


def _row_as_dirty_dict(q: QuestionBank) -> dict:
    return {"question_text": q.question_text or ""}


def rule_flags(q: QuestionBank) -> Tuple[Optional[str], Optional[str]]:
    """返回 (low_quality_reason, anomaly_reason)，无则 None。"""
    text = q.question_text or ""
    answer = (q.answer or "").strip()
    solution = (q.solution or "").strip()
    low = None
    if not answer and not solution:
        low = "empty_answer_solution"
    elif len(text) < 15:
        low = "question_text_too_short"
    elif len(text) > 2000:
        low = "question_text_too_long"

    anomaly = None
    qtype = (q.question_type or "").strip()
    if qtype not in VALID_QUESTION_TYPES:
        anomaly = "invalid_question_type"
    return low, anomaly


async def fetch_recent_rows(hours: float = 24.0) -> List[QuestionBank]:
    cutoff = now_bj() - timedelta(hours=hours)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(QuestionBank)
            .where(QuestionBank.created_at >= cutoff)
            .order_by(QuestionBank.id.asc())
        )
        return list(result.scalars().all())


async def quarantine_rows(
    rows: Sequence[QuestionBank],
    *,
    dry_run: bool,
) -> Tuple[List[dict], List[dict]]:
    """隔离脏行：备份 dict 列表 + 报告条目。返回后 ORM 实例不可再依赖。"""
    dirty = [q for q in rows if looks_like_dirty_row(_row_as_dirty_dict(q))]
    if not dirty:
        return [], []

    backups = [question_to_backup_dict(q) for q in dirty]
    report_items = [
        {"id": q.id, "reason": "dirty", "sample": _sample_text(q.question_text or "")}
        for q in dirty
    ]
    if dry_run:
        return backups, report_items

    ids = [q.id for q in dirty]
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(QuestionBank).where(QuestionBank.id.in_(ids)))
        found = list(result.scalars().all())
        # 重跑幂等：查不到即跳过
        found_by_id = {q.id: q for q in found}
        still_backups: List[dict] = []
        still_report: List[dict] = []
        for b, r in zip(backups, report_items):
            qid = int(r["id"])
            if qid not in found_by_id:
                continue
            still_backups.append(b)
            still_report.append(r)
            await db.delete(found_by_id[qid])
        await db.commit()
        return still_backups, still_report


async def run_jev_sample(
    candidates: Sequence[QuestionBank],
    *,
    token_usage: Dict[str, int],
) -> dict:
    """对通过规则的行随机抽最多 10 条做 Jev 语义抽检。失败则 skipped。"""
    out = {
        "sampled": 0,
        "passed": 0,
        "failed_ids": [],
        "skipped": False,
    }
    if not candidates:
        return out

    sample = list(candidates)
    if len(sample) > JEV_SAMPLE_LIMIT:
        sample = random.sample(sample, JEV_SAMPLE_LIMIT)

    try:
        from jev_client import get_jev_client

        client = get_jev_client()
        if not getattr(client, "enabled", True):
            out["skipped"] = True
            out["sampled"] = 0
            return out

        # 捕获用量（不改 jev_client；经 logger 旁路累加）
        orig_log = client.logger.log_call

        async def _capturing_log(**kwargs):
            usage = kwargs.get("usage") or {}
            if kwargs.get("success"):
                token_usage["calls"] += 1
                token_usage["input_tokens"] += int(
                    usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                )
                token_usage["output_tokens"] += int(
                    usage.get("completion_tokens") or usage.get("output_tokens") or 0
                )
            return await orig_log(**kwargs)

        client.logger.log_call = _capturing_log  # type: ignore[method-assign]

        passed = 0
        failed: List[int] = []
        try:
            for q in sample:
                cand = {
                    "id": q.id,
                    "question_text": q.question_text or "",
                    "knowledge_points": q.knowledge_points,
                }
                # keyword 带 review 标记，便于与普通搜索日志区分（jev_client 不改）
                ranked = await client.rank_candidates(
                    keyword=f"[review]{JEV_REVIEW_KEYWORD}",
                    candidates=[cand],
                    subject=q.subject,
                    education_level=q.education_level,
                    teacher_id=None,
                )
                score = ranked[0].relevance if ranked else 0.0
                if score >= JEV_PASS_THRESHOLD:
                    passed += 1
                else:
                    failed.append(q.id)
        finally:
            client.logger.log_call = orig_log  # type: ignore[method-assign]

        out["sampled"] = len(sample)
        out["passed"] = passed
        out["failed_ids"] = failed
        return out
    except Exception:  # noqa: BLE001  # Jev 不可用/超时等，不阻断
        out["skipped"] = True
        out["sampled"] = 0
        out["passed"] = 0
        out["failed_ids"] = []
        return out


async def review_once(
    *,
    day: str,
    dry_run: bool = False,
    skip_jev: bool = False,
) -> dict:
    notes: List[str] = []
    _, summary_notes = load_crawl_summary(day)
    notes.extend(summary_notes)

    rows = await fetch_recent_rows(24.0)
    scope_total = len(rows)

    backups, quarantined = await quarantine_rows(rows, dry_run=dry_run)
    quarantined_ids: Set[int] = {item["id"] for item in quarantined}

    if backups and not dry_run:
        merge_quarantine_backup(BACKUP_DIR / f"review_quarantined_{day}.json", backups)

    # 规则标记：跳过已隔离 id
    remaining = [q for q in rows if q.id not in quarantined_ids]
    # 隔离后若已 delete，remaining 里 ORM 可能仍持有旧对象；标记只用内存字段
    low_quality: List[dict] = []
    anomaly: List[dict] = []
    passed_rules: List[QuestionBank] = []
    for q in remaining:
        low_r, anom_r = rule_flags(q)
        if low_r:
            low_quality.append(
                {"id": q.id, "reason": low_r, "sample": _sample_text(q.question_text or "")}
            )
        if anom_r:
            anomaly.append(
                {
                    "id": q.id,
                    "reason": anom_r,
                    "sample": _sample_text(q.question_text or ""),
                    "question_type": q.question_type,
                }
            )
        if not low_r and not anom_r:
            passed_rules.append(q)

    token_usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
    if skip_jev or dry_run:
        jev_sample = {
            "sampled": 0,
            "passed": 0,
            "failed_ids": [],
            "skipped": True,
        }
        if dry_run:
            notes.append("dry-run：跳过 Jev 抽检与写库隔离")
    else:
        jev_sample = await run_jev_sample(passed_rules, token_usage=token_usage)

    status = decide_status(
        quarantined=quarantined,
        jev_failed=jev_sample.get("failed_ids") or [],
        jev_skipped=bool(jev_sample.get("skipped")),
        fatal=False,
    )

    report = {
        "date": day,
        "scope_total": scope_total,
        "quarantined": quarantined,
        "low_quality": low_quality,
        "anomaly": anomaly,
        "jev_sample": jev_sample,
        "token_usage": token_usage,
        "status": status,
        "notes": "; ".join(notes) if notes else "",
        "dry_run": bool(dry_run),
    }
    return report


def format_summary_line(report: dict) -> str:
    jev = report.get("jev_sample") or {}
    if jev.get("skipped"):
        jev_part = "skipped"
    else:
        jev_part = f"{jev.get('passed', 0)}/{jev.get('sampled', 0)}"
    return (
        f"[review] {report.get('date')} "
        f"scope={report.get('scope_total', 0)} "
        f"quarantined={len(report.get('quarantined') or [])} "
        f"low_quality={len(report.get('low_quality') or [])} "
        f"jev={jev_part} "
        f"status={report.get('status')}"
    )


async def async_main(args: argparse.Namespace) -> int:
    day = review_day(args.date)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [review_daily] %(message)s",
    )
    logger = logging.getLogger("review_daily")

    try:
        if not args.dry_run:
            await init_db()
        report = await review_once(day=day, dry_run=bool(args.dry_run), skip_jev=bool(args.skip_jev))
    except Exception as exc:  # noqa: BLE001
        logger.exception("审核失败: %s", exc)
        report = {
            "date": day,
            "scope_total": 0,
            "quarantined": [],
            "low_quality": [],
            "anomaly": [],
            "jev_sample": {"sampled": 0, "passed": 0, "failed_ids": [], "skipped": True},
            "token_usage": {"calls": 0, "input_tokens": 0, "output_tokens": 0},
            "status": "error",
            "notes": f"脚本异常: {exc}",
            "dry_run": bool(args.dry_run),
        }
        write_report(day, report)
        print(format_summary_line(report), flush=True)
        return 1

    path = write_report(day, report)
    line = format_summary_line(report)
    print(line, flush=True)
    logger.info("%s | report=%s", line, path)
    return 0 if report.get("status") != "error" else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="每日题库数据审核")
    p.add_argument("--date", default=None, help="审核日期 YYYY-MM-DD（默认北京时间当天）")
    p.add_argument("--dry-run", action="store_true", help="只评审不删库、不调 Jev")
    p.add_argument("--skip-jev", action="store_true", help="跳过 Jev 抽检")
    return p


def main() -> None:
    args = build_parser().parse_args()
    code = asyncio.run(async_main(args))
    sys.exit(code)


if __name__ == "__main__":
    main()
