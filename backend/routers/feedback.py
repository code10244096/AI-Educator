"""使用改进意见：提交反馈 / 管理员查看"""
import json
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import current_user, is_guest_user
from database import get_db
from models import Feedback, User

router = APIRouter()
admin_router = APIRouter()

# 轻量防刷：同一用户 60 秒内不可重复提交（进程内内存，不需新依赖）
_RATE_LIMIT_SECONDS = 60
_last_submit_at: dict[int, float] = {}


class TopicInput(BaseModel):
    name: str
    detail: str = ""


class FeedbackCreate(BaseModel):
    topics: list[TopicInput] = []
    content: str = ""
    contact: str = ""
    page: str = ""


@router.post("/feedback")
async def submit_feedback(
    body: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """提交使用改进意见（体验账号与正式账号均可）"""
    topics = []
    for t in body.topics or []:
        name = (t.name or "").strip()[:50]
        if not name:
            continue
        detail = (t.detail or "").strip()[:200]
        topics.append({"name": name, "detail": detail})
    content = (body.content or "").strip()[:300]
    contact = (body.contact or "").strip()[:100]
    page = (body.page or "").strip()[:200]

    if not topics and not content:
        raise HTTPException(status_code=400, detail="请至少选择一个问题或填写意见")

    now = time.monotonic()
    last = _last_submit_at.get(user.id)
    if last is not None and now - last < _RATE_LIMIT_SECONDS:
        raise HTTPException(status_code=429, detail="提交过于频繁，请稍后再试")

    row = Feedback(
        topics=json.dumps(topics, ensure_ascii=False),
        content=content,
        contact=contact,
        page=page,
        user_id=user.id,
    )
    db.add(row)
    await db.commit()
    _last_submit_at[user.id] = now
    from trial_quota import mark_feedback
    mark_feedback(user.id)
    return {"ok": True}


@admin_router.get("/feedback/list")
async def list_feedback(
    db: AsyncSession = Depends(get_db),
):
    """管理员查看最近 200 条反馈（按时间倒序）"""
    result = await db.execute(
        select(Feedback, User)
        .outerjoin(User, Feedback.user_id == User.id)
        .order_by(Feedback.created_at.desc())
        .limit(200)
    )
    items = []
    for feedback, user in result.all():
        try:
            topics = json.loads(feedback.topics or "[]")
        except (TypeError, json.JSONDecodeError):
            topics = []
        if not isinstance(topics, list):
            topics = []
        items.append({
            "id": feedback.id,
            "topics": topics,
            "content": feedback.content or "",
            "contact": feedback.contact or "",
            "page": feedback.page or "",
            "user_id": feedback.user_id,
            "is_guest": is_guest_user(user) if user else False,
            "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
        })
    return {"items": items}
