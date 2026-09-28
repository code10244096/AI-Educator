"""R1-006 工作台汇总 GET /api/dashboard：必须登录；只统计当前教师自己的数据；计数口径与作业详情一致。"""
import uuid

import pytest

import database
from models import HomeworkSubmission, LessonPlan

HAS_REVIEW = hasattr(HomeworkSubmission, "review_status")
HAS_MEMBER = hasattr(HomeworkSubmission, "member_id")


def _walk_numbers(x, out):
    if isinstance(x, dict):
        for v in x.values():
            _walk_numbers(v, out)
    elif isinstance(x, list):
        out.append(len(x))
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        out.append(x)
    return out


async def _setup(c, members=4):
    """班级 + 学生 + 作业；返回 (class_id, assignment_id, member_ids, teacher_id)"""
    cls = (await c.post("/api/class", json={"name": f"工作台班{uuid.uuid4().hex[:4]}"})).json()
    key = cls.get("slug") or cls["id"]
    member_ids = []
    for i in range(members):
        m = (await c.post(f"/api/class/{key}/members", json={"name": f"学生{i}", "student_no": f"W{uuid.uuid4().hex[:6]}"})).json()
        member_ids.append(m["id"])
    hw = (await c.post(f"/api/class/{key}/homework", json={"title": "工作台作业", "reference_answer": "1. A"})).json()
    me = (await c.get("/api/auth/me")).json()
    return cls["id"], hw["assignment_id"], member_ids, me["id"]


async def _add_submission(assignment_id, teacher_id, name, status, *, member_id=None, score=None, review=None):
    async with database.AsyncSessionLocal() as db:
        sub = HomeworkSubmission(assignment_id=assignment_id, teacher_id=teacher_id, student_name=name,
                                 status=status, score=score,
                                 grading_status={"completed": "已批改", "processing": "批改中"}.get(status, "待批改"))
        if HAS_MEMBER and member_id:
            sub.member_id = member_id
        if HAS_REVIEW and review:
            sub.review_status = review
        db.add(sub)
        await db.commit()
        return sub.id


async def test_dashboard_requires_login(anon_client):
    r = await anon_client.get("/api/dashboard")
    assert r.status_code == 401


async def test_dashboard_new_teacher_all_zero(make_teacher):
    c = await make_teacher()
    r = await c.get("/api/dashboard")
    assert r.status_code == 200, r.text
    d = r.json()
    for key in ("counts", "targets", "recent_assignments", "classes", "recent_lesson_plans"):
        assert key in d
    assert not any(_walk_numbers(d, [])), d
    assert list(d["counts"])[:4] == ["pending_review", "processing", "failed", "collecting"]


async def test_dashboard_counts_and_links(make_teacher):
    c = await make_teacher()
    class_id, aid, mids, tid = await _setup(c, members=4)
    await _add_submission(aid, tid, "学生0", "completed", member_id=mids[0], score=80.0, review="pending_review")
    await _add_submission(aid, tid, "学生1", "completed", member_id=mids[1], score=60.0, review="reviewed")
    await _add_submission(aid, tid, "学生2", "failed", member_id=mids[2])
    await _add_submission(aid, tid, "学生3", "processing", member_id=mids[3])

    d = (await c.get("/api/dashboard")).json()
    counts = d["counts"]
    if HAS_REVIEW:
        assert counts["pending_review"] == 1
    assert counts["processing"] == 1
    assert counts["failed"] == 1
    # 4 名学生都已上传：不在“收集中”
    assert counts["collecting"] == 0 and counts["missing_students"] == 0

    row = d["recent_assignments"][0]
    assert row["assignment_id"] == aid and row["class_id"] == class_id
    assert row["total_members"] == 4 and row["uploaded"] == 4 and row["completed"] == 2
    assert row["avg_score"] == 70.0  # 失败/批改中的不计入均分
    assert d["targets"]["failed"][0]["assignment_id"] == aid
    assert d["targets"]["processing"][0]["class_id"] == class_id
    cls_row = [x for x in d["classes"] if x["class_id"] == class_id][0]
    assert cls_row["member_count"] == 4 and cls_row["assignment_count"] == 1 and cls_row["avg_score"] == 70.0


async def test_dashboard_collecting_counts_missing_students(make_teacher):
    c = await make_teacher()
    _, aid, mids, tid = await _setup(c, members=3)
    await _add_submission(aid, tid, "学生0", "completed", member_id=mids[0], score=90.0)
    d = (await c.get("/api/dashboard")).json()
    assert d["counts"]["collecting"] == 1
    assert d["counts"]["missing_students"] == 2
    # 已有分数但没有标记 pending_review 的历史记录，不算「等你确认」
    assert d["counts"]["pending_review"] == 0
    assert d["targets"]["missing"][0] == {**d["targets"]["missing"][0], "assignment_id": aid, "count": 2}


async def test_dashboard_isolated_between_teachers(make_teacher):
    a = await make_teacher()
    b = await make_teacher()
    _, aid, mids, tid = await _setup(a, members=2)
    await _add_submission(aid, tid, "学生0", "failed", member_id=mids[0])
    await _add_submission(aid, tid, "学生1", "processing", member_id=mids[1])
    async with database.AsyncSessionLocal() as db:
        db.add(LessonPlan(teacher_id=tid, title="A 的教案", content="# 教案", status="completed"))
        await db.commit()

    da = (await a.get("/api/dashboard")).json()
    assert da["counts"]["failed"] == 1 and da["counts"]["processing"] == 1
    assert [p["title"] for p in da["recent_lesson_plans"]] == ["A 的教案"]

    db_ = (await b.get("/api/dashboard")).json()
    assert not any(_walk_numbers(db_, [])), f"教师 B 看到了教师 A 的数据: {db_}"


@pytest.mark.skipif(not HAS_REVIEW, reason="review_status 列由第④组提供")
async def test_dashboard_review_count_drops_after_reviewed(make_teacher):
    c = await make_teacher()
    _, aid, mids, tid = await _setup(c, members=1)
    sid = await _add_submission(aid, tid, "学生0", "completed", member_id=mids[0], score=100.0, review="pending_review")
    assert (await c.get("/api/dashboard")).json()["counts"]["pending_review"] == 1
    async with database.AsyncSessionLocal() as db:
        sub = await db.get(HomeworkSubmission, sid)
        sub.review_status = "reviewed"
        await db.commit()
    assert (await c.get("/api/dashboard")).json()["counts"]["pending_review"] == 0
