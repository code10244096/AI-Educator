"""Class / member / homework views and CRUD (backend/API.md, routers/classes.py)."""
import uuid

import pytest

from fakes import DEFAULT_OCR
from helpers import grade


async def test_class_list(client):
    r = await client.get("/api/class/list")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 3
    assert {"class1", "class2", "class3"} <= {c["slug"] for c in items}
    for c in items:
        assert c["name"] and isinstance(c["students"], int)


async def test_homework_list_and_detail(client):
    items = (await client.get("/api/class/class1/homework")).json()["items"]
    assert len(items) >= 10
    for hw in items:
        for key in ("id", "assignment_id", "title", "status", "submitted", "total", "avgScore"):
            assert key in hw
    hw = items[0]
    d = await client.get(f"/api/class/class1/homework/{hw['id']}")
    assert d.status_code == 200 and d.json()["assignment_id"] == hw["assignment_id"]
    assert (await client.get("/api/class/class1/homework/424242")).status_code == 404


async def test_submissions_list(client):
    subs = (await client.get("/api/class/class1/homework/10/submissions")).json()["items"]
    members = (await client.get("/api/class/class1/members")).json()["items"]
    assert len(subs) >= len(members) > 0
    assert {s["gradingStatus"] for s in subs} <= {"已批改", "待批改", "未提交", "批改中"}
    assert any(s["submitStatus"] == "未提交" for s in subs)


async def test_homework_stats_tasks_alerts_archive(client):
    s = (await client.get("/api/class/class1/homework-stats")).json()
    assert s["totalHomeworks"] >= 10 and 0 <= s["submitRate"] <= 100
    for t in (await client.get("/api/class/class1/grading-tasks")).json()["items"]:
        assert 0 <= t["progress"] <= 100
    assert (await client.get("/api/class/class1/alert-students")).status_code == 200
    arch = await client.get("/api/class/class1/score-archive")
    assert arch.status_code == 200
    for a in arch.json()["items"]:
        if a["distribution"]:
            assert abs(sum(d["count"] for d in a["distribution"]) - a["gradedCount"]) <= 0
    assert (await client.get("/api/tasks/all")).status_code == 200
    jobs = await client.get("/api/tasks/jobs", params={"limit": 5})
    assert jobs.status_code == 200 and len(jobs.json()["items"]) <= 5


async def test_class_stats(client):
    r = await client.get("/api/class/stats")
    assert r.status_code == 200 and "average_wrong_count" in r.json()
    assert (await client.get("/api/class/stats", params={"class_slug": "class2"})).status_code == 200
    assert (await client.get("/api/class/stats", params={"class_slug": "nope"})).status_code == 404


@pytest.mark.parametrize("path", [
    "/api/class/nope", "/api/class/nope/homework", "/api/class/nope/homework-stats",
    "/api/class/nope/grading-tasks", "/api/class/nope/alert-students", "/api/class/nope/members",
    "/api/class/nope/homework/1/submissions", "/api/class/class999/homework",
])
async def test_unknown_class_404(client, path):
    assert (await client.get(path)).status_code == 404


async def test_class_crud(client):
    name = f"测试班{uuid.uuid4().hex[:4]}"
    assert (await client.post("/api/class", json={"name": "  "})).status_code == 400
    r = await client.post("/api/class", json={"name": name, "grade": "高二", "subject": "数学"})
    assert r.status_code in (200, 201), r.text
    cls = r.json()
    slug = cls["slug"]
    assert cls["name"] == name and cls["grade"] == "高二"
    assert any(c["slug"] == slug for c in (await client.get("/api/class/list")).json()["items"])
    assert (await client.get(f"/api/class/{slug}")).json()["name"] == name
    assert (await client.get(f"/api/class/{cls['id']}")).status_code == 200, "numeric id accepted"

    up = await client.put(f"/api/class/{slug}", json={"name": name + "改"})
    assert up.status_code == 200 and up.json()["name"] == name + "改"
    assert (await client.put(f"/api/class/{slug}", json={"name": ""})).status_code == 400

    d = await client.delete(f"/api/class/{slug}")
    assert d.status_code == 200
    assert (await client.get(f"/api/class/{slug}")).status_code == 404
    assert not any(c["slug"] == slug for c in (await client.get("/api/class/list")).json()["items"])


