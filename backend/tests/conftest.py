"""
Pytest bootstrap: isolate DB / uploads / call logs in a temp dir and force the
model layer offline BEFORE the application is imported.

Run from repo root:   python -m pytest backend/tests
or from backend/:     python -m pytest tests
"""
import os
import shutil
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

# 路径常量与测试环境变量在 testenv 中设置（import 即生效，必须早于导入应用）。
# 用例里请 `from testenv import ...`，不要 `from conftest import ...`：
# 子目录（如 acceptance/）也有 conftest.py，模块名 conftest 会冲突。
from testenv import (  # noqa: E402,F401
    BACKEND_DIR, DATASET_HW_DIR, GAOKAO_SCAN_DIR, REPO_ROOT,
    TEST_API_RUNS, TEST_DB, TEST_TMP, TEST_UPLOADS,
)

import asyncio  # noqa: E402
import uuid  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from fakes import FakeGateway, install_gateway, restore_gateway  # noqa: E402
from helpers import login_client, new_http_client  # noqa: E402


def _safety_check():
    from config import settings
    assert "teaching_assistant.db" not in settings.DATABASE_URL, settings.DATABASE_URL
    assert str(TEST_TMP.as_posix()) in settings.DATABASE_URL
    assert Path(settings.UPLOAD_DIR).resolve() == TEST_UPLOADS.resolve()
    assert Path(settings.LLM.log_root).resolve() == TEST_API_RUNS.resolve()
    assert not settings.LLM.enabled, "LLM must be disabled in the default test run"


@pytest.fixture(scope="session")
def app_module():
    import main
    try:
        import database
        database.engine.sync_engine.echo = False  # config debug=true => very noisy SQL echo
    except Exception:
        pass
    _safety_check()
    return main


@pytest_asyncio.fixture(scope="session")
async def app(app_module):
    application = app_module.app
    async with application.router.lifespan_context(application):
        yield application


# ---------------------------------------------------------------- 登录（鉴权）
# 所有 /api/* 业务接口都需要登录（Cookie 会话）。现有用例统一使用 `client`：
# 它以默认测试教师 DEFAULT_TEACHER 登录，并且启动播种的演示数据已通过 assign_orphans 归到该教师。
# 需要多个教师 / 管理员时用 `make_teacher` 工厂；需要未登录请求时用 `anon_client`。
# acceptance 用例同样可以直接使用这几个 fixture。

DEFAULT_TEACHER = "pytest_teacher"
DEFAULT_PASSWORD = "PytestPass123"


@pytest.fixture(scope="session")
def default_teacher(app):
    """默认测试教师（不要求改初始密码），并把演示数据归到他名下"""
    import manage
    uid, _ = manage.create_user(DEFAULT_TEACHER, "测试老师", password=DEFAULT_PASSWORD, must_change_password=False)
    manage.assign_orphans(DEFAULT_TEACHER)
    return {"id": uid, "username": DEFAULT_TEACHER, "password": DEFAULT_PASSWORD}


@pytest_asyncio.fixture(scope="session")
async def client(app, default_teacher):
    async with new_http_client(app) as c:
        await login_client(c, default_teacher["username"], default_teacher["password"])
        yield c


@pytest_asyncio.fixture
async def anon_client(app):
    """未登录的客户端"""
    async with new_http_client(app) as c:
        yield c


@pytest_asyncio.fixture
async def make_teacher(app):
    """
    工厂：`c = await make_teacher(username=None, role="teacher", name=None, must_change_password=False)`
    返回已登录的 httpx.AsyncClient，`c.user` 为登录接口返回的用户信息，`c.password` 为密码。
    must_change_password=True 时同样会登录（此时业务接口返回 403，需先改密）。
    """
    import manage
    clients = []

    async def _make(username=None, role="teacher", name=None, must_change_password=False, password=None):
        username = username or f"t_{uuid.uuid4().hex[:10]}"
        password = password or f"Pass{uuid.uuid4().hex[:8]}9"
        manage.create_user(username, name or "测试老师", role=role, password=password,
                           must_change_password=must_change_password)
        c = new_http_client(app)
        clients.append(c)
        await login_client(c, username, password)
        return c

    yield _make
    for c in clients:
        await c.aclose()


@pytest.fixture(autouse=True)
def _reset_login_limiter():
    """登录失败计数是进程内状态，每个用例前清零，避免相互影响"""
    try:
        from auth import login_limiter
        login_limiter.reset()
    except ImportError:
        pass
    yield


async def _drain_jobs():
    try:
        import jobs
    except ImportError:
        return
    await jobs.wait_all_jobs(timeout=15)


@pytest_asyncio.fixture
async def fake_ai(app_module):
    """Replace the model gateway with a recording fake for one test.
    Background jobs are drained before restoring so they never hit another test's gateway."""
    await _drain_jobs()
    fake = FakeGateway()
    prev = install_gateway(fake)
    try:
        yield fake
    finally:
        await _drain_jobs()
        restore_gateway(prev)


@pytest.fixture
def upload_dir():
    return TEST_UPLOADS


@pytest.fixture
def test_tmp():
    return TEST_TMP


def pytest_sessionfinish(session, exitstatus):
    if os.environ.get("KEEP_TEST_TMP"):
        print(f"\n[tests] temp dir kept: {TEST_TMP}")
        return
    try:
        # dispose engine first so Windows releases the sqlite file
        import database
        asyncio.run(database.engine.dispose())
    except Exception:
        pass
    shutil.rmtree(TEST_TMP, ignore_errors=True)
