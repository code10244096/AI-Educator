"""Question bank + wrong-question notebook contracts."""
import uuid

import pytest

from fakes import DEFAULT_VARIANTS


def _q(text, **extra):
    d = {"question_text": text, "answer": "42", "question_type": "填空题",
         "subject": "数学", "education_level": "高中", "knowledge_points": '["函数"]', "difficulty": "2"}
    d.update(extra)
    return d


async def test_add_list_detail_search(client):
    marker = f"QB{uuid.uuid4().hex[:8]}"
    r = await client.post("/api/questionbank/add", data=_q(f"题目 {marker}", year="2024"))
    assert r.status_code == 200, r.text
    qid = r.json()["id"]

    lst = (await client.get("/api/questionbank/list", params={"year": 2024, "limit": 100})).json()
    assert any(q["id"] == qid for q in lst)
    d = (await client.get(f"/api/questionbank/{qid}")).json()
    assert d["knowledge_points"] == ["函数"] and d["variants"] == []
    s = await client.post("/api/questionbank/search", data={"keyword": marker})
    assert [q["id"] for q in s.json()] == [qid]
    assert (await client.get("/api/questionbank/99999999")).status_code == 404


async def test_batch_add(client):
    marker = f"BATCH{uuid.uuid4().hex[:6]}"
    payload = [{"question_text": f"{marker} {i}", "answer": "1", "question_type": "填空题",
                "subject": "数学", "education_level": "高中", "knowledge_points": ["数列"]} for i in range(3)]
    r = await client.post("/api/questionbank/batch-add", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["added_count"] == 3
    s = await client.post("/api/questionbank/search", data={"keyword": marker})
    assert len(s.json()) == 3


# FINDING F-03 (at HEAD): /questionbank/stats was shadowed by /questionbank/{question_id} -> 422. Fixed in the
# working tree during this session; kept as a regression test.
async def test_questionbank_stats(client):
    r = await client.get("/api/questionbank/stats")
    assert r.status_code == 200
    assert "total" in r.json()


async def test_notebook_upload_txt_generates_variants(client, fake_ai):
    text = "已知 f(x)=x^2，求 f(2)。答案 4"
    r = await client.post("/api/notebook/upload",
                          files={"file": ("wq.txt", text.encode("utf-8"), "text/plain")},
                          data={"knowledge_point": "二次函数NB", "subject": "数学"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] and body["variant_questions"] == DEFAULT_VARIANTS
    assert fake_ai.features() == ["variant"]
    lst = (await client.get("/api/notebook/list", params={"knowledge_point": "二次函数NB"})).json()
    items = lst.get("items", lst) if isinstance(lst, dict) else lst
    assert items[0]["id"] == body["id"]
    assert items[0]["is_mastered"] is False

    m = await client.post(f"/api/notebook/{body['id']}/mastered")
    assert m.status_code == 200
    lst = (await client.get("/api/notebook/list", params={"knowledge_point": "二次函数NB"})).json()
    items = lst.get("items", lst) if isinstance(lst, dict) else lst
    assert items[0]["is_mastered"] is True


async def test_notebook_upload_variant_failure_still_saves(client, fake_ai):
    fake_ai.fail_features = {"variant"}
    r = await client.post("/api/notebook/upload",
                          files={"file": ("wq.md", "求 1+1 的值，答案 2，请写出过程".encode(), "text/markdown")},
                          data={"knowledge_point": "变式失败NB"})
    assert r.status_code == 200
    assert r.json()["variant_questions"] == []


async def test_notebook_upload_bad_format_and_empty(client, fake_ai):
    r = await client.post("/api/notebook/upload", files={"file": ("x.xyz", b"abc", "application/octet-stream")},
                          data={"knowledge_point": "k"})
    assert r.json().get("error_type") == "invalid_format"
    r = await client.post("/api/notebook/upload", files={"file": ("x.txt", b"  ", "text/plain")},
                          data={"knowledge_point": "k"})
    assert r.json().get("error_type") == "empty"
    assert fake_ai.calls == []


async def test_notebook_mastered_missing_404(client):
    assert (await client.post("/api/notebook/99999999/mastered")).status_code == 404


async def test_notebook_list_filters_and_paging(client):
    r = await client.get("/api/notebook/list", params={"subject": "数学", "limit": 2, "offset": 0})
    assert r.status_code == 200
    items = r.json()
    items = items.get("items", items) if isinstance(items, dict) else items
    assert len(items) <= 2


async def test_notebook_stats_unmastered_variants_delete(client, fake_ai):
    kp = f"统计NB{uuid.uuid4().hex[:4]}"
    r = await client.post("/api/notebook/upload",
                          files={"file": ("wq.txt", "已知 f(x)=2x，求 f(3)。答案 6".encode(), "text/plain")},
                          data={"knowledge_point": kp})
    qid = r.json()["id"]
    st = await client.get("/api/notebook/stats", params={"subject": "数学"})
    assert st.status_code == 200
    s = st.json()
    assert s["total"] == s["mastered"] + s["unmastered"]
    assert any(k["name"] == kp for k in s["knowledge_points"])

    await client.post(f"/api/notebook/{qid}/mastered")
    assert (await client.post(f"/api/notebook/{qid}/unmastered")).status_code == 200
    lst = (await client.get("/api/notebook/list", params={"knowledge_point": kp, "is_mastered": "false"})).json()
    assert [i["id"] for i in lst] == [qid]
    assert lst[0]["source"] == "manual"

    v = await client.post(f"/api/notebook/{qid}/variants", data={"count": "2"})
    assert v.status_code == 200 and v.json()["variant_questions"] == DEFAULT_VARIANTS
    # out-of-range count is clamped to 1..5
    assert (await client.post(f"/api/notebook/{qid}/variants", data={"count": "9"})).status_code == 200
    assert "5道" in fake_ai.calls[-1]["messages"][0]["content"]
    fake_ai.fail_features = {"variant"}
    assert (await client.post(f"/api/notebook/{qid}/variants")).status_code == 502

    assert (await client.delete(f"/api/notebook/{qid}")).status_code == 200
    assert (await client.delete(f"/api/notebook/{qid}")).status_code == 404
    assert (await client.post("/api/notebook/99999999/unmastered")).status_code == 404


async def test_notebook_image_ocr_failure_502(client, fake_ai):
    from testenv import GAOKAO_SCAN_DIR
    fake_ai.fail_features = {"ocr"}
    jpg = (GAOKAO_SCAN_DIR / "20240608-3.jpg").read_bytes()
    r = await client.post("/api/notebook/upload", files={"file": ("q.jpg", jpg, "image/jpeg")},
                          data={"knowledge_point": "ocr失败"})
    assert r.status_code == 502 and r.json()["detail"]
