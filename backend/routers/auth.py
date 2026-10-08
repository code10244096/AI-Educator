"""账号：登录 / 退出 / 当前用户 / 修改资料 / 修改密码（账号由管理员用 manage.py 开通，不开放注册）

公测开启时，POST /auth/enter 会为没有会话的访客自动开通一个体验账号。
"""
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
    GUEST_USERNAME_PREFIX,
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


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    school: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class _GuestLimiter:
    """同一 IP 每小时最多新开若干个体验账号，避免脚本刷库。已有会话不会计次。"""

    WINDOW = 60 * 60
    MAX_CREATES = 30

    def __init__(self) -> None:
        self._hits: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def too_many(self, ip: str) -> bool:
        now = time.time()
        with self._lock:
            recent = [t for t in self._hits.get(ip, []) if now - t < self.WINDOW]
            if len(recent) >= self.MAX_CREATES:
                self._hits[ip] = recent
                return True
            recent.append(now)
            self._hits[ip] = recent
            return False


_guest_limiter = _GuestLimiter()


def _client_ip(request: Request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@router.post("/auth/enter")
async def enter(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """进入应用。已有会话则直接返回；公测开启且没有会话时，新建一个体验老师并写入 Cookie。"""
    try:
        user = await _authenticate(request, db)
        return {**user_to_dict(user), "public_beta": bool(settings.PUBLIC_BETA)}
    except HTTPException:
        pass

    if not settings.PUBLIC_BETA:
        raise HTTPException(status_code=401, detail=MSG_NOT_LOGGED_IN)

    ip = _client_ip(request)
    if _guest_limiter.too_many(ip):
        raise HTTPException(status_code=429, detail="体验人数较多，请稍后再试")

    username = GUEST_USERNAME_PREFIX + secrets.token_hex(8)
    user = User(
        username=username,
        display_name="体验老师",
        role="teacher",
        password_hash=hash_password(secrets.token_urlsafe(24)),
        must_change_password=False,
        is_active=True,
        session_version=0,
        last_login_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    set_session_cookie(response, user)
    return {**user_to_dict(user), "public_beta": True}


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
