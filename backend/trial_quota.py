"""公测体验额度。按登录账号、按北京时间自然日计算。

超限时只抛出固定的一句话。不要把次数、token 数或「哪一条规则」写进返回给用户的内容。
管理员不占用体验额度。
"""
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from llm.gateway import LLMError

MSG_NEED_FEEDBACK = "今日体验额度已用完。填写一条使用意见后，可以继续今天的体验。"
MSG_DONE = "今日体验额度已用完，明天 0 点重置；如需深度试用请联系我们"
TRIAL_MESSAGE = MSG_DONE
_TZ = timezone(timedelta(hours=8))  # 北京时间，无夏令时
_FEATURES = ("grade", "lessonplan", "variant")

_lock = threading.Lock()
_exempt = set()
_calls = {}  # user id -> [timestamps]
_usage = {"day": "", "users": {}}


class TrialLimited(LLMError):
    def __init__(self, message: str = MSG_DONE):
        super().__init__(message)


def _enabled() -> bool:
    from config import settings
    return bool(getattr(settings, "TRIAL_QUOTA_ENABLED", True))


def _caps(extended: bool) -> dict:
    from config import settings
    if extended:
        return {
            "tokens": int(settings.TRIAL_EXT_TOKENS),
            "grade": int(settings.TRIAL_EXT_GRADE),
            "lessonplan": int(settings.TRIAL_EXT_LESSONPLAN),
            "variant": int(settings.TRIAL_EXT_VARIANT),
        }
    return {
        "tokens": int(settings.TRIAL_BASE_TOKENS),
        "grade": int(settings.TRIAL_BASE_GRADE),
        "lessonplan": int(settings.TRIAL_BASE_LESSONPLAN),
        "variant": int(settings.TRIAL_BASE_VARIANT),
    }


def _per_minute() -> int:
    from config import settings
    return int(settings.TRIAL_CALLS_PER_MINUTE)


def _message(extended: bool) -> str:
    return MSG_DONE if extended else MSG_NEED_FEEDBACK


def _store_path() -> Path:
    from config import settings
    return Path(settings.TRIAL_QUOTA_FILE)


def _today() -> str:
    return datetime.now(_TZ).date().isoformat()


def _uid(teacher_id):
    if teacher_id is None or teacher_id == "":
        return None
    try:
        return int(teacher_id)
    except (TypeError, ValueError):
        return None


def remember_admin(user_id) -> None:
    uid = _uid(user_id)
    if uid is not None:
        _exempt.add(uid)


def _load_locked() -> None:
    global _usage
    path = _store_path()
    day = _today()
    if _usage.get("day") == day and _usage.get("users") is not None:
        return
    data = {"day": day, "users": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("day") == day and isinstance(raw.get("users"), dict):
            data = {"day": day, "users": raw["users"]}
    except (OSError, json.JSONDecodeError):
        pass
    _usage = data


def _save_locked() -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_usage, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _bucket_locked(uid: int) -> dict:
    _load_locked()
    users = _usage["users"]
    key = str(uid)
    row = users.get(key)
    if not isinstance(row, dict):
        row = {"tokens": 0, "grade": 0, "lessonplan": 0, "variant": 0, "feedback": False}
        users[key] = row
    return row


def _reject_if_over(row: dict, feature: str = "") -> None:
    extended = bool(row.get("feedback"))
    caps = _caps(extended)
    if int(row.get("tokens") or 0) >= caps["tokens"]:
        raise TrialLimited(_message(extended))
    if feature and int(row.get(feature) or 0) >= caps[feature]:
        raise TrialLimited(_message(extended))


def mark_feedback(user_id) -> None:
    """当天提交过意见后，升到第二档。已经记过则不动文件。"""
    if not _enabled():
        return
    uid = _uid(user_id)
    if uid is None or uid in _exempt:
        return
    with _lock:
        row = _bucket_locked(uid)
        if row.get("feedback"):
            return
        row["feedback"] = True
        _save_locked()


def consume(user, feature: str) -> None:
    """占用一次批改 / 教案 / 变式。已用完时抛 TrialLimited，不增加计数。"""
    if not _enabled() or feature not in _FEATURES:
        return
    if (getattr(user, "role", "") or "") == "admin":
        remember_admin(getattr(user, "id", None))
        return
    uid = _uid(getattr(user, "id", None))
    if uid is None:
        raise TrialLimited(MSG_DONE)
    with _lock:
        if uid in _exempt:
            return
        row = _bucket_locked(uid)
        _reject_if_over(row, feature)
        row[feature] = int(row.get(feature) or 0) + 1
        _save_locked()


async def unlock_if_feedback_today(db, user_id) -> None:
    """库里当天有意见时，打开第二档。"""
    uid = _uid(user_id)
    if uid is None or not _enabled():
        return
    from sqlalchemy import select
    from models import Feedback
    rows = (await db.execute(
        select(Feedback.created_at)
        .where(Feedback.user_id == uid)
        .order_by(Feedback.created_at.desc())
        .limit(30)
    )).scalars().all()
    today = _today()
    if any(_beijing_day(dt) == today for dt in rows):
        mark_feedback(uid)


def _beijing_day(dt) -> str:
    if dt is None:
        return ""
    if getattr(dt, "tzinfo", None) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_TZ).date().isoformat()


