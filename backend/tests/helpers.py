"""HTTP helpers that work with both the old synchronous grading API and the
background-job API documented in backend/API.md (POST returns status=processing,
client polls GET /grader/{submission_id} or GET /lessonplan/{id})."""
import asyncio
from typing import Any, Dict, Optional

import httpx

TERMINAL = {"completed", "failed"}


def submission_id_of(body: Dict[str, Any]) -> Optional[int]:
    for k in ("submission_id", "submissionId"):
        if body.get(k) is not None:
            return int(body[k])
    sub = body.get("submission")
    if isinstance(sub, dict) and sub.get("id") is not None:
        return int(sub["id"])
    return None


def is_pending(body: Dict[str, Any]) -> bool:
    return str(body.get("status")) in ("processing", "queued", "pending", "running") and not body.get("grading_result")


async def poll_url(client: httpx.AsyncClient, url: str, *, timeout: float = 30.0,
                   interval: float = 0.05) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    history = []
    while True:
        r = await client.get(url)
        assert r.status_code == 200, f"poll {url} -> {r.status_code}: {r.text[:300]}"
        data = r.json()
        st = data.get("status") or "completed"  # legacy rows: empty status == completed
        if not history or history[-1] != (st, data.get("progress_stage")):
            history.append((st, data.get("progress_stage")))
        if st in TERMINAL:
            data["_history"] = history
            return data
        if loop.time() > deadline:
            raise AssertionError(f"{url} did not finish in {timeout}s; history={history}")
        await asyncio.sleep(interval)


async def poll_job(client: httpx.AsyncClient, body: Dict[str, Any], *, timeout: float = 30.0,
                   kind: str = "grader", interval: float = 0.05) -> Dict[str, Any]:
    if kind == "grader":
        sid = submission_id_of(body)
        assert sid, f"no submission_id in {body}"
        return await poll_url(client, f"/api/grader/{sid}", timeout=timeout, interval=interval)
    return await poll_url(client, f"/api/lessonplan/{body['id']}", timeout=timeout, interval=interval)


async def grade(client: httpx.AsyncClient, url: str, *, files=None, data=None,
                expect_ok: bool = True, timeout: float = 30.0) -> httpx.Response:
    """POST a grading request; if it runs as a background job wait for it and return a
    synthetic 200 response whose JSON is the final submission detail merged over the POST body."""
    r = await client.post(url, files=files, data=data or {})
    if r.status_code in (200, 201, 202):
        body = r.json()
        if is_pending(body):
            final = await poll_job(client, body, timeout=timeout)
            if expect_ok:
                assert final["status"] == "completed", f"job failed: {final.get('error_message')}"
            return httpx.Response(200, json={**body, **final}, request=r.request)
    if expect_ok:
        assert r.status_code in (200, 201, 202), f"{url} -> {r.status_code}: {r.text[:500]}"
    return r


async def generate_plan(client: httpx.AsyncClient, data: Dict[str, Any], *, timeout: float = 30.0):
    """POST /lessonplan/generate and wait for completion. Returns (post_response, final_json|None)."""
    r = await client.post("/api/lessonplan/generate", data=data)
    if r.status_code not in (200, 201, 202):
        return r, None
    body = r.json()
    if body.get("status") == "processing":
        return r, await poll_job(client, body, kind="lessonplan", timeout=timeout)
    return r, body


def grading_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    gr = body.get("grading_result")
    if isinstance(gr, dict) and gr:
        return gr
    return body


# ---------------------------------------------------------------- 登录

def new_http_client(app) -> httpx.AsyncClient:
    """直连 ASGI 应用的客户端（自带 Cookie 罐，登录后自动携带会话）"""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=60)


async def login_client(c: httpx.AsyncClient, username: str, password: str) -> Dict[str, Any]:
    r = await c.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"login {username} -> {r.status_code}: {r.text}"
    user = r.json()
    c.user = user
    c.password = password
    return user


SEED_HW_TITLE = "高考数学作业集10"  # 演示数据中“待批改”的那份作业（含 38 份待批改提交）


async def seeded_homework_id(client: httpx.AsyncClient, title: str = SEED_HW_TITLE, class_slug: str = "class1") -> int:
    """演示数据的作业主键（R1-005 起作业一律按主键访问）"""
    r = await client.get(f"/api/class/{class_slug}/homework")
    assert r.status_code == 200, r.text
    return next(h["id"] for h in r.json()["items"] if h["title"] == title)
