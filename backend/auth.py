"""
登录鉴权：密码哈希（bcrypt）、会话令牌（JWT，存 httpOnly Cookie）、当前用户依赖、登录限流。

- 会话 Cookie 名 `aiedu_session`（httpOnly、SameSite=Lax，生产环境 Secure）；也接受 `Authorization: Bearer <token>`。
- 令牌内带 `sv`（users.session_version）：改密 / 重置密码 / 停用账号时 +1，旧会话立即失效。
- 业务接口统一挂 `current_user`：未登录 401；账号仍是初始密码（must_change_password）时 403，
  只允许访问 /api/auth/*（查看自己、改密、退出）。
- 运维接口挂 `require_admin`：非管理员 403。
"""
import math
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import bcrypt
from fastapi import Depends, HTTPException, Request
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import User

SESSION_COOKIE = "aiedu_session"
_BCRYPT_MAX_BYTES = 72

PASSWORD_RULE = "新密码至少 8 位，且需同时包含字母和数字"
MSG_NOT_LOGGED_IN = "请先登录"
MSG_EXPIRED = "登录已过期，请重新登录"
MSG_MUST_CHANGE = "请先修改初始密码"
MSG_ADMIN_ONLY = "仅管理员可访问"
MSG_BAD_CREDENTIALS = "账号或密码错误"


# ==================== 密码 ====================

def hash_password(password: str) -> str:
    rounds = min(max(int(settings.BCRYPT_ROUNDS), 4), 15)
    return bcrypt.hashpw(password.encode("utf-8")[:_BCRYPT_MAX_BYTES], bcrypt.gensalt(rounds)).decode("ascii")


def is_bcrypt_hash(password_hash: Optional[str]) -> bool:
    """真实账号的密码一律是 bcrypt 哈希；历史占位账号（如 'hashed'）不是，无法登录"""
    return bool(password_hash) and password_hash.startswith(("$2a$", "$2b$", "$2y$"))


def verify_password(password: str, password_hash: Optional[str]) -> bool:
    if not password or not is_bcrypt_hash(password_hash):
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:_BCRYPT_MAX_BYTES], password_hash.encode("ascii"))
    except ValueError:
        return False


# 不存在的账号也做一次同等耗时的校验，避免通过响应时间判断账号是否存在
_DUMMY_HASH = hash_password("dummy-password-0")


def check_password_for_timing() -> None:
    verify_password("dummy-password-1", _DUMMY_HASH)


def validate_new_password(password: Optional[str]) -> Optional[str]:
    """新密码规则：8~64 位，同时包含字母和数字。合规返回 None，否则返回中文原因"""
    password = password or ""
    if len(password) < 8:
        return PASSWORD_RULE
    if len(password) > 64:
        return "新密码不能超过 64 位"
    if not any(c.isascii() and c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        return PASSWORD_RULE
    return None


# ==================== 令牌 ====================

def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None,
                        session_version: Optional[int] = None) -> str:
    """签发会话令牌；有效期默认读取 settings.SESSION_EXPIRE_MINUTES（运行时修改立即生效）"""
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.SESSION_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "sv": int(session_version or 0),
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def set_session_cookie(response, user: User) -> None:
    token = create_access_token(user.id, session_version=user.session_version or 0)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(settings.SESSION_EXPIRE_MINUTES * 60),
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=settings.COOKIE_SECURE)


def _token_from_request(request: Request) -> Optional[str]:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        return token
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return None


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "school": user.school or "",
        "role": user.role or "teacher",
        "must_change_password": bool(user.must_change_password),
    }


# ==================== 依赖 ====================

async def _authenticate(request: Request, db: AsyncSession) -> User:
    token = _token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail=MSG_NOT_LOGGED_IN)
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail=MSG_EXPIRED)
    except JWTError:
        raise HTTPException(status_code=401, detail=MSG_EXPIRED)
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail=MSG_EXPIRED)
    user = await db.get(User, user_id)
    if (
        not user
        or user.is_active is False
        or not is_bcrypt_hash(user.password_hash)
        or int(payload.get("sv", 0)) != int(user.session_version or 0)
    ):
        raise HTTPException(status_code=401, detail=MSG_EXPIRED)
    request.state.user_id = user.id
    return user


async def current_user_allow_pending(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """已登录即可（包括还没改初始密码的账号）：仅用于 /api/auth/* """
    return await _authenticate(request, db)


async def current_user(user: User = Depends(current_user_allow_pending)) -> User:
    """业务接口使用：已登录且已设置自己的密码"""
    if user.must_change_password:
        raise HTTPException(status_code=403, detail=MSG_MUST_CHANGE)
    return user


async def require_admin(user: User = Depends(current_user)) -> User:
    if (user.role or "") != "admin":
        raise HTTPException(status_code=403, detail=MSG_ADMIN_ONLY)
    return user


# ==================== 登录限流 ====================

class LoginLimiter:
    """
    同一账号（按输入的账号字符串，不区分是否存在）在 WINDOW 秒内失败 MAX_FAILURES 次，锁定 LOCK_SECONDS 秒。
    单进程内存实现（部署为单个后端进程）；重启后计数清零。
    """

    WINDOW = 5 * 60
    MAX_FAILURES = 10
    LOCK_SECONDS = 15 * 60

    def __init__(self) -> None:
        self._failures: Dict[str, List[float]] = {}
        self._locked_until: Dict[str, float] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(username: str) -> str:
        return (username or "").strip().lower()

    def locked_seconds(self, username: str) -> int:
        key = self._key(username)
        with self._lock:
            until = self._locked_until.get(key)
            if not until:
                return 0
            remaining = until - time.time()
            if remaining <= 0:
                self._locked_until.pop(key, None)
                self._failures.pop(key, None)
                return 0
            return int(math.ceil(remaining))

    def record_failure(self, username: str) -> None:
        key = self._key(username)
        now = time.time()
        with self._lock:
            recent = [t for t in self._failures.get(key, []) if now - t < self.WINDOW]
            recent.append(now)
            self._failures[key] = recent
            if len(recent) >= self.MAX_FAILURES:
                self._locked_until[key] = now + self.LOCK_SECONDS
                self._failures[key] = []

    def record_success(self, username: str) -> None:
        key = self._key(username)
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
            self._locked_until.clear()


login_limiter = LoginLimiter()


def lockout_message(seconds: int) -> str:
    minutes = max(1, int(math.ceil(seconds / 60)))
    return f"尝试次数过多，请 {minutes} 分钟后再试"
