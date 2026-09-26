"""第 1 轮验收测试共用工具（测试 agent 维护）。

约定（与开发确认，见 docs/product/test-plan-r1.md §1.3）：
- 开通账号：`python backend/manage.py create-user --username U --name N [--role admin] [--school S]
  [--password P] [--no-force-change]`，输出固定含一行 `初始密码: <pwd>`；
  也可 `from manage import create_user` → `(user_id, password)`（同步，自己开 sqlite 连接）。
- 会话 Cookie 名 `aiedu_session`；`settings.SESSION_EXPIRE_MINUTES` 签发时读取；
  `auth.create_access_token(user_id, expires_delta=...)` 可造过期 token；也接受 `Authorization: Bearer`。
- must_change_password=true 的账号，除 /api/auth/* 外业务接口 403 “请先修改初始密码”。
- 公开接口：`/`、`/health`、`POST /api/auth/login`、`POST /api/auth/logout`（未登录也 200）。
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx
import pytest

ACCEPTANCE_DIR = Path(__file__).resolve().parent
TESTS_DIR = ACCEPTANCE_DIR.parent
BACKEND = TESTS_DIR.parent
REPO = BACKEND.parent
FRONTEND = REPO / "frontend"
FRONTEND_SRC = FRONTEND / "src"

SESSION_COOKIE = "aiedu_session"
NEW_PASSWORD = "Qa2026abcd"          # 合规：≥8 位，含字母和数字
INITIAL_PASSWORD = "Init2026qa"
GENERIC_LOGIN_ERROR = "账号或密码错误"


# ------------------------------------------------------------------ small utils

def uniq(prefix: str = "qa") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def items_of(body: Any) -> List[Dict[str, Any]]:
    """Lists come back either as a bare array or as {"items": [...]}."""
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for k in ("items", "data", "results"):
            if isinstance(body.get(k), list):
                return body[k]
    return []


def db_path_from_url(url: Optional[str] = None) -> Path:
    url = url or os.environ["DATABASE_URL"]
    return Path(re.sub(r"^sqlite(\+aiosqlite)?:///", "", url))


def sql(query: str, params: Iterable = (), db: Optional[Path] = None) -> List[tuple]:
    con = sqlite3.connect(str(db or db_path_from_url()), timeout=30)
    try:
        return con.execute(query, tuple(params)).fetchall()
    finally:
        con.close()


def table_columns(table: str, db: Optional[Path] = None) -> List[str]:
    return [r[1] for r in sql(f"PRAGMA table_info({table})", db=db)]


def require_route(app, path: str, method: str = "GET"):
    """xfail (待开发) when a route promised by the PRD is not registered yet."""
    from fastapi.routing import APIRoute
    for r in app.routes:
        if isinstance(r, APIRoute) and r.path == path and method.upper() in r.methods:
            return
    pytest.xfail(f"待开发：{method} {path} 未注册")


# ------------------------------------------------------------------ accounts

def manage_available() -> bool:
    return (BACKEND / "manage.py").exists()


def run_manage(*args: str, env: Optional[Dict[str, str]] = None, timeout: int = 120) -> subprocess.CompletedProcess:
    if not manage_available():
        pytest.xfail("待开发：backend/manage.py 不存在")
    full_env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})}
    return subprocess.run([sys.executable, str(BACKEND / "manage.py"), *args], cwd=str(BACKEND), env=full_env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def parse_initial_password(output: str) -> Optional[str]:
    m = re.findall(r"初始密码\s*[:：]\s*(\S+)", output)
    return m[-1] if m else None


def create_user(username: str, name: str, *, role: str = "teacher", school: Optional[str] = None,
                password: Optional[str] = None, must_change_password: bool = False) -> Tuple[int, str]:
    """In-process call of manage.create_user (fast path for fixtures)."""
    if not manage_available():
        pytest.xfail("待开发：backend/manage.py 不存在")
    import importlib
    manage = importlib.import_module("manage")
    fn = getattr(manage, "create_user", None)
    if fn is None:
        pytest.xfail("待开发：manage.create_user 不存在")
    res = fn(username, name, role=role, school=school, password=password,
             must_change_password=must_change_password)
    if asyncio.iscoroutine(res):  # pragma: no cover - contract says sync
        raise AssertionError("manage.create_user 应为同步函数（与开发约定）")
    uid, pwd = res
    return int(uid), pwd


def make_client(app, *, base_url: str = "http://testserver", headers: Optional[Dict[str, str]] = None) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url=base_url, timeout=60, headers=headers or {})


async def login(c: httpx.AsyncClient, username: str, password: str) -> httpx.Response:
    r = await c.post("/api/auth/login", json={"username": username, "password": password})
    if r.status_code == 404 and r.json().get("detail") == "Not Found":
        pytest.xfail("待开发：POST /api/auth/login 未实现")
    if r.status_code == 422:  # form-encoded variant
        r = await c.post("/api/auth/login", data={"username": username, "password": password})
    return r


async def change_password(c: httpx.AsyncClient, old: str, new: str) -> httpx.Response:
    r = await c.post("/api/auth/change-password", json={"old_password": old, "new_password": new})
    if r.status_code == 422:
        r = await c.post("/api/auth/change-password", data={"old_password": old, "new_password": new})
    return r


class Teacher:
    def __init__(self, client: httpx.AsyncClient, username: str, password: str, user: Dict[str, Any], role: str):
        self.client = client
        self.username = username
        self.password = password
        self.user = user
        self.role = role

    @property
    def id(self) -> int:
        return int(self.user["id"])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Teacher {self.username} id={self.user.get('id')} role={self.role}>"


class TeacherFactory:
    def __init__(self, app):
        self.app = app
        self.clients: List[httpx.AsyncClient] = []

    def client(self, **kw) -> httpx.AsyncClient:
        c = make_client(self.app, **kw)
        self.clients.append(c)
        return c

    async def __call__(self, *, role: str = "teacher", name: Optional[str] = None,
                       username: Optional[str] = None, school: Optional[str] = None) -> Teacher:
        username = username or uniq("t" if role == "teacher" else "admin")
        name = name or ("测试管理员" if role == "admin" else f"测试老师{username[-4:]}")
        _uid, pwd = create_user(username, name, role=role, school=school, password=NEW_PASSWORD,
                                must_change_password=False)
        c = self.client()
        r = await login(c, username, pwd)
        assert r.status_code == 200, f"login {username} -> {r.status_code} {r.text[:300]}"
        return Teacher(c, username, pwd, r.json(), role)

    async def aclose(self):
        for c in self.clients:
            await c.aclose()


# ------------------------------------------------------------------ domain helpers

def class_key(cls: Dict[str, Any]) -> str:
    """URL key of a class. Group ③ may switch from slug `class{id}` to the numeric id."""
    return str(cls.get("slug") or cls["id"])


async def create_class(c: httpx.AsyncClient, name: Optional[str] = None, grade: str = "高一") -> Dict[str, Any]:
    r = await c.post("/api/class", json={"name": name or uniq("验收班"), "grade": grade, "subject": "数学"})
    assert r.status_code in (200, 201), f"create class -> {r.status_code} {r.text[:300]}"
    return r.json()


async def add_member(c: httpx.AsyncClient, ck: str, name: str, student_no: Optional[str] = None,
                     gender: str = "男") -> Dict[str, Any]:
    body = {"name": name, "gender": gender}
    if student_no:
        body["student_no"] = student_no
    r = await c.post(f"/api/class/{ck}/members", json=body)
    assert r.status_code in (200, 201), f"add member -> {r.status_code} {r.text[:300]}"
    return r.json()


async def import_members(c: httpx.AsyncClient, ck: str, text: str) -> httpx.Response:
    return await c.post(f"/api/class/{ck}/members/import", data={"text": text})


async def create_homework(c: httpx.AsyncClient, ck: str, title: Optional[str] = None,
                          reference_answer: Optional[str] = "1. 2\n2. 4\n3. 6") -> Dict[str, Any]:
    body: Dict[str, Any] = {"title": title or uniq("验收作业"), "subject": "数学"}
    if reference_answer is not None:
        body["reference_answer"] = reference_answer
    r = await c.post(f"/api/class/{ck}/homework", json=body)
    assert r.status_code in (200, 201), f"create homework -> {r.status_code} {r.text[:300]}"
    return r.json()


def hw_key(hw: Dict[str, Any]) -> str:
    """After group ③ the URL id must equal the primary key (`assignment_id`)."""
    return str(hw.get("assignment_id") or hw["id"])


SAMPLE_MD = "### 1. 填空题\n1+1=?\n\n**学生答案**：2\n\n---\n\n### 2. 填空题\n2+2=?\n\n**学生答案**：5\n"


async def upload(c: httpx.AsyncClient, *, files: Optional[List[Tuple[str, bytes, str]]] = None,
                 assignment_id: Optional[int] = None, member_id: Optional[int] = None,
                 student_name: Optional[str] = None, submission_id: Optional[int] = None,
                 reference_answer: Optional[str] = None, wait: bool = False) -> httpx.Response:
    files = files or [("作业.md", SAMPLE_MD.encode("utf-8"), "text/markdown")]
    data: Dict[str, str] = {}
    for k, v in (("assignment_id", assignment_id), ("member_id", member_id), ("student_name", student_name),
                 ("submission_id", submission_id), ("reference_answer", reference_answer)):
        if v is not None:
            data[k] = str(v)
    if wait:
        data["wait"] = "true"
    return await c.post("/api/grader/upload", files=[("files", f) for f in files], data=data)


async def wait_submission(c: httpx.AsyncClient, sid: int, timeout: float = 30.0) -> Dict[str, Any]:
    from helpers import poll_url
    return await poll_url(c, f"/api/grader/{sid}", timeout=timeout)


async def graded_submission(c: httpx.AsyncClient, **kw) -> Dict[str, Any]:
    r = await upload(c, **kw)
    assert r.status_code in (200, 202), f"upload -> {r.status_code} {r.text[:300]}"
    return await wait_submission(c, int(r.json()["submission_id"]))


async def drain_jobs(timeout: float = 30):
    try:
        import jobs
    except ImportError:  # pragma: no cover
        return
    await jobs.wait_all_jobs(timeout=timeout)


# ------------------------------------------------------------------ subprocess runner

def run_runner(action: str, env: Dict[str, str], timeout: int = 180, extra: Optional[Dict[str, Any]] = None
               ) -> Tuple[subprocess.CompletedProcess, Optional[Dict[str, Any]]]:
    """Run acceptance/_qa_runner.py in a clean interpreter. Returns (proc, RESULT json or None)."""
    base = {k: v for k, v in os.environ.items()
            if k not in ("APP_ENV", "JWT_SECRET", "CORS_ORIGINS", "SEED_DEMO_DATA", "SESSION_EXPIRE_MINUTES")}
    full_env = {**base, "PYTHONIOENCODING": "utf-8", **env}
    if extra is not None:
        full_env["QA_EXTRA"] = json.dumps(extra, ensure_ascii=False)
    p = subprocess.run([sys.executable, str(ACCEPTANCE_DIR / "_qa_runner.py"), action], cwd=str(BACKEND),
                       env=full_env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout)
    result = None
    for line in p.stdout.splitlines():
        if line.startswith("RESULT:"):
            result = json.loads(line[len("RESULT:"):])
    return p, result


def fresh_env(tmp: Path, **overrides: str) -> Dict[str, str]:
    """Env for a brand-new data directory (never touches backend/teaching_assistant.db or api_runs/)."""
    (tmp / "uploads").mkdir(parents=True, exist_ok=True)
    env = {
        "DATABASE_URL": f"sqlite+aiosqlite:///{(tmp / 'qa.db').as_posix()}",
        "UPLOAD_DIR": str(tmp / "uploads"),
        "API_OUTPUT_ROOT": str(tmp / "api_runs"),
        "LLM_API_KEY": "your_api_key_here",
    }
    env.update(overrides)
    return env


PROD_JWT = "qa-prod-secret-" + "x" * 40
PROD_LLM_KEY = "sk-qa-dummy-key-0000000000000000"


def prod_env(tmp: Path, **overrides: str) -> Dict[str, str]:
    base = {"APP_ENV": "production", "JWT_SECRET": PROD_JWT, "LLM_API_KEY": PROD_LLM_KEY,
            "CORS_ORIGINS": "https://school.example.com"}
    base.update(overrides)
    return fresh_env(tmp, **base)


def copy_real_db(dst: Path) -> Path:
    """Consistent read-only copy of backend/teaching_assistant.db (source opened with mode=ro)."""
    src = BACKEND / "teaching_assistant.db"
    if not src.exists():
        pytest.skip("backend/teaching_assistant.db 不存在")
    s = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True)
    d = sqlite3.connect(str(dst))
    try:
        s.backup(d)
    finally:
        d.close()
        s.close()
    return dst


# ------------------------------------------------------------------ frontend static checks

def frontend_files(exts=(".js", ".jsx", ".ts", ".tsx")) -> List[Path]:
    return [p for p in FRONTEND_SRC.rglob("*") if p.suffix in exts and "node_modules" not in p.parts]


def grep_frontend(pattern: str, flags: int = 0, exts=(".js", ".jsx", ".ts", ".tsx", ".html", ".css")
                  ) -> List[Tuple[str, int, str]]:
    rx = re.compile(pattern, flags)
    hits = []
    for p in frontend_files(exts):
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if rx.search(line):
                hits.append((str(p.relative_to(REPO)).replace("\\", "/"), i, line.strip()[:160]))
    return hits


def strip_js_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(^|[^:])//[^\n]*", r"\1", text)
    text = re.sub(r"\{/\*.*?\*/\}", "", text, flags=re.S)
    return text
