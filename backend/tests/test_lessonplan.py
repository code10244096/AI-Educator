"""Lesson plans: generate (background job), get, list, edit, delete, regenerate, export, failures."""
import uuid

import pytest

from fakes import DEFAULT_LESSONPLAN, prompt_text
from helpers import generate_plan, poll_job

GEN = "/api/lessonplan/generate"


async def test_generate_and_get(client, fake_ai):
    r, final = await generate_plan(client, {"title": "导数的几何意义", "period": "2 课时",
                                            "student_level": "较好", "requirements": "多举例"})
    assert r.status_code == 200, r.text
    assert final["status"] == "completed", final.get("error_message")
    assert final["content"] == DEFAULT_LESSONPLAN
    assert fake_ai.features() == ["lessonplan"]
    p = prompt_text(fake_ai.calls[0])
    assert "导数的几何意义" in p and "2 课时" in p and "多举例" in p

    gb = (await client.get(f"/api/lessonplan/{final['id']}")).json()
    assert gb["title"] == "导数的几何意义" and gb["period"] == "2 课时"
    assert gb["content"] == DEFAULT_LESSONPLAN


async def test_generate_returns_processing_then_completes(client, fake_ai):
    fake_ai.delay = 0.3
    r = await client.post(GEN, data={"title": "异步教案"})
    body = r.json()
    assert body["status"] == "processing" and body["content"] in ("", None)
    final = await poll_job(client, body, kind="lessonplan", timeout=10)
    assert final["status"] == "completed"
    stages = [s for _, s in final["_history"]]
    assert stages[-1] == "生成完成"


async def test_generate_wait_true(client, fake_ai):
    r = await client.post(GEN, data={"title": "同步教案", "wait": "true"})
    assert r.status_code == 200
    assert r.json()["content"] == DEFAULT_LESSONPLAN


async def test_generate_uses_question_bank_context(client, fake_ai):
    add = await client.post("/api/questionbank/add", data={
        "question_text": "三角函数 RAGMARK 求值", "answer": "1", "question_type": "填空题",
        "subject": "数学", "education_level": "高中", "knowledge_points": '["三角函数"]'})
    assert add.status_code == 200
    r, final = await generate_plan(client, {"title": "三角函数"})
    assert final["status"] == "completed"
    assert "RAGMARK" in prompt_text(fake_ai.calls[0])
    assert final["retrieved_questions_count"] >= 1


async def test_get_missing_plan_404(client):
    assert (await client.get("/api/lessonplan/987654")).status_code == 404


async def test_generate_requires_title(client, fake_ai):
    assert (await client.post(GEN, data={})).status_code == 422
    assert (await client.post(GEN, data={"title": "   "})).status_code == 400
    assert fake_ai.calls == []


async def test_ai_failure_marks_plan_failed(client, fake_ai):
    fake_ai.fail_features = {"lessonplan"}
    r, final = await generate_plan(client, {"title": "失败课题"})
    assert final["status"] == "failed"
    assert "fake upstream failure" in final["error_message"]
    r = await client.post(GEN, data={"title": "失败课题", "wait": "true"})
    assert r.status_code == 502 and "fake upstream failure" in r.json()["detail"]
    assert (await client.get("/health")).status_code == 200


async def test_list_edit_delete_regenerate(client, fake_ai):
    tag = uuid.uuid4().hex[:6]
    _, final = await generate_plan(client, {"title": f"列表课题{tag}"})
    pid = final["id"]
    lst = await client.get("/api/lessonplan/list", params={"keyword": tag})
    assert lst.status_code == 200
    body = lst.json()
    assert body["total"] == 1 and body["items"][0]["id"] == pid
    assert "content" not in body["items"][0] and body["items"][0]["preview"]

    up = await client.put(f"/api/lessonplan/{pid}", json={"title": f"改名{tag}", "content": "# 手工修改"})
    assert up.status_code == 200 and up.json()["content"] == "# 手工修改"
    assert (await client.put(f"/api/lessonplan/{pid}", json={"title": " "})).status_code == 400
    assert (await client.get(f"/api/lessonplan/{pid}")).json()["title"] == f"改名{tag}"

    rg = await client.post(f"/api/lessonplan/{pid}/regenerate")
    assert rg.status_code == 200
    final = await poll_job(client, rg.json(), kind="lessonplan")
    assert final["content"] == DEFAULT_LESSONPLAN

    d = await client.delete(f"/api/lessonplan/{pid}")
    assert d.status_code == 200
    assert (await client.get(f"/api/lessonplan/{pid}")).status_code == 404
    assert (await client.delete(f"/api/lessonplan/{pid}")).status_code == 404


async def test_edit_while_generating_conflicts(client, fake_ai):
    fake_ai.delay = 0.5
    r = await client.post(GEN, data={"title": "生成中"})
    pid = r.json()["id"]
    assert (await client.put(f"/api/lessonplan/{pid}", json={"title": "x"})).status_code == 409
    assert (await client.delete(f"/api/lessonplan/{pid}")).status_code == 409
    await poll_job(client, r.json(), kind="lessonplan", timeout=10)


@pytest.mark.parametrize("fmt", ["md", "txt", "docx"])
async def test_export(client, fake_ai, fmt):
    _, final = await generate_plan(client, {"title": "导出课题"})
    r = await client.get(f"/api/lessonplan/{final['id']}/export", params={"format": fmt})
    assert r.status_code == 200
    assert "filename*=UTF-8''" in r.headers.get("content-disposition", "")
    if fmt == "docx":
        import io
        from docx import Document
        text = "\n".join(p.text for p in Document(io.BytesIO(r.content)).paragraphs)
        assert "测试教案" in text
    else:
        assert "测试教案" in r.content.decode("utf-8")
    bad = await client.get(f"/api/lessonplan/{final['id']}/export", params={"format": "exe"})
    assert bad.status_code == 422


async def test_generate_in_mock_mode(client):
    """No API key => mock lesson plan (per API.md) instead of a 5xx."""
    import ai_client as ai_mod
    assert not ai_mod.ai_client.gateway.enabled
    r, final = await generate_plan(client, {"title": "模拟模式课题"})
    assert final and final["status"] == "completed" and final["content"]
