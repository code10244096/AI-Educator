"""第 1 轮验收测试 fixture（测试 agent 维护；上级 backend/tests/conftest.py 由开发维护）。

运行：仓库根目录 `python -m pytest backend/tests/acceptance`（或随全量 `python -m pytest backend/tests`）。
- 复用上级 conftest 的临时库 / 临时上传目录 / 离线模型（`app`、`fake_ai` fixture）。
- 每个用例自建教师账号与数据，不依赖演示播种数据。
- 验收用例在收集阶段被移到全量回归的最后执行，避免影响开发维护的既有用例。
- 尚未开发的分组以模块级 `xfail(reason="待开发…", run=False)` 标记；想看当前真实失败情况时加 `--runxfail`。
"""
import sys
from pathlib import Path

import pytest
import pytest_asyncio

ACCEPTANCE_DIR = Path(__file__).resolve().parent
if str(ACCEPTANCE_DIR) not in sys.path:
    sys.path.insert(0, str(ACCEPTANCE_DIR))

from qa_helpers import TeacherFactory, drain_jobs  # noqa: E402


def pytest_collection_modifyitems(session, config, items):
    """Run acceptance tests after the developer-owned suite (stable ordering inside each group)."""
    acc = [it for it in items if ACCEPTANCE_DIR in Path(str(it.fspath)).resolve().parents]
    if not acc:
        return
    rest = [it for it in items if it not in acc]
    items[:] = rest + acc


@pytest_asyncio.fixture
async def teachers(app):
    """Factory: `t = await teachers()` / `await teachers(role="admin")` → logged-in Teacher (own cookie jar)."""
    f = TeacherFactory(app)
    try:
        yield f
    finally:
        await drain_jobs()
        await f.aclose()


@pytest_asyncio.fixture
async def anon(app):
    """A client without any credentials."""
    f = TeacherFactory(app)
    try:
        yield f.client()
    finally:
        await f.aclose()


@pytest.fixture
def restore_settings():
    """Snapshot/restore attributes on config.settings that a test monkeypatches."""
    from config import settings
    saved = {}

    def setattr_(name, value):
        if name not in saved:
            saved[name] = getattr(settings, name, _MISSING)
        setattr(settings, name, value)

    yield setattr_
    for name, value in saved.items():
        if value is _MISSING:
            try:
                delattr(settings, name)
            except AttributeError:
                pass
        else:
            setattr(settings, name, value)


_MISSING = object()
