# -*- coding: utf-8 -*-
"""模型调用用量统计 API。"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool

import usage_stats

router = APIRouter()


def _parse_bool(value: Optional[str]) -> Optional[bool]:
    if value is None or value == "":
        return None
    v = value.strip().lower()
    if v in ("1", "true", "yes", "ok", "success"):
        return True
    if v in ("0", "false", "no", "fail", "failed"):
        return False
    return None


def _summary(since, until, source, feature):
    root = usage_stats.default_log_root()
    records = usage_stats.load_call_records(root, since=since, until=until, source=source, feature=feature)
    result = usage_stats.summarize(records)
    result["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    result["log_root"] = root
    result["filters"] = {"since": since, "until": until, "source": source, "feature": feature}
    return result


def _calls(limit, since, until, source, feature, success):
    root = usage_stats.default_log_root()
    records = usage_stats.load_call_records(root, since=since, until=until, source=source, feature=feature)
    records = usage_stats.filter_records(records, success=_parse_bool(success))
    return {
        "total": len(records),
        "items": usage_stats.recent_calls(records, limit=limit),
    }


@router.get("/usage/summary")
async def usage_summary(
    since: Optional[str] = Query(None, description="ISO 时间（无时区按 UTC），仅统计此时间之后"),
    until: Optional[str] = Query(None, description="ISO 时间，仅统计此时间之前"),
    source: Optional[str] = Query(None, description="backend / cli，可逗号分隔"),
    feature: Optional[str] = Query(None, description="ocr / grade / lessonplan / variant / seed_grade / other / unknown"),
):
    return await run_in_threadpool(_summary, since, until, source, feature)


@router.get("/usage/calls")
async def usage_calls(
    limit: int = Query(50, ge=1, le=1000),
    since: Optional[str] = None,
    until: Optional[str] = None,
    source: Optional[str] = None,
    feature: Optional[str] = None,
    success: Optional[str] = Query(None, description="true / false"),
):
    return await run_in_threadpool(_calls, limit, since, until, source, feature, success)
