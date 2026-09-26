"""backend/llm: LLMGateway + CallLogger with an httpx.MockTransport-backed
OpenAI client (no network), and end-to-end usage logging through the app."""
import base64
import json
from pathlib import Path

import httpx
import openai
import pytest

from conftest import TEST_API_RUNS
from fakes import DEFAULT_GRADE, install_gateway, restore_gateway
from llm import LLMConfig, LLMError, LLMGateway

API_KEY = "sk-test-SECRETSECRET-wxyz"


def _completion(content: str, model: str = "m", reasoning: int = 3) -> dict:
    return {
        "id": "chatcmpl-test", "object": "chat.completion", "created": 1700000000, "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18,
                  "completion_tokens_details": {"reasoning_tokens": reasoning}},
    }


class Recorder:
    def __init__(self, status=200, content="hello", fail_times=0):
        self.requests = []
        self.status = status
        self.content = content
        self.fail_times = fail_times

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append({"url": str(request.url), "headers": dict(request.headers), "body": body})
        if self.fail_times > 0:
            self.fail_times -= 1
            return httpx.Response(500, json={"error": {"message": "boom upstream", "type": "server_error"}})
        if self.status != 200:
            return httpx.Response(self.status, json={"error": {"message": "quota exceeded", "type": "insufficient_quota"}})
        content = self.content(body) if callable(self.content) else self.content
        return httpx.Response(200, json=_completion(content, model=body["model"]))


def make_gateway(log_root: Path, recorder: Recorder, **cfg) -> LLMGateway:
    config = LLMConfig(
        api_key=API_KEY, base_url="https://fake-llm.test/v1",
        models={"default": "m-default", "grade": "m-grade", "ocr": "m-ocr"},
        max_retries=cfg.pop("max_retries", 0), log_root=str(log_root), **cfg,
    )
    gw = LLMGateway(config, source=cfg.pop("source", "backend"))
    gw._client = openai.AsyncOpenAI(
        api_key=config.api_key, base_url=config.base_url, max_retries=config.max_retries,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(recorder)),
    )
    return gw


