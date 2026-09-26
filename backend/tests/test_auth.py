"""R1-001 账号：登录 / 退出 / 改密 / 限流 / 会话过期 / 管理命令；R1-002 未登录一律 401；R1-003 运维接口仅管理员。"""
import os
import re
import sqlite3
import subprocess
import sys
import uuid
from datetime import timedelta

import pytest

from testenv import BACKEND_DIR, TEST_DB

PUBLIC_ROUTES = {("POST", "/api/auth/login"), ("POST", "/api/auth/logout")}


def _concrete(path: str) -> str:
    path = path.replace("{class_slug}", "class1")
    return re.sub(r"\{[^}]+\}", "1", path)


def _api_routes(app):
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None) or set()
        if not path.startswith("/api"):
            continue
        for m in sorted(methods - {"HEAD", "OPTIONS"}):
            yield m, path


async def test_every_api_route_requires_login(app, anon_client):
    checked = 0
    failures = []
    for method, path in _api_routes(app):
        if (method, path) in PUBLIC_ROUTES:
            continue
        r = await anon_client.request(method, _concrete(path))
        checked += 1
        if r.status_code != 401:
            failures.append(f"{method} {path} -> {r.status_code}")
    assert checked > 40
    assert not failures, failures


async def test_public_endpoints(anon_client):
    assert (await anon_client.get("/health")).status_code == 200
    assert (await anon_client.post("/api/auth/logout")).status_code == 200
    r = await anon_client.get("/api/auth/me")
    assert r.status_code == 401 and r.json()["detail"] == "请先登录"


async def test_login_success_sets_httponly_cookie_and_hashes_password(app, anon_client):
    import manage
    username = f"1380000{uuid.uuid4().int % 10000:04d}"
    uid, pwd = manage.create_user(username, "王老师", school="实验中学")
    assert re.fullmatch(r"[A-Za-z0-9]{10}", pwd) and re.search(r"\d", pwd) and re.search(r"[A-Za-z]", pwd)
    con = sqlite3.connect(TEST_DB)
    h = con.execute("SELECT password_hash FROM users WHERE id=?", (uid,)).fetchone()[0]
    con.close()
    assert h.startswith("$2b$")

    r = await anon_client.post("/api/auth/login", json={"username": username, "password": pwd})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {"id": uid, "username": username, "display_name": "王老师", "school": "实验中学",
                    "role": "teacher", "must_change_password": True}
    set_cookie = r.headers["set-cookie"].lower()
    assert "aiedu_session=" in set_cookie and "httponly" in set_cookie and "samesite=lax" in set_cookie
    # 初始密码：只能访问账号接口，业务接口 403
    assert (await anon_client.get("/api/auth/me")).json()["must_change_password"] is True
    r = await anon_client.get("/api/class/list")
    assert r.status_code == 403 and r.json()["detail"] == "请先修改初始密码"

    r = await anon_client.post("/api/auth/change-password",
                               json={"old_password": pwd, "new_password": "NewPass2026"})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["must_change_password"] is False
    assert (await anon_client.get("/api/class/list")).status_code == 200, "当前会话改密后自动续期"


@pytest.mark.parametrize("username,password", [("pytest_teacher", "wrong-pass-1"), ("no_such_user_x", "whatever1")])
async def test_bad_credentials_same_message(anon_client, client, username, password):
    r = await anon_client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 401
    assert r.json()["detail"] == "账号或密码错误"


async def test_lockout_after_10_failures(anon_client, make_teacher):
    t = await make_teacher()
    username = t.user["username"]
    for _ in range(10):
        r = await anon_client.post("/api/auth/login", json={"username": username, "password": "bad-pass-1"})
        assert r.status_code == 401
    r = await anon_client.post("/api/auth/login", json={"username": username, "password": t.password})
    assert r.status_code == 429
    assert r.json()["detail"] == "尝试次数过多，请 15 分钟后再试"
    # 不存在的账号同样会被锁定（不泄露账号是否存在）
    ghost = f"ghost_{uuid.uuid4().hex[:6]}"
    for _ in range(10):
        await anon_client.post("/api/auth/login", json={"username": ghost, "password": "bad-pass-1"})
    assert (await anon_client.post("/api/auth/login", json={"username": ghost, "password": "x"})).status_code == 429


async def test_logout_invalidates_browser_session(make_teacher):
    t = await make_teacher()
    assert (await t.get("/api/class/list")).status_code == 200
    r = await t.post("/api/auth/logout")
    assert r.status_code == 200
    assert (await t.get("/api/class/list")).status_code == 401
    assert (await t.get("/api/auth/me")).status_code == 401


