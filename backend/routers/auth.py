"""账号：登录 / 退出 / 当前用户 / 修改资料 / 修改密码。

公测开启时，访客用手机号领取 6 位注册码，再用手机号和注册码登录。
管理员账号仍由 manage.py 开通，不走注册码。
"""
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import (
    MSG_BAD_CREDENTIALS,
    MSG_NOT_LOGGED_IN,
    _authenticate,
    check_password_for_timing,
    clear_session_cookie,
    current_user,
    current_user_allow_pending,
    hash_password,
    lockout_message,
    login_limiter,
    set_session_cookie,
    user_to_dict,
    validate_new_password,
    verify_password,
)
from config import settings
from database import get_db
from models import User

router = APIRouter()


class LoginBody(BaseModel):
    username: str
    password: str


class PhoneCodeBody(BaseModel):
    phone: str


_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    school: Optional[str] = None
    education_stage: Optional[str] = None
    subject: Optional[str] = None


STAGE_SUBJECTS = {
    "小学": ("语文", "数学", "英语", "科学"),
    "初中": ("语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史", "地理"),
    "高中": ("语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史", "地理"),
    "大学": ("数学", "大学物理", "大学化学", "大学英语", "计算机", "大学语文", "经济学", "管理学"),
}
class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class _PhoneCodeLimiter:
    """同一手机号、同一 IP 每小时最多领取几次注册码。"""

    WINDOW = 60 * 60
    MAX_PER_PHONE = 8
    MAX_PER_IP = 20

    def __init__(self) -> None:
        self._hits: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def too_many(self, key: str, limit: int) -> bool:
        now = time.time()
        with self._lock:
            recent = [t for t in self._hits.get(key, []) if now - t < self.WINDOW]
            if len(recent) >= limit:
                self._hits[key] = recent
                return True
            recent.append(now)
            self._hits[key] = recent
            return False


_phone_code_limiter = _PhoneCodeLimiter()


def _normalize_phone(raw: str) -> str:
    return re.sub(r"[\s\-]", "", (raw or "").strip())


def _new_login_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _client_ip(request: Request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@router.post("/auth/enter")
async def enter(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """已有会话则返回当前用户。没有会话时不再自动建号，请改用手机号注册码登录。"""
    try:
        user = await _authenticate(request, db)
        return {**user_to_dict(user), "public_beta": bool(settings.PUBLIC_BETA)}
    except HTTPException:
        raise HTTPException(status_code=401, detail=MSG_NOT_LOGGED_IN)


@router.post("/auth/phone-code")
async def phone_code(body: PhoneCodeBody, request: Request, db: AsyncSession = Depends(get_db)):
    """公测：用手机号领取 6 位注册码。新号当场开通；已领过的号会换一个新码，旧码失效。"""
    if not settings.PUBLIC_BETA:
        raise HTTPException(status_code=403, detail="公测未开放，请使用已有账号登录")

    phone = _normalize_phone(body.phone)
    if not _PHONE_RE.fullmatch(phone):
        raise HTTPException(status_code=400, detail="请输入 11 位手机号")

    ip = _client_ip(request)
    if _phone_code_limiter.too_many(f"ip:{ip}", _PhoneCodeLimiter.MAX_PER_IP) or \
            _phone_code_limiter.too_many(f"phone:{phone}", _PhoneCodeLimiter.MAX_PER_PHONE):
        raise HTTPException(status_code=429, detail="获取太频繁，请稍后再试")

    user = (await db.execute(
        select(User).where(func.lower(User.username) == phone.lower())
    )).scalar_one_or_none()
    created = user is None
    if user is not None and (user.role == "admin" or (user.auth_method or "password") != "phone_code"):
        raise HTTPException(status_code=409, detail="这个账号已有密码，请直接登录")
    if user is not None and user.is_active is False:
        raise HTTPException(status_code=403, detail="这个账号已停用")

    code = _new_login_code()
    if created:
        user = User(
            username=phone,
            display_name=f"老师{phone[-4:]}",
            role="teacher",
            auth_method="phone_code",
            password_hash=hash_password(code),
            must_change_password=False,
            is_active=True,
            session_version=0,
        )
        db.add(user)
    else:
        user.password_hash = hash_password(code)
        user.session_version = int(user.session_version or 0) + 1
    await db.commit()
    return {"phone": phone, "code": code, "created": created}


@router.post("/auth/login")
async def login(body: LoginBody, response: Response, db: AsyncSession = Depends(get_db)):
    """账号密码登录，成功后写入会话 Cookie。失败统一提示“账号或密码错误”；连续失败 10 次锁定 15 分钟（429）"""
    username = (body.username or "").strip()
    locked = login_limiter.locked_seconds(username)
    if locked:
        raise HTTPException(status_code=429, detail=lockout_message(locked))

    user = None
    if username:
        user = (await db.execute(
            select(User).where(func.lower(User.username) == username.lower())
        )).scalar_one_or_none()
    if user is None:
        check_password_for_timing()
        ok = False
    else:
        ok = verify_password(body.password or "", user.password_hash) and user.is_active is not False

    if not ok:
        login_limiter.record_failure(username)
        raise HTTPException(status_code=401, detail=MSG_BAD_CREDENTIALS)

    login_limiter.record_success(username)
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    set_session_cookie(response, user)
    return user_to_dict(user)


@router.post("/auth/logout")
async def logout(response: Response):
    """退出登录：清除会话 Cookie（未登录调用也返回 200）"""
    clear_session_cookie(response)
    return {"message": "已退出登录"}


@router.get("/auth/me")
async def get_me(user: User = Depends(current_user_allow_pending)):
    """当前登录的老师"""
    return user_to_dict(user)


@router.put("/auth/me")
async def update_me(body: ProfileUpdate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    """修改个人资料：姓名、学校（账号不可修改）"""
    if body.display_name is not None:
        name = body.display_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="姓名不能为空")
        if len(name) > 50:
            raise HTTPException(status_code=400, detail="姓名不能超过 50 个字")
        user.display_name = name
    if body.school is not None:
        school = body.school.strip()
        if len(school) > 100:
            raise HTTPException(status_code=400, detail="学校名称不能超过 100 个字")
        user.school = school or None
    if body.education_stage is not None or body.subject is not None:
        stage = (body.education_stage if body.education_stage is not None else user.education_stage or "").strip()
        subject = (body.subject if body.subject is not None else user.subject or "").strip()
        if stage not in STAGE_SUBJECTS:
            raise HTTPException(status_code=400, detail="请选择学段")
        if subject not in STAGE_SUBJECTS[stage]:
            raise HTTPException(status_code=400, detail="请选择学科")
        user.education_stage = stage
        user.subject = subject
    await db.commit()
    await db.refresh(user)
    return user_to_dict(user)


@router.post("/auth/change-password")
async def change_password(
    body: PasswordChange,
    response: Response,
    user: User = Depends(current_user_allow_pending),
    db: AsyncSession = Depends(get_db),
):
    """修改密码：校验当前密码；新密码 ≥8 位且同时含字母和数字。成功后其他设备上的会话失效，当前会话自动续期"""
    if not verify_password(body.old_password or "", user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    problem = validate_new_password(body.new_password)
    if problem:
        raise HTTPException(status_code=400, detail=problem)
    if body.new_password == body.old_password:
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    user.session_version = int(user.session_version or 0) + 1
    await db.commit()
    await db.refresh(user)
    set_session_cookie(response, user)
    return {"message": "密码已修改", "user": user_to_dict(user)}
