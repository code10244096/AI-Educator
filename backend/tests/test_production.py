"""R1-003 生产安全基线：生产拒绝不安全配置启动、关闭接口文档、CORS 白名单、上传文件头校验与数量上限。"""
import io
import json
import os
import subprocess
import sys

import pytest

from fakes import DEFAULT_OCR
from testenv import BACKEND_DIR

PROD_SECRET = "prod-secret-" + "a" * 40
PROD_KEY = "sk-prodtest-key-000000000000"

_BOOT = r"""
import asyncio, json, os, sys
sys.path.insert(0, os.getcwd())
async def main():
    try:
        from main import app
        import database
        from config import settings
    except BaseException as e:
        print("BOOT_ERROR:" + str(e)); sys.exit(3)
    import httpx
    out = {"debug": settings.DEBUG, "sql_echo": bool(database.engine.sync_engine.echo),
           "dataset_routes": [r.path for r in app.routes if "dataset" in getattr(r, "path", "")]}
    try:
        async with app.router.lifespan_context(app):
            t = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=t, base_url="http://x") as c:
                out["docs"] = (await c.get("/docs")).status_code
                out["openapi"] = (await c.get("/openapi.json")).status_code
                out["health"] = (await c.get("/health")).status_code
                pre = lambda o: c.options("/api/auth/login", headers={"Origin": o, "Access-Control-Request-Method": "POST"})
                out["cors_evil"] = (await pre("https://evil.example.com")).headers.get("access-control-allow-origin")
                out["cors_good"] = (await pre("https://school.example.com")).headers.get("access-control-allow-origin")
                out["classes"] = None
        await database.engine.dispose()
    except BaseException as e:
        print("BOOT_ERROR:" + str(e)); sys.exit(3)
    print("RESULT:" + json.dumps(out))
asyncio.run(main())
"""


def _boot(tmp_path, **env_over):
    env = {k: v for k, v in os.environ.items()
           if k not in ("APP_ENV", "JWT_SECRET", "CORS_ORIGINS", "SEED_DEMO_DATA", "LLM_API_KEY")}
    env.update({
        "APP_ENV": "production", "JWT_SECRET": PROD_SECRET, "LLM_API_KEY": PROD_KEY,
        "CORS_ORIGINS": "https://school.example.com",
        "DATABASE_URL": f"sqlite+aiosqlite:///{(tmp_path / 'prod.db').as_posix()}",
        "UPLOAD_DIR": str(tmp_path / "uploads"), "API_OUTPUT_ROOT": str(tmp_path / "api_runs"),
        "PYTHONIOENCODING": "utf-8",
    })
    for k, v in env_over.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    p = subprocess.run([sys.executable, "-c", _BOOT], cwd=str(BACKEND_DIR), env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=180)
    result = None
    for line in p.stdout.splitlines():
        if line.startswith("RESULT:"):
            result = json.loads(line[7:])
    return p, result


@pytest.mark.slow
def test_production_refuses_insecure_config(tmp_path):
    p, res = _boot(tmp_path / "a", JWT_SECRET=None)
    assert res is None and p.returncode != 0
    assert "生产环境必须设置 JWT_SECRET" in p.stdout + p.stderr
    p, res = _boot(tmp_path / "b", JWT_SECRET="your-secret-key-change-in-production")
    assert res is None and p.returncode != 0
    p, res = _boot(tmp_path / "c", LLM_API_KEY="your_api_key_here")
    assert res is None and p.returncode != 0
    assert "LLM_API_KEY" in p.stdout + p.stderr


@pytest.mark.slow
def test_production_boot_is_locked_down(tmp_path):
    p, res = _boot(tmp_path)
    assert res, p.stdout[-800:] + p.stderr[-1500:]
    assert res["docs"] == 404 and res["openapi"] == 404 and res["health"] == 200
    assert res["debug"] is False and res["sql_echo"] is False
    assert res["cors_evil"] is None
    assert res["dataset_routes"] == [], "生产环境不注册开发用测试集接口"
    assert res["cors_good"] == "https://school.example.com"
    # 生产不播种演示数据：空库
    import sqlite3
    con = sqlite3.connect(tmp_path / "prod.db")
    counts = [con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("users", "classes", "class_members", "homework_assignments", "homework_submissions")]
    con.close()
    assert counts == [0, 0, 0, 0, 0], counts


def test_placeholder_llm_keys_are_not_enabled():
    from llm import LLMConfig
    for key in ("", "your_api_key_here", "your-api-key", "sk-xxxxxxxx", "sk-your-key", "<LLM_API_KEY>"):
        assert not LLMConfig(api_key=key, base_url="x", models={"default": "m"}).enabled, key
    assert LLMConfig(api_key="sk-real-looking-0001", base_url="x", models={"default": "m"}).enabled


def test_env_only_llm_config(monkeypatch):
    from llm import load_llm_config
    monkeypatch.setenv("LLM_API_KEY", "sk-env-only-1234")
    monkeypatch.setenv("LLM_BASE_URL", "https://gw.example/v1")
    monkeypatch.setenv("LLM_MODEL_GRADE", "grade-x")
    monkeypatch.setenv("LLM_FALLBACK_GRADE", "a, b")
    cfg = load_llm_config({}, {})
    assert cfg.enabled and cfg.base_url == "https://gw.example/v1"
    assert cfg.model_for("grade") == "grade-x" and cfg.model_chain("grade") == ["grade-x", "a", "b"]
    assert cfg.model_for("ocr") == "gpt-6-astra"


# ---------------------------------------------------------------- 上传：文件头 + 数量

def _png() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buf, "PNG")
    return buf.getvalue()


@pytest.mark.parametrize("name,content", [
    ("作业.jpg", b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64),   # exe 改名
    ("作业.png", b"\xff\xd8\xff\xe0" + b"0" * 64),                 # jpg 冒充 png
    ("作业.pdf", b"hello, not a pdf"),
    ("作业.docx", b"not a zip file at all"),
    ("作业.txt", b"MZ\x90\x00\x03\x00binary"),
])
async def test_content_must_match_extension(client, fake_ai, name, content):
    r = await client.post("/api/grader/upload", files={"files": (name, content, "application/octet-stream")})
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "文件内容与格式不符"
    assert fake_ai.calls == []


async def test_real_image_and_gbk_text_accepted(client, fake_ai):
    r = await client.post("/api/grader/upload", files={"files": ("p.png", _png(), "image/png")})
    assert r.status_code == 200, r.text
    gbk = "### 1. 题目\n**学生答案**：二".encode("gbk")
    r = await client.post("/api/grader/upload", files={"files": ("g.txt", gbk, "text/plain")})
    assert r.status_code == 200, r.text


async def test_at_most_10_files_per_submission(client, fake_ai):
    mk = lambda i: ("files", (f"p{i}.md", DEFAULT_OCR.encode(), "text/markdown"))  # noqa: E731
    r = await client.post("/api/grader/upload", files=[mk(i) for i in range(11)])
    assert r.status_code == 400 and "最多上传 10 个文件" in r.json()["detail"]
    assert fake_ai.calls == []
    r = await client.post("/api/grader/upload", files=[mk(i) for i in range(10)])
    assert r.status_code == 200, r.text


def test_dockerignore_excludes_secrets_and_data():
    text = (BACKEND_DIR / ".dockerignore").read_text(encoding="utf-8")
    for need in ("config.json", ".env", "*.db", "**/*.db", "uploads", "api_runs", "venv", "__pycache__", "tests"):
        assert need in text.splitlines(), need
