"""Subprocess helper for restart / migration tests (not collected by pytest).

usage: python _app_runner.py <action>   with DATABASE_URL / UPLOAD_DIR / API_OUTPUT_ROOT set.
Prints one JSON line prefixed with RESULT: on stdout.

actions:
  create   start the app (lifespan), write data through the API, print ids
  check    start the app again on the same DB and read it all back (ids via RUNNER_IDS env)
  initdb   only run database.init_db() (for migration tests)
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
os.environ.setdefault("LLM_API_KEY", "your_api_key_here")
os.environ.setdefault("SEED_DEMO_DATA", "true")
logging.disable(logging.CRITICAL)


RUNNER_USER = "runner_teacher"
RUNNER_PASSWORD = "RunnerPass123"


async def _client(app):
    import httpx
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                             base_url="http://runner")


async def _login(c, create: bool):
    """鉴权后所有业务接口都要登录：首次运行开通账号并认领演示数据，之后直接登录"""
    if create:
        import manage
        manage.create_user(RUNNER_USER, "重启测试老师", password=RUNNER_PASSWORD, must_change_password=False)
        manage.assign_orphans(RUNNER_USER)
    r = await c.post("/api/auth/login", json={"username": RUNNER_USER, "password": RUNNER_PASSWORD})
    assert r.status_code == 200, r.text


async def create():
    from main import app
    import database
    database.engine.sync_engine.echo = False
    from fakes import FakeGateway, install_gateway
    install_gateway(FakeGateway())
    out = {}
    async with app.router.lifespan_context(app):
        async with await _client(app) as c:
            await _login(c, create=True)
            r = await c.post("/api/lessonplan/generate", data={"title": "重启测试教案"})
            out["lesson_status"] = r.status_code
            out["lesson_id"] = r.json().get("id") if r.status_code == 200 else None
            r = await c.post("/api/grader/upload",
                             files={"files": ("r.md", "### 1. x\n**学生答案**：1".encode(), "text/markdown")},
                             data={"student_name": "重启学生"})
            out["grade_status"] = 200 if r.status_code in (200, 202) else r.status_code
            out["submission_id"] = r.json().get("submission_id") if r.status_code in (200, 202) else None
            try:  # background-job API: let the job finish before "shutdown"
                import jobs
                await jobs.wait_all_jobs(timeout=30)
            except ImportError:
                pass
            r = await c.post("/api/questionbank/add", data={
                "question_text": "重启题目", "answer": "1", "question_type": "填空题",
                "subject": "数学", "education_level": "高中"})
            out["question_id"] = r.json().get("id")
            out["classes"] = len((await c.get("/api/class/list")).json()["items"])
            out["hw10_submitted"] = await _hw10_submitted(c)
    await database.engine.dispose()
    return out


async def _hw10_submitted(c):
    items = (await c.get("/api/class/class1/homework")).json()["items"]
    hid = next(h["id"] for h in items if h["title"] == "高考数学作业集10")
    subs = (await c.get(f"/api/class/class1/homework/{hid}/submissions")).json()["items"]
    return sum(1 for s in subs if s.get("submission_id"))


async def check():
    from main import app
    import database
    database.engine.sync_engine.echo = False
    ids = json.loads(os.environ["RUNNER_IDS"])
    out = {}
    async with app.router.lifespan_context(app):
        async with await _client(app) as c:
            await _login(c, create=False)
            if ids.get("lesson_id"):
                out["lesson"] = (await c.get(f"/api/lessonplan/{ids['lesson_id']}")).status_code
            if ids.get("submission_id"):
                r = await c.get(f"/api/grader/{ids['submission_id']}")
                out["submission"] = r.status_code
                out["submission_score"] = r.json().get("score") if r.status_code == 200 else None
            out["question"] = (await c.get(f"/api/questionbank/{ids['question_id']}")).status_code
            out["classes"] = len((await c.get("/api/class/list")).json()["items"])
            out["hw10_submitted"] = await _hw10_submitted(c)
    await database.engine.dispose()
    return out


async def initdb():
    import database
    import models  # noqa: F401  (register tables)
    database.engine.sync_engine.echo = False
    await database.init_db()
    await database.engine.dispose()
    return {"ok": True}


if __name__ == "__main__":
    action = sys.argv[1]
    result = asyncio.run({"create": create, "check": check, "initdb": initdb}[action]())
    print("RESULT:" + json.dumps(result, ensure_ascii=False))
