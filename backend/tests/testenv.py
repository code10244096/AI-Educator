"""
测试环境：把数据库 / 上传目录 / 模型调用日志隔离到临时目录，并强制模型离线（模拟模式）。
必须在导入后端应用之前执行（conftest.py 最先 import 本模块）。
用例中需要这些路径时 `from testenv import TEST_UPLOADS` 等。
"""
import os
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
os.environ["USER_RECORDS_DIR"] = str(TEST_TMP / "user_records")
os.environ["TRIAL_QUOTA_ENABLED"] = "false"
os.environ["TRIAL_QUOTA_FILE"] = str(TEST_TMP / "trial_quota.json")
# placeholder key => LLMConfig.enabled is False => no real network calls ever
os.environ["LLM_API_KEY"] = "your_api_key_here"
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
# bcrypt 用最低强度，加快测试（生产默认 12）
os.environ.setdefault("BCRYPT_ROUNDS", "4")
# 现有用例依赖启动时播种的演示数据（开发环境显式开启；生产强制关闭）
os.environ["SEED_DEMO_DATA"] = "true"
# 测试始终在开发环境运行（即使外部设置了 APP_ENV=production）
os.environ["APP_ENV"] = "development"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def iter_concrete_routes(routes, prefix=""):
    """递归展平路由表，兼容新版 Starlette 的懒加载嵌套路由。

    Starlette >= 1.x 中 include_router 不再立即拍平路由，而是在 routes 里
    挂一个 _IncludedRouter 占位对象；需要遍历具体接口时必须递归展开，
    把各级 include 时的 prefix 拼回路径。
    """
    for route in routes:
        if type(route).__name__ == "_IncludedRouter":
            ctx = route.include_context
            sub_prefix = prefix + (ctx.prefix or "")
            yield from iter_concrete_routes(route.original_router.routes, sub_prefix)
            continue
        path = getattr(route, "path", "") or ""
        methods = getattr(route, "methods", None) or set()
        for m in sorted(methods - {"HEAD", "OPTIONS"}):
            yield m, prefix + path


def api_routes(app, prefix="/api"):
    """返回 [(method, path)]：path 以 prefix 开头的全部具体接口。"""
    return [(m, p) for m, p in iter_concrete_routes(app.routes) if p.startswith(prefix)]
