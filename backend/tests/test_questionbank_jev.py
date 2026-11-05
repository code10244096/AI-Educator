"""Jev semantic question-bank search: client logging and route integration."""
import json
import uuid

import httpx
import pytest

from jev_client import JevClient, JevError, RankedCandidate


def _q(text, **extra):
    data = {
        "question_text": text,
        "answer": "42",
        "question_type": "填空题",
        "subject": "数学",
        "education_level": "高中",
        "knowledge_points": '["函数"]',
        "difficulty": "2",
    }
    data.update(extra)
    return data


def _read_call_rows(root):
    rows = []
    for path in root.glob("*/api_calls.jsonl"):
        rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return rows


def _systemone_payload(candidates):
    return {
        "model": "jev-1.14.0-test",
        "answers": {
            f"q_{item['id']}": {"type": "noul", "noul": item["score"]}
            for item in candidates
        },
        "usage": {"input_tokens": 123, "output_tokens": 45},
    }


async def test_jev_client_success_logs_questionbank_search_usage(tmp_path):
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        body = json.loads(request.content)
        return httpx.Response(200, json=_systemone_payload([
            {"id": 1, "score": 0.2},
            {"id": 2, "score": 0.9},
        ]))

    client = JevClient(
        api_key="sk-test-SECRET-1234",
        base_url="https://fake-llm.test/v1",
        log_root=str(tmp_path),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    ranked = await client.rank_candidates(
        keyword="三角函数图象",
        candidates=[
            {"id": 1, "question_text": "干扰题", "knowledge_points": []},
            {"id": 2, "question_text": "目标题", "knowledge_points": ["三角函数"]},
        ],
        subject="数学",
        education_level="高中",
        teacher_id=7,
    )

    assert [item.question_id for item in ranked] == [2, 1]
    assert ranked[0].relevance == 0.9
    assert str(sent[0].url).endswith("/v1/systemone")
    assert sent[0].headers["authorization"] == "Bearer sk-test-SECRET-1234"

    rows = _read_call_rows(tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["feature"] == "questionbank_search"
    assert row["success"] is True
    assert row["model"] == "jev-1.14.0-test"
    assert row["usage"] == {
        "prompt_tokens": 123,
        "completion_tokens": 45,
        "total_tokens": 168,
        "reasoning_tokens": 0,
    }
    assert row["task_meta"]["teacher_id"] == 7
    assert row["task_meta"]["candidate_count"] == 2
    raw_log = json.dumps(row, ensure_ascii=False)
    assert "SECRET" not in raw_log
    assert "目标题" not in raw_log


async def test_jev_client_failure_is_logged(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "upstream boom"})

    client = JevClient(
        api_key="sk-test-1234",
        base_url="https://fake-llm.test/v1",
        log_root=str(tmp_path),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(JevError):
        await client.rank_candidates(
            keyword="导数",
            candidates=[{"id": 1, "question_text": "题"}],
            teacher_id=3,
        )

    rows = _read_call_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["feature"] == "questionbank_search"
    assert rows[0]["success"] is False
    assert rows[0]["usage"]["total_tokens"] == 0
    assert "HTTP 500" in rows[0]["error"]["message"]


class FakeJevSearch:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    async def rank_candidates(self, *, keyword, candidates, subject=None, education_level=None, teacher_id=None):
        self.calls.append({
            "keyword": keyword,
            "candidate_ids": [item["id"] for item in candidates],
            "subject": subject,
            "education_level": education_level,
            "teacher_id": teacher_id,
        })
        if self.fail:
            raise JevError("fake Jev failure")
        ranked = []
        for item in candidates:
            score = 0.92 if "目标" in item["question_text"] else 0.10
            ranked.append(RankedCandidate(question_id=item["id"], relevance=score, candidate=item))
        return ranked


async def test_questionbank_search_uses_jev_and_cache(client, monkeypatch):
    import routers.questionbank as questionbank_router

    marker = f"JEV{uuid.uuid4().hex[:8]}"
    ids = {}
    for label in ("目标", "干扰甲", "干扰乙"):
        response = await client.post("/api/questionbank/add", data=_q(f"{marker} {label} 题干"))
        assert response.status_code == 200, response.text
        ids[label] = response.json()["id"]

    fake = FakeJevSearch()
    monkeypatch.setattr(questionbank_router, "get_jev_client", lambda: fake)

    first = await client.post("/api/questionbank/search", data={"keyword": marker})
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["semantic"] is True
    assert body["fuzzy"] is False
    assert body["matched_count"] == 1
    assert [item["id"] for item in body["results"]] == [ids["目标"]]
    assert len(fake.calls) == 1

    second = await client.post("/api/questionbank/search", data={"keyword": marker})
    assert second.status_code == 200
    assert second.json()["results"] == body["results"]
    assert len(fake.calls) == 1, "相同搜索应命中 10 分钟 TTL 缓存，不应重复调用 Jev"


async def test_questionbank_search_falls_back_when_jev_fails(client, monkeypatch):
    import routers.questionbank as questionbank_router

    marker = f"FBJEV{uuid.uuid4().hex[:8]}"
    response = await client.post("/api/questionbank/add", data=_q(f"{marker} 精确命中题干"))
    assert response.status_code == 200, response.text
    expected_id = response.json()["id"]

    fake = FakeJevSearch(fail=True)
    monkeypatch.setattr(questionbank_router, "get_jev_client", lambda: fake)

    result = await client.post("/api/questionbank/search", data={"keyword": marker})
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["semantic"] is False
    assert body["fuzzy"] is False
    assert [item["id"] for item in body["results"]] == [expected_id]
    assert len(fake.calls) == 1
