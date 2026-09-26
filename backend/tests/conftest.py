"""
Pytest bootstrap: isolate DB / uploads / call logs in a temp dir and force the
model layer offline BEFORE the application is imported.

Run from repo root:   python -m pytest backend/tests
or from backend/:     python -m pytest tests
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DATASET_HW_DIR = REPO_ROOT / "dataset" / "测试集" / "批改作业"
GAOKAO_SCAN_DIR = REPO_ROOT / "dataset" / "高考" / "数学" / "高考数学真题" / "PDF资源" / "2024年新高考I卷"

TEST_TMP = Path(tempfile.mkdtemp(prefix="aiedu_tests_"))
TEST_DB = TEST_TMP / "test.db"
# nested so that a path-traversal escape still lands inside TEST_TMP
TEST_UPLOADS = TEST_TMP / "data" / "files" / "uploads"
TEST_API_RUNS = TEST_TMP / "api_runs"
TEST_UPLOADS.mkdir(parents=True, exist_ok=True)

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB.as_posix()}"
os.environ["UPLOAD_DIR"] = str(TEST_UPLOADS)
os.environ["API_OUTPUT_ROOT"] = str(TEST_API_RUNS)
# placeholder key => LLMConfig.enabled is False => no real network calls ever
os.environ["LLM_API_KEY"] = "your_api_key_here"
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import asyncio  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from fakes import FakeGateway, install_gateway, restore_gateway  # noqa: E402


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


@pytest_asyncio.fixture(scope="session")
async def client(app):
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=60) as c:
        yield c


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
