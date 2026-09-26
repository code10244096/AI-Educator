"""Subprocess runner for acceptance checks that need a fresh interpreter / env (not collected by pytest).

usage: python _qa_runner.py <action>   env: DATABASE_URL / UPLOAD_DIR / API_OUTPUT_ROOT / APP_ENV / ...
       optional QA_EXTRA = JSON (see actions)
Prints `RESULT:<json>` on success; on startup failure prints `BOOT_ERROR:<message>` and exits 3.

actions
  boot    import main + run lifespan (startup), then perform QA_EXTRA["requests"] anonymously and
          QA_EXTRA["users"][i]["requests"] after logging in as that user. Reports statuses, selected
          headers, JSON bodies (truncated), registered routes, DEBUG / SQL echo flags.
  initdb  only database.init_db() (schema + migrations, no seeding)
"""
import asyncio
import json
import logging
import os
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
# QA_BACKEND_DIR: run against another copy of backend/ (e.g. a simulated docker build context)
BACKEND = Path(os.environ.get("QA_BACKEND_DIR") or HERE.parents[1])
os.chdir(BACKEND)
sys.path[:0] = [str(BACKEND)] + ([] if os.environ.get("QA_BACKEND_DIR") else [str(HERE.parent), str(HERE)])
logging.disable(logging.CRITICAL)

EXTRA = json.loads(os.environ.get("QA_EXTRA") or "{}")
SAMPLE = "### 1. 1+1=?\n**学生答案**：2\n\n---\n\n### 2. 2+2=?\n**学生答案**：4\n"
KEEP_HEADERS = ("access-control-allow-origin", "access-control-allow-credentials", "set-cookie",
                "content-type", "x-request-id", "location")


def _boot_error(exc: BaseException):
    msg = f"{type(exc).__name__}: {exc}"
    print("BOOT_ERROR:" + msg.replace("\n", " "))
    traceback.print_exc()
    sys.exit(3)


async def _do(client, req):
    method = req.get("method", "GET").upper()
    kw = {}
    if req.get("headers"):
        kw["headers"] = req["headers"]
    if req.get("json") is not None:
        kw["json"] = req["json"]
    if req.get("data") is not None:
        kw["data"] = req["data"]
    r = await client.request(method, req["path"], **kw)
    try:
        body = r.json()
    except Exception:
        body = r.text[:300]
    items = body if isinstance(body, list) else (body.get("items") if isinstance(body, dict) else None)
    count = len(items) if isinstance(items, list) else None
    if len(json.dumps(body, ensure_ascii=False, default=str)) >= 4000:
        if isinstance(body, list):
            body = body[:3]
        elif isinstance(body, dict) and isinstance(items, list):
            body = {**body, "items": items[:3]}
        else:
            body = "<truncated>"
    return {"method": method, "path": req["path"], "status": r.status_code, "count": count,
            "headers": {k: v for k, v in r.headers.items() if k.lower() in KEEP_HEADERS}, "body": body}


async def boot():
    try:
        from main import app
        import database
    except BaseException as e:  # config / import time refusal
        _boot_error(e)
    import httpx
    from fastapi.routing import APIRoute
    out = {"routes": sorted({f"{m} {r.path}" for r in app.routes if isinstance(r, APIRoute) for m in r.methods}),
           "anon": [], "users": []}
    try:
        from config import settings
        out["debug"] = bool(getattr(settings, "DEBUG", None))
    except Exception:
        out["debug"] = None
    try:
        out["sql_echo"] = bool(database.engine.sync_engine.echo)
    except Exception:
        out["sql_echo"] = None
    try:
        ctx = app.router.lifespan_context(app)
        await ctx.__aenter__()
    except BaseException as e:
        _boot_error(e)
    try:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url=EXTRA.get("base_url", "http://testserver")) as c:
            for req in EXTRA.get("requests", []):
                out["anon"].append(await _do(c, req))
        for u in EXTRA.get("users", []):
            async with httpx.AsyncClient(transport=transport, base_url=EXTRA.get("base_url", "http://testserver")) as c:
                lr = await c.post("/api/auth/login", json={"username": u["username"], "password": u["password"]})
                res = {"username": u["username"], "login": lr.status_code, "results": [],
                       "login_headers": {"set-cookie": lr.headers.get_list("set-cookie")}}
                for req in u.get("requests", []):
                    res["results"].append(await _do(c, req))
                out["users"].append(res)
        try:
            import jobs
            await jobs.wait_all_jobs(timeout=30)
        except Exception:
            pass
    finally:
        await ctx.__aexit__(None, None, None)
        try:
            await database.engine.dispose()
        except Exception:
            pass
    return out


async def crash_after_batch():
    """Log in, create a class with N members + 1 homework, upload one file per member (queued behind
    GRADING_CONCURRENCY / MOCK_LLM_DELAY_SECONDS), report statuses, then die abruptly (no shutdown)."""
    try:
        from main import app
    except BaseException as e:
        _boot_error(e)
    import httpx
    ctx = app.router.lifespan_context(app)
    await ctx.__aenter__()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    out = {"submissions": []}
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        r = await c.post("/api/auth/login", json={"username": EXTRA["username"], "password": EXTRA["password"]})
        assert r.status_code == 200, r.text
        cls = (await c.post("/api/class", json={"name": "重启班", "grade": "高一"})).json()
        ck = cls.get("slug") or cls["id"]
        hw = (await c.post(f"/api/class/{ck}/homework", json={"title": "重启作业", "reference_answer": "1. 2"})).json()
        out.update(class_key=ck, assignment_id=hw["assignment_id"])
        for i in range(int(EXTRA.get("n", 4))):
            m = (await c.post(f"/api/class/{ck}/members", json={"name": f"重启生{i}", "student_no": f"30{i:03d}"})).json()
            r = await c.post("/api/grader/upload", data={"assignment_id": str(hw["assignment_id"]), "member_id": str(m["id"])},
                             files=[("files", (f"{i}.md", SAMPLE.encode(), "text/markdown"))])
            out["submissions"].append({"id": r.json().get("submission_id"), "status_code": r.status_code})
        await asyncio.sleep(float(EXTRA.get("settle", 0.5)))
        for s in out["submissions"]:
            d = (await c.get(f"/api/grader/{s['id']}")).json()
            s.update(status=d.get("status"), stage=d.get("progress_stage"))
    print("RESULT:" + json.dumps(out, ensure_ascii=False, default=str), flush=True)
    os._exit(0)  # simulate a crash / kill -9: no lifespan shutdown, background tasks abandoned


async def initdb():
    try:
        import database
        import models  # noqa: F401
        await database.init_db()
        await database.engine.dispose()
    except BaseException as e:
        _boot_error(e)
    return {"ok": True}


if __name__ == "__main__":
    action = sys.argv[1]
    fn = {"boot": boot, "initdb": initdb, "crash_after_batch": crash_after_batch}[action]
    result = asyncio.run(fn())
    print("RESULT:" + json.dumps(result, ensure_ascii=False, default=str))