async def test_members_crud_and_import(client):
    slug = (await client.post("/api/class", json={"name": f"成员班{uuid.uuid4().hex[:4]}"})).json()["slug"]
    m = await client.post(f"/api/class/{slug}/members", json={"name": "甲同学", "gender": "女", "student_no": "001"})
    assert m.status_code in (200, 201), m.text
    mid = m.json()["id"]
    assert (await client.post(f"/api/class/{slug}/members", json={"name": "甲同学"})).status_code == 409
    assert (await client.post(f"/api/class/{slug}/members", json={"name": " "})).status_code == 400

    imp = await client.post(f"/api/class/{slug}/members/import",
                            data={"text": "姓名,性别,学号\n乙同学,男,002\n丙同学,女,003\n甲同学,女,001\n"})
    assert imp.status_code == 200, imp.text
    assert imp.json()["added_count"] == 2 and imp.json()["skipped_count"] >= 1
    csv = "丁同学,男\n".encode("utf-8")
    imp2 = await client.post(f"/api/class/{slug}/members/import", files={"file": ("m.csv", csv, "text/csv")})
    assert imp2.status_code == 200 and imp2.json()["added_count"] == 1
    bad = await client.post(f"/api/class/{slug}/members/import", files={"file": ("m.exe", b"x", "application/x")})
    assert bad.status_code == 400
    assert (await client.post(f"/api/class/{slug}/members/import", data={})).status_code == 400

    members = (await client.get(f"/api/class/{slug}/members")).json()["items"]
    assert {x["name"] for x in members} == {"甲同学", "乙同学", "丙同学", "丁同学"}
    cls = (await client.get(f"/api/class/{slug}")).json()
    assert cls["students"] == 4

    up = await client.put(f"/api/class/{slug}/members/{mid}", json={"name": "甲改名"})
    assert up.status_code == 200 and up.json()["name"] == "甲改名"
    assert (await client.delete(f"/api/class/{slug}/members/{mid}")).status_code == 200
    assert (await client.delete(f"/api/class/{slug}/members/{mid}")).status_code == 404
    await client.delete(f"/api/class/{slug}")


async def test_homework_crud_grading_and_analysis(client, fake_ai):
    slug = (await client.post("/api/class", json={"name": f"作业班{uuid.uuid4().hex[:4]}"})).json()["slug"]
    await client.post(f"/api/class/{slug}/members/import", data={"text": "小红\n小明\n"})
    assert (await client.post(f"/api/class/{slug}/homework", json={"title": ""})).status_code == 400
    hw = await client.post(f"/api/class/{slug}/homework",
                           json={"title": "新作业", "reference_answer": "1. 2\n2. 4\n3. 6", "deadline": "2026-10-01"})
    assert hw.status_code in (200, 201), hw.text
    hw = hw.json()
    hid, aid = hw["id"], hw["assignment_id"]
    assert hw["total"] == 2 and hw["submitted"] == 0

    # grade a student's work against this homework
    await grade(client, "/api/grader/upload", files={"files": ("h.md", DEFAULT_OCR.encode(), "text/markdown")},
                data={"assignment_id": str(aid), "student_name": "小红"})
    assert "1. 2\n2. 4" in fake_ai.calls[-1]["messages"][0]["content"], "homework reference answer used"
    subs = (await client.get(f"/api/class/{slug}/homework/{hid}/submissions")).json()["items"]
    red = next(s for s in subs if s["name"] == "小红")
    assert red["gradingStatus"] == "已批改" and red["score"] == fake_ai.grade_result["score"]
    assert next(s for s in subs if s["name"] == "小明")["submitStatus"] == "未提交"

    # re-uploading for same student + assignment reuses the submission
    await grade(client, "/api/grader/upload", files={"files": ("h.md", DEFAULT_OCR.encode(), "text/markdown")},
                data={"assignment_id": str(aid), "student_name": "小红"})
    subs2 = (await client.get(f"/api/class/{slug}/homework/{hid}/submissions")).json()["items"]
    assert sum(1 for s in subs2 if s["name"] == "小红") == 1
    assert (await client.get(f"/api/class/{slug}/homework/{hid}")).json()["submitted"] == 1

    an = await client.get(f"/api/class/{slug}/homework/{hid}/analysis")
    assert an.status_code == 200
    q2 = next(q for q in an.json()["questions"] if str(q["question_number"]) == "2")
    assert q2["correct"] == 0 and "小红" in q2["wrong_students"]

    up = await client.put(f"/api/class/{slug}/homework/{hid}", json={"title": "改名作业"})
    assert up.status_code == 200 and up.json()["title"] == "改名作业"
    d = await client.delete(f"/api/class/{slug}/homework/{hid}")
    assert d.status_code == 200 and d.json()["deleted_submissions"] == 1
    assert (await client.get(f"/api/class/{slug}/homework/{hid}")).status_code == 404
    await client.delete(f"/api/class/{slug}")


async def test_delete_class_keeps_notebook(client, fake_ai):
    slug = (await client.post("/api/class", json={"name": f"删除班{uuid.uuid4().hex[:4]}"})).json()["slug"]
    stu = f"删班学生{uuid.uuid4().hex[:4]}"
    await client.post(f"/api/class/{slug}/members", json={"name": stu})
    aid = (await client.post(f"/api/class/{slug}/homework", json={"title": "作业"})).json()["assignment_id"]
    await grade(client, "/api/grader/upload", files={"files": ("h.md", DEFAULT_OCR.encode(), "text/markdown")},
                data={"assignment_id": str(aid), "student_name": stu})
    d = await client.delete(f"/api/class/{slug}")
    assert d.status_code == 200 and d.json()["deleted_submissions"] == 1
    nb = (await client.get("/api/notebook/list", params={"student_name": stu})).json()
    assert len(nb) == fake_ai.grade_result["wrong_count"], "错题本保留 per API.md"


async def test_dataset_submission_visible_in_class(client):
    subs = (await client.get("/api/class/class1/homework/9/submissions")).json()["items"]
    assert any(s.get("isTestData") for s in subs), "seed should mark one dataset-backed submission"
