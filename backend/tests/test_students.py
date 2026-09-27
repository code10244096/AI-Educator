"""R1-011 同名学生按学号区分；R1-005 作业主键、重新上传更新时间、演示数据开关。"""
import json
import uuid

from fakes import DEFAULT_OCR
from helpers import grade

UPLOAD = "/api/grader/upload"


async def _class(t, name=None):
    return (await t.post("/api/class", json={"name": name or f"同名班{uuid.uuid4().hex[:4]}"})).json()


async def test_import_keeps_same_name_with_different_numbers(make_teacher):
    t = await make_teacher()
    cid = (await _class(t))["id"]
    r = await t.post(f"/api/class/{cid}/members/import", data={"text": "陈晓明,男,2025001\n陈晓明,男,2025004\n"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["added_count"] == 2 and "成功导入 2 名" in body["message"]
    r = await t.post(f"/api/class/{cid}/members/import", data={"text": "张三\n张三\n"})
    body = r.json()
    assert body["added_count"] == 1 and body["skipped_count"] == 1
    assert "重名跳过 1 名：张三" in body["message"]
    r = await t.post(f"/api/class/{cid}/members/import", data={"text": "李四,2025001\n"})
    assert r.json()["added_count"] == 0 and "学号重复跳过 1 名" in r.json()["message"]

    members = (await t.get(f"/api/class/{cid}/members")).json()["items"]
    shown = sorted(m["display_name"] for m in members)
    assert shown == ["张三", "陈晓明（2025001）", "陈晓明（2025004）"]


async def test_add_member_uniqueness_rules(make_teacher):
    t = await make_teacher()
    cid = (await _class(t))["id"]
    assert (await t.post(f"/api/class/{cid}/members", json={"name": "王五", "student_no": "01"})).status_code == 200
    assert (await t.post(f"/api/class/{cid}/members", json={"name": "王五", "student_no": "02"})).status_code == 200
    r = await t.post(f"/api/class/{cid}/members", json={"name": "赵六", "student_no": "01"})
    assert r.status_code == 409 and "学号为 01" in r.json()["detail"]
    assert (await t.post(f"/api/class/{cid}/members", json={"name": "赵六"})).status_code == 200
    r = await t.post(f"/api/class/{cid}/members", json={"name": "赵六"})
    assert r.status_code == 409 and "同名" in r.json()["detail"]


async def test_same_name_students_graded_separately(make_teacher, fake_ai):
    t = await make_teacher()
    cid = (await _class(t))["id"]
    await t.post(f"/api/class/{cid}/members/import", data={"text": "陈晓明,2025001\n陈晓明,2025004\n"})
    members = {m["student_no"]: m for m in (await t.get(f"/api/class/{cid}/members")).json()["items"]}
    hw = (await t.post(f"/api/class/{cid}/homework", json={"title": "单调性练习", "reference_answer": "1. 2"})).json()
    assert hw["id"] == hw["assignment_id"], "作业标识就是主键"
    aid = hw["assignment_id"]

    # 同名学生只给姓名时无法确定是谁 → 400
    r = await t.post(UPLOAD, files={"files": ("x.md", DEFAULT_OCR.encode(), "text/markdown")},
                     data={"assignment_id": str(aid), "student_name": "陈晓明"})
    assert r.status_code == 400 and "学号" in r.json()["detail"]

    fake_ai.grade_result = {**fake_ai.grade_result}
    for no in ("2025001", "2025004"):
        await grade(t, UPLOAD, files={"files": (f"{no}.md", DEFAULT_OCR.encode(), "text/markdown")},
                    data={"assignment_id": str(aid), "member_id": str(members[no]["id"])})

    rows = (await t.get(f"/api/class/{cid}/homework/{aid}/submissions")).json()["items"]
    graded = [r for r in rows if r["submission_id"]]
    assert len(graded) == 2 and len({r["submission_id"] for r in graded}) == 2
    assert sorted(r["display_name"] for r in graded) == ["陈晓明（2025001）", "陈晓明（2025004）"]
    assert all(r["member_id"] in (members["2025001"]["id"], members["2025004"]["id"]) for r in graded)

    an = (await t.get(f"/api/class/{cid}/homework/{aid}/analysis")).json()
    q2 = next(q for q in an["questions"] if str(q["question_number"]) == "2")
    assert sorted(q2["wrong_students"]) == ["陈晓明（2025001）", "陈晓明（2025004）"]
    arch = (await t.get(f"/api/class/{cid}/score-archive")).json()["items"][0]
    assert sorted(s["name"] for s in arch["topStudents"]) == ["陈晓明（2025001）", "陈晓明（2025004）"]
    stats = (await t.get(f"/api/class/{cid}/members")).json()["items"]
    assert all(m["gradedCount"] == 1 for m in stats)

    # 改名后历史成绩仍归属该学生
    mid = members["2025004"]["id"]
    r = await t.put(f"/api/class/{cid}/members/{mid}", json={"name": "陈晓敏"})
    assert r.status_code == 200 and r.json()["display_name"] == "陈晓敏"
    rows = (await t.get(f"/api/class/{cid}/homework/{aid}/submissions")).json()["items"]
    renamed = next(r for r in rows if r["member_id"] == mid)
    assert renamed["submission_id"] and renamed["name"] == "陈晓敏" and renamed["score"] is not None
    assert next(m for m in (await t.get(f"/api/class/{cid}/members")).json()["items"] if m["id"] == mid)["gradedCount"] == 1


async def test_member_from_other_class_rejected(make_teacher, fake_ai):
    t = await make_teacher()
    c1, c2 = (await _class(t))["id"], (await _class(t))["id"]
    m2 = (await t.post(f"/api/class/{c2}/members", json={"name": "外班生"})).json()
    aid = (await t.post(f"/api/class/{c1}/homework", json={"title": "作业"})).json()["assignment_id"]
    r = await t.post(UPLOAD, files={"files": ("x.md", DEFAULT_OCR.encode(), "text/markdown")},
                     data={"assignment_id": str(aid), "member_id": str(m2["id"])})
    assert r.status_code == 400
    assert fake_ai.calls == []


async def test_reupload_updates_submit_time(make_teacher, fake_ai):
    import database
    from models import HomeworkSubmission
    t = await make_teacher()
    cid = (await _class(t))["id"]
    m = (await t.post(f"/api/class/{cid}/members", json={"name": "重传生"})).json()
    aid = (await t.post(f"/api/class/{cid}/homework", json={"title": "作业"})).json()["assignment_id"]
    r = await grade(t, UPLOAD, files={"files": ("x.md", DEFAULT_OCR.encode(), "text/markdown")},
                    data={"assignment_id": str(aid), "member_id": str(m["id"])})
    sid = r.json()["submission_id"]
    async with database.AsyncSessionLocal() as db:
        sub = await db.get(HomeworkSubmission, sid)
        sub.submit_time = "2024-01-18 10:05"
        await db.commit()
    r = await grade(t, UPLOAD, files={"files": ("y.md", DEFAULT_OCR.encode(), "text/markdown")},
                    data={"assignment_id": str(aid), "member_id": str(m["id"])})
    assert r.json()["submission_id"] == sid
    row = next(x for x in (await t.get(f"/api/class/{cid}/homework/{aid}/submissions")).json()["items"]
               if x["member_id"] == m["id"])
    assert row["submitTime"] != "2024-01-18 10:05" and row["submitTime"].startswith("20")
    detail = (await t.get(f"/api/grader/{sid}")).json()
    assert detail["image_count"] == 0, "文本文件不算图片"
    assert detail["class_id"] == cid and detail["homework_id"] == aid and detail["class_name"]


async def test_backfill_member_ids_only_when_unambiguous(make_teacher):
    import database
    from class_service import backfill_member_ids
    from models import HomeworkSubmission
    t = await make_teacher()
    cid = (await _class(t))["id"]
    await t.post(f"/api/class/{cid}/members/import", data={"text": "唯一生\n同名生,01\n同名生,02\n"})
    aid = (await t.post(f"/api/class/{cid}/homework", json={"title": "旧作业"})).json()["assignment_id"]
    async with database.AsyncSessionLocal() as db:
        a = HomeworkSubmission(assignment_id=aid, teacher_id=t.user["id"], student_name="唯一生",
                               status="completed", grading_status="已批改", score=80, image_paths="[]",
                               grading_result=json.dumps({"questions": []}))
        b = HomeworkSubmission(assignment_id=aid, teacher_id=t.user["id"], student_name="同名生",
                               status="completed", grading_status="已批改", score=70, image_paths="[]")
        db.add_all([a, b])
        await db.commit()
        await backfill_member_ids(db)
        await db.commit()
        await db.refresh(a)
        await db.refresh(b)
        assert a.member_id is not None and b.member_id is None
    rows = (await t.get(f"/api/class/{cid}/homework/{aid}/submissions")).json()["items"]
    assert next(r for r in rows if r["display_name"] == "唯一生")["score"] == 80
    orphan = [r for r in rows if not r["in_roster"]]
    assert len(orphan) == 1 and orphan[0]["name"] == "同名生", "有歧义的旧记录单独列出，不归到任何一人名下"


async def test_seed_demo_data_flag(tmp_path, monkeypatch):
    """SEED_DEMO_DATA 关闭时不播种（默认关闭；生产强制关闭）"""
    from config import settings
    from class_service import seed_initial_data
    import database
    monkeypatch.setattr(settings, "SEED_DEMO_DATA", False)
    async with database.AsyncSessionLocal() as db:
        from sqlalchemy import func, select
        from models import ClassInfo
        before = await db.scalar(select(func.count(ClassInfo.id)))
        await seed_initial_data(db)
        assert await db.scalar(select(func.count(ClassInfo.id))) == before
