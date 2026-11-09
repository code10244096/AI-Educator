"""身份选择页访客埋点：统计每天「我是学生 / 我是教师」点击次数。

供管理端评估学生版需求热度。按北京时间自然日计数，最多保留 90 天。
"""
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

ROLES = ("student", "teacher")
_KEEP_DAYS = 90
_TZ = timezone(timedelta(hours=8))

_lock = threading.Lock()
_counts = {}  # day -> {"student": int, "teacher": int}

router = APIRouter()


def _path() -> Path:
    from config import settings
    return Path(settings.STUDENT_TRACK_FILE)


def _today() -> str:
    return datetime.now(_TZ).date().isoformat()


def _load_locked() -> None:
    global _counts
    try:
        raw = json.loads(_path().read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            _counts = {
                str(day): {"student": int(row.get("student") or 0), "teacher": int(row.get("teacher") or 0)}
                for day, row in raw.items()
                if isinstance(row, dict)
            }
    except (OSError, json.JSONDecodeError):
        _counts = {}


def _save_locked() -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_counts, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def track(role: str) -> None:
    if role not in ROLES:
        return
    with _lock:
        _load_locked()
        day = _today()
        row = _counts.setdefault(day, {"student": 0, "teacher": 0})
        row[role] = int(row.get(role) or 0) + 1
        # 只保留最近 _KEEP_DAYS 天，防止文件无限增长
        cutoff = (datetime.now(_TZ).date() - timedelta(days=_KEEP_DAYS)).isoformat()
        for old in [d for d in _counts if d < cutoff]:
            del _counts[old]
        _save_locked()


def stats() -> dict:
    """今日 + 最近 30 天按天的身份点击数，给管理端展示。"""
    with _lock:
        _load_locked()
        day = _today()
        today = _counts.get(day, {"student": 0, "teacher": 0})
        days = [
            {"day": d, **{r: int(_counts[d].get(r) or 0) for r in ROLES}}
            for d in sorted(_counts, reverse=True)[:30]
        ]
        return {"today": {"day": day, **{r: int(today.get(r) or 0) for r in ROLES}}, "days": days}


def reset_for_tests() -> None:
    global _counts
    with _lock:
        _counts = {}
        path = _path()
        if path.exists():
            path.unlink()


class RoleHit(BaseModel):
    role: str


@router.post("/track/role")
async def track_role(hit: RoleHit):
    """身份选择页埋点（未登录可访问）。只计数，不收集任何个人信息。"""
    role = (hit.role or "").strip().lower()
    if role not in ROLES:
        raise HTTPException(status_code=422, detail="role 必须是 student 或 teacher")
    track(role)
    return {"ok": True}
