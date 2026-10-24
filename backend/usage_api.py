# -*- coding: utf-8 -*-
"""模型调用用量统计 API。"""

import json
from datetime import datetime
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import usage_stats
from database import get_db
from models import User

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


def _require_ts(name: str, value: Optional[str]) -> Optional[str]:
    """空值放行；有值但解析失败则 422（与 FastAPI 参数校验一致）。"""
    if value is None or value == "":
        return None
    if usage_stats.parse_ts(value) is None:
        raise HTTPException(status_code=422, detail=f"{name} 时间格式无效")
    return value


def _summary(since, until, source, feature):
    root = usage_stats.default_log_root()
    records = usage_stats.load_call_records(root, since=since, until=until, source=source, feature=feature)
    result = usage_stats.summarize(records)
    result["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    # 不返回服务器上的日志绝对路径
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
    since = _require_ts("since", since)
    until = _require_ts("until", until)
    return await run_in_threadpool(_summary, since, until, source, feature)


def _module_brief(stat: Optional[dict]) -> dict:
    stat = stat or {}
    return {
        "calls": int(stat.get("calls") or 0),
        "failed": int(stat.get("failed") or 0),
        "total_tokens": int(stat.get("total_tokens") or 0),
        "prompt_tokens": int(stat.get("prompt_tokens") or 0),
        "completion_tokens": int(stat.get("completion_tokens") or 0),
    }


def _account_row(user_id, username, display_name, role, auth_method, stat) -> dict:
    stat = stat or {}
    raw_modules = stat.get("modules") or {}
    return {
        "id": user_id,
        "username": username or "",
        "display_name": display_name or username or "未命名",
        "role": role or "",
        "auth_method": auth_method or "",
        "calls": int(stat.get("calls") or 0),
        "failed": int(stat.get("failed") or 0),
        "total_tokens": int(stat.get("total_tokens") or 0),
        "prompt_tokens": int(stat.get("prompt_tokens") or 0),
        "completion_tokens": int(stat.get("completion_tokens") or 0),
        "modules": {key: _module_brief(raw_modules.get(key)) for key in usage_stats.MODULE_ORDER},
    }


@router.get("/usage/accounts")
async def usage_accounts(
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """每个账号的调用次数和 token。没有产生调用的账号也列出，方便对照注册情况。"""
    since = _require_ts("since", since)
    until = _require_ts("until", until)
    summary = await run_in_threadpool(_summary, since, until, None, None)
    by_teacher = {item.get("teacher_id"): item for item in summary.get("by_teacher") or []}
    users = (await db.execute(select(User).order_by(User.id))).scalars().all()
    seen = set()
    items = []
    for user in users:
        seen.add(user.id)
        items.append(_account_row(
            user.id, user.username, user.display_name or user.username,
            user.role or "teacher", user.auth_method or "password", by_teacher.get(user.id),
        ))
    for teacher_id, stat in by_teacher.items():
        if teacher_id in seen or teacher_id is None:
            continue
        items.append(_account_row(teacher_id, "", "已删除的账号", "", "", stat))
    if None in by_teacher and int(by_teacher[None].get("calls") or 0):
        items.append(_account_row(None, "", "历史日志", "", "", by_teacher[None]))
    items.sort(key=lambda row: (-row["total_tokens"], -row["calls"], row["id"] is None, row["id"] or 0))
    return {"items": items, "generated_at": summary.get("generated_at")}


@router.get("/usage/calls")
async def usage_calls(
    limit: int = Query(50, ge=1, le=1000),
    since: Optional[str] = None,
    until: Optional[str] = None,
    source: Optional[str] = None,
    feature: Optional[str] = None,
    success: Optional[str] = Query(None, description="true / false"),
):
    since = _require_ts("since", since)
    until = _require_ts("until", until)
    return await run_in_threadpool(_calls, limit, since, until, source, feature, success)


@router.get("/usage/daily")
async def usage_daily(db: AsyncSession = Depends(get_db)):
    """当天每个账号的体验额度用量。只给管理员看具体数字。"""
    from trial_quota import _today, daily_usage, quota_caps
    usage = {row["user_id"]: row for row in daily_usage()}
    users = (await db.execute(select(User).order_by(User.id))).scalars().all()
    items = []
    seen = set()
    for user in users:
        if (user.role or "") == "admin":
            continue
        row = usage.get(user.id) or {}
        seen.add(user.id)
        items.append(_daily_item(user, row))
    for uid, row in usage.items():
        if uid in seen:
            continue
        items.append(_daily_item(None, row, uid))
    items.sort(key=lambda item: (-item["tokens"], -item["grade"], item["username"]))
    caps = quota_caps()
    return {"day": _today(), "caps": caps, "items": items}


def _daily_item(user, row: dict, uid: int = 0) -> dict:
    tokens = int(row.get("tokens") or 0)
    grade = int(row.get("grade") or 0)
    lessonplan = int(row.get("lessonplan") or 0)
    variant = int(row.get("variant") or 0)
    feedback = bool(row.get("feedback"))
    return {
        "user_id": user.id if user else uid,
        "username": user.username if user else str(uid),
        "display_name": user.display_name if user else "",
        "tokens": tokens,
        "grade": grade,
        "lessonplan": lessonplan,
        "variant": variant,
        "feedback": feedback,
        "tier": "extended" if feedback else "base",
    }


@router.get("/usage/records")
async def usage_records():
    """按登录账号列出已留存的教案、批改和变式题。"""
    from user_archive import list_accounts
    return {"items": await run_in_threadpool(list_accounts)}


@router.get("/usage/records/days")
async def usage_record_days():
    """按日期统计服务器上留存的用户文件数量。"""
    from user_archive import count_by_day
    return {"items": await run_in_threadpool(count_by_day)}


@router.get("/usage/records/download")
async def usage_records_download(days: str = Query(..., description="逗号分隔的 YYYY-MM-DD")):
    """把选中日期的用户文件打包下载。文件本身留在服务器上。"""
    from user_archive import zip_by_days
    selected = [part.strip() for part in (days or "").split(",") if part.strip()]
    try:
        payload = await run_in_threadpool(zip_by_days, selected)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="这些日期没有留存文件")
    if len(selected) == 1:
        filename = quote(f"用户记录-{selected[0]}.zip")
    else:
        filename = quote(f"用户记录-{selected[0]}_{selected[-1]}.zip")
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.get("/usage/records/{username}")
async def usage_record_list(username: str):
    from user_archive import list_records
    try:
        items = await run_in_threadpool(list_records, username)
    except ValueError:
        raise HTTPException(status_code=404, detail="没有这个账号的记录")
    return {"username": username, "items": items}


@router.get("/usage/records/{username}/archive")
async def usage_record_archive(username: str):
    """下载一个账号的全部留存文件（zip）。"""
    from user_archive import account_dirname, account_zip
    try:
        payload = await run_in_threadpool(account_zip, username)
    except (ValueError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="没有这个账号的记录")
    filename = quote(f"{account_dirname(username)}.zip")
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.get("/usage/records/{username}/{kind}/{name}/file")
async def usage_record_file(username: str, kind: str, name: str, format: Optional[str] = Query(None)):
    """下载单条记录。format=md 时返回可直接打开的正文，否则返回原始 JSON。"""
    from user_archive import read_record, record_markdown, record_path
    if (format or "").lower() == "md":
        try:
            data = await run_in_threadpool(read_record, username, kind, name)
        except (ValueError, FileNotFoundError, json.JSONDecodeError):
            raise HTTPException(status_code=404, detail="记录不存在")
        stem = name[:-5] if name.endswith(".json") else name
        filename = quote(f"{stem}.md")
        return Response(
            content=record_markdown(data),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
        )
    try:
        path = await run_in_threadpool(record_path, username, kind, name)
    except (ValueError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="记录不存在")
    return FileResponse(path, media_type="application/json", filename=name)


@router.get("/usage/records/{username}/{kind}/{name}")
async def usage_record_detail(username: str, kind: str, name: str):
    from user_archive import read_record
    try:
        data = await run_in_threadpool(read_record, username, kind, name)
    except (ValueError, FileNotFoundError, json.JSONDecodeError):
        raise HTTPException(status_code=404, detail="记录不存在")
    return data