async def enforce(user, feature: str, db=None) -> None:
    from fastapi import HTTPException
    if db is not None:
        await unlock_if_feedback_today(db, getattr(user, "id", None))
    try:
        consume(user, feature)
    except TrialLimited as exc:
        raise HTTPException(status_code=429, detail=str(exc))


def before_call(teacher_id) -> None:
    """每次真正发起模型调用之前检查频率和当日 token。"""
    if not _enabled():
        return
    uid = _uid(teacher_id)
    if uid is not None and uid in _exempt:
        return
    key = uid if uid is not None else "anon"
    now = time.monotonic()
    with _lock:
        recent = [t for t in _calls.get(key, []) if now - t < 60]
        if len(recent) >= _per_minute():
            _calls[key] = recent
            raise TrialLimited(MSG_DONE)
        recent.append(now)
        _calls[key] = recent
        if uid is None:
            return
        row = _bucket_locked(uid)
        _reject_if_over(row)


def add_tokens(teacher_id, tokens: int) -> None:
    if not _enabled():
        return
    uid = _uid(teacher_id)
    if uid is None or uid in _exempt:
        return
    amount = int(tokens or 0)
    if amount <= 0:
        return
    with _lock:
        row = _bucket_locked(uid)
        row["tokens"] = int(row.get("tokens") or 0) + amount
        _save_locked()


def daily_usage() -> list:
    """当天各账号已用掉的额度。只给管理员接口用。"""
    if not _enabled():
        return []
    with _lock:
        _load_locked()
        items = []
        for key, row in _usage.get("users", {}).items():
            if not isinstance(row, dict):
                continue
            try:
                uid = int(key)
            except (TypeError, ValueError):
                continue
            items.append({
                "user_id": uid,
                "tokens": int(row.get("tokens") or 0),
                "grade": int(row.get("grade") or 0),
                "lessonplan": int(row.get("lessonplan") or 0),
                "variant": int(row.get("variant") or 0),
                "feedback": bool(row.get("feedback")),
            })
        return items


def quota_caps() -> dict:
    from config import settings
    return {
        "base": _caps(False),
        "extended": _caps(True),
        "per_minute": int(settings.TRIAL_CALLS_PER_MINUTE),
    }


async def load_admin_exemptions() -> None:
    """启动时记住管理员，后台任务里的模型调用也不占用体验额度。"""
    if not _enabled():
        return
    try:
        from sqlalchemy import select
        from database import AsyncSessionLocal
        from models import User
        async with AsyncSessionLocal() as db:
            ids = (await db.execute(select(User.id).where(User.role == "admin"))).scalars().all()
        for user_id in ids:
            remember_admin(user_id)
    except Exception:  # noqa: BLE001
        return


async def load_today_feedback() -> None:
    """重启后仍承认今天已经提交过的意见。"""
    if not _enabled():
        return
    try:
        from sqlalchemy import select
        from database import AsyncSessionLocal
        from models import Feedback
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(
                select(Feedback.user_id, Feedback.created_at).order_by(Feedback.id.desc()).limit(500)
            )).all()
        today = _today()
        for user_id, created_at in rows:
            if _beijing_day(created_at) == today:
                mark_feedback(user_id)
    except Exception:  # noqa: BLE001
        return


def reset_for_tests() -> None:
    global _usage
    with _lock:
        _exempt.clear()
        _calls.clear()
        _usage = {"day": "", "users": {}}
        path = _store_path()
        if path.exists():
            path.unlink()