async def test_expired_session_returns_401(app, make_teacher, anon_client):
    import auth
    from config import settings
    t = await make_teacher()
    expired = auth.create_access_token(t.user["id"], expires_delta=timedelta(seconds=-5))
    r = await anon_client.get("/api/class/list", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401 and r.json()["detail"] == "登录已过期，请重新登录"
    # 有效期配置在签发时读取
    old = settings.SESSION_EXPIRE_MINUTES
    settings.SESSION_EXPIRE_MINUTES = 1
    try:
        tok = auth.create_access_token(t.user["id"])
    finally:
        settings.SESSION_EXPIRE_MINUTES = old
    from jose import jwt
    payload = jwt.get_unverified_claims(tok)
    assert payload["exp"] - payload["iat"] == 60
    r = await anon_client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 401


async def test_change_password_rules_and_old_password_revoked(app, make_teacher, anon_client):
    t = await make_teacher()
    r = await t.post("/api/auth/change-password", json={"old_password": "wrong-old-1", "new_password": "Abcdefg123"})
    assert r.status_code == 400 and r.json()["detail"] == "当前密码不正确"
    for weak in ("short1", "abcdefghij", "1234567890"):
        r = await t.post("/api/auth/change-password", json={"old_password": t.password, "new_password": weak})
        assert r.status_code == 400 and "8 位" in r.json()["detail"] and "字母和数字" in r.json()["detail"]

    # 另一处登录的同一账号，改密后旧会话失效
    from helpers import login_client, new_http_client
    second = new_http_client(app)
    try:
        await login_client(second, t.user["username"], t.password)
        r = await t.post("/api/auth/change-password", json={"old_password": t.password, "new_password": "Changed2026x"})
        assert r.status_code == 200
        assert (await t.get("/api/class/list")).status_code == 200
        assert (await second.get("/api/class/list")).status_code == 401
    finally:
        await second.aclose()
    bad = await anon_client.post("/api/auth/login", json={"username": t.user["username"], "password": t.password})
    assert bad.status_code == 401
    good = await anon_client.post("/api/auth/login", json={"username": t.user["username"], "password": "Changed2026x"})
    assert good.status_code == 200


async def test_update_profile(make_teacher):
    t = await make_teacher(name="旧名字")
    r = await t.put("/api/auth/me", json={"display_name": "  新名字 ", "school": "第一中学"})
    assert r.status_code == 200
    assert r.json()["display_name"] == "新名字" and r.json()["school"] == "第一中学"
    assert (await t.get("/api/auth/me")).json()["display_name"] == "新名字"
    assert (await t.put("/api/auth/me", json={"display_name": "  "})).status_code == 400
    assert (await t.put("/api/auth/me", json={"username": "hack"})).json()["username"] == t.user["username"]


async def test_disabled_user_cannot_login_and_session_revoked(make_teacher, anon_client):
    import manage
    t = await make_teacher()
    manage.disable_user(t.user["username"])
    assert (await t.get("/api/auth/me")).status_code == 401
    r = await anon_client.post("/api/auth/login", json={"username": t.user["username"], "password": t.password})
    assert r.status_code == 401 and r.json()["detail"] == "账号或密码错误"
    manage.enable_user(t.user["username"])
    r = await anon_client.post("/api/auth/login", json={"username": t.user["username"], "password": t.password})
    assert r.status_code == 200


async def test_reset_password_forces_change(make_teacher, anon_client):
    import manage
    t = await make_teacher()
    new_pwd = manage.reset_password(t.user["username"])
    assert (await t.get("/api/auth/me")).status_code == 401, "重置后旧会话失效"
    r = await anon_client.post("/api/auth/login", json={"username": t.user["username"], "password": new_pwd})
    assert r.status_code == 200 and r.json()["must_change_password"] is True


async def test_usage_is_admin_only(make_teacher):
    teacher = await make_teacher()
    admin = await make_teacher(role="admin")
    for path in ("/api/usage/summary", "/api/usage/calls"):
        r = await teacher.get(path)
        assert r.status_code == 403 and r.json()["detail"] == "仅管理员可访问"
        assert (await admin.get(path)).status_code == 200


def test_manage_errors():
    import manage
    with pytest.raises(manage.ManageError):
        manage.create_user("pytest_teacher", "重复")  # 已存在
    with pytest.raises(manage.ManageError):
        manage.create_user("has space", "x")
    with pytest.raises(manage.ManageError):
        manage.create_user(f"u{uuid.uuid4().hex[:6]}", "x", password="weak")
    with pytest.raises(manage.ManageError):
        manage.reset_password("no_such_user_zz")
    users = manage.list_users()
    assert any(u["username"] == "pytest_teacher" and u["can_login"] for u in users)


@pytest.mark.slow
def test_manage_cli_create_user_prints_initial_password(test_tmp):
    db = test_tmp / "cli.db"
    env = dict(os.environ, DATABASE_URL=f"sqlite+aiosqlite:///{db.as_posix()}", PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(BACKEND_DIR / "manage.py"), "create-user",
                        "--username", "13800000001", "--name", "王老师"],
                       env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert p.returncode == 0, p.stderr
    m = re.search(r"^初始密码: (\S+)$", p.stdout, re.MULTILINE)
    assert m, p.stdout
    p2 = subprocess.run([sys.executable, str(BACKEND_DIR / "manage.py"), "create-user",
                         "--username", "13800000001", "--name", "王老师"],
                        env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert p2.returncode == 1 and "账号已存在" in p2.stderr
    p3 = subprocess.run([sys.executable, str(BACKEND_DIR / "manage.py"), "list-users"],
                        env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert "13800000001" in p3.stdout and "待修改初始密码" in p3.stdout