def read_records(log_root: Path):
    files = list(Path(log_root).glob("*/api_calls.jsonl"))
    rows = []
    for f in files:
        rows += [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    return files, rows


# ------------------------------------------------------------------ unit

async def test_fallback_model_used_and_each_attempt_logged(tmp_path):
    def reply(body):
        return "ok-from-" + body["model"]

    class FailPrimary(Recorder):
        def __call__(self, request):
            if json.loads(request.content)["model"] == "m-grade":
                self.requests.append({"body": json.loads(request.content)})
                return httpx.Response(503, json={"error": {"message": "billing down", "type": "server_error"}})
            return super().__call__(request)

    rec = FailPrimary(content=reply)
    gw = make_gateway(tmp_path, rec, fallbacks={"grade": ["m-backup"]})
    res = await gw.chat([{"role": "user", "content": "hi"}], feature="grade")
    assert res.model == "m-backup" and res.content == "ok-from-m-backup"

    _, rows = read_records(tmp_path)
    calls = [r for r in rows if r.get("call_id")]
    assert [(r["model"], r["success"]) for r in calls] == [("m-grade", False), ("m-backup", True)]
    assert calls[1]["task_meta"]["fallback_from"] == "m-grade"


async def test_fallback_exhausted_raises_last_error(tmp_path):
    rec = Recorder(status=429)
    gw = make_gateway(tmp_path, rec, fallbacks={"grade": ["m-backup"]})
    with pytest.raises(LLMError):
        await gw.chat([{"role": "user", "content": "hi"}], feature="grade")
    _, rows = read_records(tmp_path)
    assert len([r for r in rows if r.get("call_id")]) == 2
    # 显式指定 model 时不走备用链
    rec2 = Recorder(status=429)
    gw2 = make_gateway(tmp_path / "b", rec2, fallbacks={"grade": ["m-backup"]})
    with pytest.raises(LLMError):
        await gw2.chat([{"role": "user", "content": "hi"}], feature="grade", model="m-x")
    assert len(rec2.requests) == 1


async def test_success_call_logged_v4(tmp_path):
    rec = Recorder(content="你好")
    gw = make_gateway(tmp_path, rec)
    res = await gw.chat([{"role": "user", "content": "hi"}], feature="grade", task_meta={"k": "v"})
    assert res.content == "你好"
    assert res.model == "m-grade"  # per-feature model routing
    assert res.usage == {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18, "reasoning_tokens": 3}
    assert rec.requests[0]["url"].endswith("/v1/chat/completions")
    assert rec.requests[0]["headers"]["authorization"] == f"Bearer {API_KEY}"

    files, rows = read_records(tmp_path)
    assert len(files) == 1 and len(rows) == 1
    r = rows[0]
    assert r["schema_version"] == "api_call_log_v4"
    assert r["feature"] == "grade" and r["success"] is True and r["error"] is None
    assert r["model"] == "m-grade" and r["source"] == "backend"
    assert r["api_key_suffix"] == "wxyz"
    assert r["usage"]["total_tokens"] == 18
    assert r["task_meta"] == {"k": "v"}
    assert r["response"]["content"] == "你好"
    run_dir = files[0].parent
    assert "SECRETSECRET" not in "".join(p.read_text(encoding="utf-8") for p in run_dir.iterdir())
    meta = json.loads((run_dir / "run_meta.json").read_text(encoding="utf-8"))
    assert meta["schema_version"] == "api_run_meta_v4"
    assert (run_dir / "responses.jsonl").exists()
    await gw.aclose()


async def test_failure_logged_and_raises_llmerror(tmp_path):
    rec = Recorder(status=429)
    gw = make_gateway(tmp_path, rec)
    with pytest.raises(LLMError) as ei:
        await gw.chat([{"role": "user", "content": "hi"}], feature="lessonplan")
    assert "429" in str(ei.value)
    _, rows = read_records(tmp_path)
    assert len(rows) == 1
    r = rows[0]
    assert r["success"] is False and r["feature"] == "lessonplan"
    assert r["model"] == "m-default"
    assert r["error"]["type"] and "quota" in r["error"]["message"]
    assert r["usage"]["total_tokens"] == 0


async def test_image_base64_stripped_from_log(tmp_path):
    rec = Recorder(content="ocr text")
    gw = make_gateway(tmp_path, rec)
    b64 = base64.b64encode(b"\x89PNG" + b"x" * 5000).decode()
    url = f"data:image/png;base64,{b64}"
    msgs = [{"role": "user", "content": [{"type": "text", "text": "识别"},
                                         {"type": "image_url", "image_url": {"url": url}}]}]
    await gw.chat(msgs, feature="ocr")
    # the image must actually be sent upstream...
    sent = rec.requests[0]["body"]["messages"][0]["content"][1]["image_url"]["url"]
    assert sent == url
    # ...but never written to disk
    files, rows = read_records(tmp_path)
    raw = files[0].read_text(encoding="utf-8")
    assert b64[:200] not in raw
    logged = rows[0]["request"]["messages"][0]["content"][1]["image_url"]["url"]
    assert logged.startswith("<image omitted")
    assert rows[0]["request"]["messages"][0]["content"][0]["text"] == "识别"
    # caller's message list is not mutated
    assert msgs[0]["content"][1]["image_url"]["url"] == url


async def test_summary_totals(tmp_path):
    rec = Recorder(content="ok")
    gw = make_gateway(tmp_path, rec)
    await gw.chat([{"role": "user", "content": "a"}], feature="grade")
    await gw.chat([{"role": "user", "content": "b"}], feature="ocr")
    rec.status = 500
    with pytest.raises(LLMError):
        await gw.chat([{"role": "user", "content": "c"}], feature="grade")
    files, rows = read_records(tmp_path)
    assert len(files) == 1, "one run dir per gateway/process"
    summary = json.loads((files[0].parent / "summary.json").read_text(encoding="utf-8"))
    assert summary["schema_version"] == "api_run_summary_v4"
    assert summary["total_calls"] == 3
    assert summary["success_calls"] == 2 and summary["failed_calls"] == 1
    assert summary["usage"]["total_tokens"] == 36
    assert summary["by_feature"]["grade"] == {"calls": 2, "failed": 1, "total_tokens": 18}
    assert summary["by_feature"]["ocr"]["calls"] == 1
    assert 66 < summary["success_rate"] < 67


async def test_retry_then_success_logged_once(tmp_path):
    rec = Recorder(content="ok", fail_times=1)
    gw = make_gateway(tmp_path, rec, max_retries=1)
    res = await gw.chat([{"role": "user", "content": "a"}], feature="grade")
    assert res.content == "ok"
    assert len(rec.requests) == 2
    _, rows = read_records(tmp_path)
    assert len(rows) == 1 and rows[0]["success"] is True


async def test_log_request_content_false_redacts(tmp_path):
    rec = Recorder(content="secret answer")
    gw = make_gateway(tmp_path, rec, log_request_content=False)
    await gw.chat([{"role": "user", "content": "private student text"}], feature="grade")
    files, rows = read_records(tmp_path)
    raw = files[0].read_text(encoding="utf-8")
    assert "private student text" not in raw and "secret answer" not in raw
    assert rows[0]["request"]["messages"][0]["content"] == "<20 chars>"


async def test_disabled_key_raises_without_network(tmp_path):
    rec = Recorder()
    config = LLMConfig(api_key="your_api_key_here", base_url="https://x/v1", models={"default": "m"},
                       log_root=str(tmp_path))
    gw = LLMGateway(config)
    assert not gw.enabled
    with pytest.raises(LLMError):
        await gw.chat([{"role": "user", "content": "a"}], feature="grade")
    assert rec.requests == []


def test_load_llm_config_env_overrides(monkeypatch, tmp_path):
    from llm import load_llm_config
    monkeypatch.setenv("LLM_API_KEY", "sk-from-env-1234")
    monkeypatch.setenv("API_OUTPUT_ROOT", str(tmp_path))
    cfg = load_llm_config({"api_key": "sk-file", "model": "x", "models": {"grade": "g"}}, {})
    assert cfg.api_key == "sk-from-env-1234"
    assert Path(cfg.log_root) == tmp_path
    assert cfg.model_for("grade") == "g" and cfg.model_for("ocr") == "x"
    legacy = load_llm_config({}, {"api_key": "k", "grader_model": "gm", "ocr_model": "om"})
    assert legacy.model_for("ocr") == "om" and legacy.model_for("lessonplan") == "gm"


# ------------------------------------------------------------------ through the app

@pytest.fixture
def real_gateway_app(app_module):
    """Real LLMGateway (fake transport) writing to the test API_OUTPUT_ROOT."""
    def responder(body):
        text = json.dumps(body["messages"], ensure_ascii=False)
        if "批改" in text:
            return json.dumps(DEFAULT_GRADE, ensure_ascii=False)
        if "教案" in text:
            return "# 教案\n内容"
        return "### 1. 题\n**学生答案**：1"
    rec = Recorder(content=responder)
    gw = make_gateway(TEST_API_RUNS, rec)
    prev = install_gateway(gw)
    yield rec
    restore_gateway(prev)


async def test_app_grading_writes_usage_record(client, real_gateway_app):
    import usage_stats
    r = await client.post("/api/grader/upload",
                          files={"files": ("u.md", "### 1. x\n**学生答案**：1".encode(), "text/markdown")},
                          data={"student_name": "用量学生"})
    assert r.status_code in (200, 202), r.text
    from helpers import is_pending, poll_job
    if is_pending(r.json()):
        assert (await poll_job(client, r.json()))["status"] == "completed"
    _, rows = read_records(TEST_API_RUNS)
    grade_rows = [x for x in rows if x["feature"] == "grade"]
    assert grade_rows and grade_rows[-1]["schema_version"] == "api_call_log_v4"
    assert grade_rows[-1]["success"] is True

    usage_stats.clear_cache()
    s = await client.get("/api/usage/summary", params={"feature": "grade"})
    assert s.status_code == 200
    body = s.json()
    assert body["overview"]["calls"] >= 1
    assert Path(body["log_root"]).resolve() == TEST_API_RUNS.resolve()
    calls = (await client.get("/api/usage/calls", params={"feature": "grade", "limit": 5})).json()
    assert calls["total"] >= 1
    assert "request" not in calls["items"][0], "usage API must not leak prompts"


async def test_app_image_grading_logs_ocr_without_base64(client, real_gateway_app):
    from conftest import GAOKAO_SCAN_DIR
    jpg = (GAOKAO_SCAN_DIR / "20240608-3.jpg").read_bytes()
    r = await client.post("/api/grader/upload", files={"files": ("s.jpg", jpg, "image/jpeg")})
    assert r.status_code in (200, 202), r.text
    from helpers import is_pending, poll_job
    if is_pending(r.json()):
        await poll_job(client, r.json())
    files, rows = read_records(TEST_API_RUNS)
    assert any(x["feature"] == "ocr" for x in rows)
    b64_head = base64.b64encode(jpg).decode()[:120]
    for f in files:
        assert b64_head not in f.read_text(encoding="utf-8")


async def test_app_lessonplan_failure_logged(client, real_gateway_app):
    real_gateway_app.status = 503
    r = await client.post("/api/lessonplan/generate", data={"title": "失败记录", "wait": "true"})
    assert r.status_code == 502
    _, rows = read_records(TEST_API_RUNS)
    fails = [x for x in rows if x["feature"] == "lessonplan" and not x["success"]]
    assert fails, "failed call must be logged"
