"""第④组 批改可信：R1-008 失败判定、统一计分、逐题改判、复核状态。
上线标准：L-F04、L-F05（接口部分；页面部分见浏览器用例 B-008-*）。
"""
import copy
import io
import json
import sqlite3

import pytest

from qa_helpers import (NEW_PASSWORD, add_member, class_key, create_class, create_homework, fresh_env,
                        hw_key, items_of, run_manage, run_runner, uniq, upload, wait_submission)

pytestmark = pytest.mark.xfail(reason="待开发：第④组 批改可信（R1-008）", run=False)

Q = lambda n, ok, **kw: {"question_number": n, "question_text": f"第{n}题 题干 x^{n}", "student_answer": f"s{n}",  # noqa: E731
                         "correct_answer": f"c{n}", "is_correct": ok, "explanation": "解析", **kw}
FOUR_TWO = {"total_questions": 4, "correct_count": 2, "wrong_count": 2, "score": 99,   # 模型自报分数故意写错
            "questions": [Q(1, True), Q(2, False), Q(3, False), Q(4, True)]}


def _png() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "white").save(buf, "PNG")
    return buf.getvalue()


async def _setup(t, n_members=1):
    ck = class_key(await create_class(t.client))
    ms = [await add_member(t.client, ck, f"学生{i}", f"20259{i:02d}") for i in range(n_members)]
    hw = await create_homework(t.client, ck, uniq("可信作业"), reference_answer="1. c1\n2. c2\n3. c3\n4. c4")
    return ck, hw, ms


async def _grade(t, hw, m, **kw):
    r = await upload(t.client, assignment_id=hw["assignment_id"], member_id=m["id"], student_name=m["name"], **kw)
    assert r.status_code in (200, 202), r.text
    return await wait_submission(t.client, int(r.json()["submission_id"]))


async def _notebook_for(t, sid):
    return [q for q in items_of((await t.client.get("/api/notebook/list", params={"limit": 500})).json())
            if q.get("submission_id") == sid]


async def _stats(t, ck, hw, m):
    hk = hw_key(hw)
    an = (await t.client.get(f"/api/class/{ck}/homework/{hk}/analysis")).json()
    arch = items_of((await t.client.get(f"/api/class/{ck}/score-archive")).json())
    a = next((x for x in arch if str(x.get("assignment_id")) == str(hw["assignment_id"])), None)
    hwd = (await t.client.get(f"/api/class/{ck}/homework/{hk}")).json()
    mem = next(x for x in items_of((await t.client.get(f"/api/class/{ck}/members")).json()) if x["id"] == m["id"])
    return {"analysis": an, "archive": a, "homework": hwd, "member": mem}


def _q(detail, n):
    return next(q for q in detail["grading_result"]["questions"] if int(q["question_number"]) == n)


# ====================================================================== 失败判定

FAIL_CASES = {
    "空白图片": dict(files=[("blank.png", _png(), "image/png")], ocr=""),
    "少于10个有效字符": dict(files=[("a.txt", "abc 。".encode(), "text/plain")]),
    "0 题": dict(grade={"total_questions": 0, "correct_count": 0, "wrong_count": 0, "score": 0, "questions": []}),
    "questions 为空": dict(grade={"total_questions": 3, "correct_count": 3, "score": 100, "questions": []}),
    "JSON 解析失败": dict(grade_raw="抱歉，我无法识别这份作业。"),
}


@pytest.mark.parametrize("case", list(FAIL_CASES))
async def test_unrecognized_submission_is_failed_not_zero(teachers, fake_ai, case):
    """R1-008 AC1 / L-F04：识别不到 / 0 题 / 解析失败 → status=failed + 老师看得懂的原因；不写分、不进任何统计。"""
    spec = FAIL_CASES[case]
    if "ocr" in spec:
        fake_ai.responses["ocr"] = spec["ocr"]
    if "grade" in spec:
        fake_ai.grade_result = spec["grade"]
    if "grade_raw" in spec:
        fake_ai.responses["grade"] = spec["grade_raw"]
    t = await teachers()
    ck, hw, (m,) = await _setup(t)
    d = await _grade(t, hw, m, files=spec.get("files"))
    assert d["status"] == "failed", f"{case}: {d['status']} score={d.get('score')}"
    assert d.get("score") is None, f"失败不应写分: {d.get('score')}"
    msg = d.get("error_message") or ""
    if case in ("空白图片", "少于10个有效字符", "0 题", "questions 为空"):
        assert "未识别到题目" in msg, msg
    assert not any(w in msg.lower() for w in ("traceback", "exception", "json", "keyerror")), msg
    assert not await _notebook_for(t, d["submission_id"]), "失败的批改不应同步错题"
    s = await _stats(t, ck, hw, m)
    assert s["analysis"].get("graded_count", 0) == 0 and s["analysis"].get("analyzed_count", 0) == 0, s["analysis"]
    assert s["archive"] is None or s["archive"].get("gradedCount", 0) == 0, s["archive"]
    assert s["homework"].get("avgScore") in (None, "-", ""), s["homework"].get("avgScore")
    assert s["member"].get("gradedCount", 0) == 0 and s["member"].get("avgScore") in (None, "-"), s["member"]


async def test_llm_failure_message_is_teacher_friendly(teachers, fake_ai):
    """R1-008 方案：模型不可用时失败原因为“AI 服务暂时不可用，请稍后重试”一类中文，不暴露技术细节。"""
    fake_ai.fail_features = {"grade"}
    t = await teachers()
    ck, hw, (m,) = await _setup(t)
    d = await _grade(t, hw, m)
    assert d["status"] == "failed"
    msg = d.get("error_message") or ""
    assert "稍后重试" in msg and fake_ai.fail_message not in msg, msg


# ====================================================================== 计分与改判

async def test_score_computed_from_is_correct(teachers, fake_ai):
    """R1-008 计分口径：score = 正确题数/总题数×100（保留 1 位），不采用模型自报分数与计数。"""
    g = copy.deepcopy(FOUR_TWO)
    g.update(total_questions=10, correct_count=9)
    fake_ai.grade_result = g
    t = await teachers()
    ck, hw, (m,) = await _setup(t)
    d = await _grade(t, hw, m)
    assert d["status"] == "completed"
    assert d["score"] == 50, d["score"]
    gr = d["grading_result"]
    assert gr["total_questions"] == 4 and gr["correct_count"] == 2 and gr["wrong_count"] == 2, gr
    fake_ai.grade_result = {"questions": [Q(1, True), Q(2, True), Q(3, False)]}
    m2 = await add_member(t.client, ck, "三题生", "2025990")
    d = await _grade(t, hw, m2)
    assert d["score"] == 66.7, d["score"]


async def test_override_recomputes_score_notebook_analysis_archive(teachers, fake_ai):
    """R1-008 AC2 / L-F05：4 题对 2 → 50；第 3 题改判为对 → 75，错题本少 1 条，逐题正确率、成绩档案、学生均分同步，刷新后保持。"""
    fake_ai.grade_result = copy.deepcopy(FOUR_TWO)
    t = await teachers()
    ck, hw, (m,) = await _setup(t)
    d = await _grade(t, hw, m)
    sid = d["submission_id"]
    assert d["score"] == 50
    assert len(await _notebook_for(t, sid)) == 2
    before = await _stats(t, ck, hw, m)
    q3 = next(q for q in before["analysis"]["questions"] if int(q["question_number"]) == 3)
    assert q3["correct"] == 0
    r = await t.client.patch(f"/api/grader/{sid}/questions/3", json={"is_correct": True, "teacher_comment": "过程正确，结论笔误"})
    assert r.status_code == 200, r.text
    assert r.json().get("score") == 75, r.json()
    detail = (await t.client.get(f"/api/grader/{sid}")).json()
    assert detail["score"] == 75 and detail["wrong_count"] == 1
    q = _q(detail, 3)
    assert q["is_correct"] is True and q.get("teacher_comment") == "过程正确，结论笔误"
    assert detail.get("teacher_modified") is True or q.get("teacher_modified") is True, detail.keys()
    assert detail["grading_result"]["correct_count"] == 3
    nb = await _notebook_for(t, sid)
    assert len(nb) == 1, nb
    after = await _stats(t, ck, hw, m)
    q3 = next(q for q in after["analysis"]["questions"] if int(q["question_number"]) == 3)
    assert q3["correct"] == 1 and not q3.get("wrong_students"), q3
    assert after["archive"]["avgScore"] == 75, after["archive"]
    assert float(after["member"]["avgScore"]) == 75, after["member"]
    again = (await t.client.get(f"/api/grader/{sid}")).json()
    assert again["score"] == 75 and _q(again, 3)["is_correct"] is True


async def test_override_to_wrong_adds_teacher_notebook_entry(teachers, fake_ai):
    """R1-008 AC3：把原判“对”的题改判为“错” → 错题本新增该题，来源标注“老师改判”。"""
    fake_ai.grade_result = copy.deepcopy(FOUR_TWO)
    t = await teachers()
    ck, hw, (m,) = await _setup(t)
    d = await _grade(t, hw, m)
    sid = d["submission_id"]
    r = await t.client.patch(f"/api/grader/{sid}/questions/1", json={"is_correct": False})
    assert r.status_code == 200 and r.json().get("score") == 25, r.text
    nb = await _notebook_for(t, sid)
    assert len(nb) == 3
    new = [q for q in nb if "第1题" in q["question_text"]]
    assert new, nb
    shown = json.dumps(new[0], ensure_ascii=False)
    assert "老师改判" in shown or str(new[0].get("source", "")).startswith("teacher"), new[0]


async def test_override_validation(teachers, fake_ai):
    """R1-008 方案：题号不存在 → 404；未完成/失败的提交不能改判（4xx）。"""
    t = await teachers()
    ck, hw, (m,) = await _setup(t)
    d = await _grade(t, hw, m)
    r = await t.client.patch(f"/api/grader/{d['submission_id']}/questions/99", json={"is_correct": True})
    assert r.status_code == 404, r.text
    fake_ai.grade_result = {"total_questions": 0, "questions": []}
    m2 = await add_member(t.client, ck, "失败生", "2025991")
    f = await _grade(t, hw, m2)
    assert f["status"] == "failed"
    r = await t.client.patch(f"/api/grader/{f['submission_id']}/questions/1", json={"is_correct": True})
    assert 400 <= r.status_code < 500, r.text


async def _retry(t, sid):
    r = await t.client.post(f"/api/grader/{sid}/retry")
    if r.status_code == 409 and "改判" in r.text:
        r = await t.client.post(f"/api/grader/{sid}/retry", data={"confirm_overwrite": "true", "force": "true",
                                                                    "confirm": "true"})
    assert r.status_code in (200, 202), r.text
    return await wait_submission(t.client, sid)


async def test_regrade_clears_overrides(teachers, fake_ai):
    """R1-008 AC4（接口部分）：已改判的提交重新批改后改判记录被清除（页面二次确认见 B-008-4）。"""
    fake_ai.grade_result = copy.deepcopy(FOUR_TWO)
    t = await teachers()
    ck, hw, (m,) = await _setup(t)
    d = await _grade(t, hw, m)
    sid = d["submission_id"]
    assert (await t.client.patch(f"/api/grader/{sid}/questions/3", json={"is_correct": True})).status_code == 200
    d2 = await _retry(t, sid)
    assert d2["status"] == "completed" and d2["score"] == 50, d2.get("score")
    assert not d2.get("teacher_modified") and not _q(d2, 3).get("teacher_modified"), "重批后改判标记应清除"
    assert _q(d2, 3)["is_correct"] is False
    assert len(await _notebook_for(t, sid)) == 2


# ====================================================================== 复核状态与 AI 提示

async def _mark_reviewed(app, t, sid):
    from fastapi.routing import APIRoute
    cands = [r for r in app.routes if isinstance(r, APIRoute) and r.path.startswith("/api/grader/{submission_id}")
             and "review" in r.path]
    if cands:
        r0 = cands[0]
        method = sorted(r0.methods - {"HEAD"})[0]
        return await t.client.request(method, r0.path.replace("{submission_id}", str(sid)),
                                      json={"review_status": "reviewed"})
    return await t.client.patch(f"/api/grader/{sid}", json={"review_status": "reviewed"})


async def test_review_status_flow(app, teachers, fake_ai):
    """R1-008 AC5（接口部分）：批改完成为 pending_review；标记已复核后为 reviewed；名录行带 review_status。"""
    t = await teachers()
    ck, hw, ms = await _setup(t, 2)
    d1 = await _grade(t, hw, ms[0])
    d2 = await _grade(t, hw, ms[1])
    assert d1.get("review_status") == "pending_review", d1.get("review_status")
    r = await _mark_reviewed(app, t, d1["submission_id"])
    assert r.status_code == 200, r.text
    assert (await t.client.get(f"/api/grader/{d1['submission_id']}")).json()["review_status"] == "reviewed"
    rows = items_of((await t.client.get(f"/api/class/{ck}/homework/{hw_key(hw)}/submissions")).json())
    st = {x.get("submission_id"): x.get("review_status") for x in rows if x.get("submission_id")}
    assert st == {d1["submission_id"]: "reviewed", d2["submission_id"]: "pending_review"}, st


async def test_needs_review_and_reference_issue_passthrough(teachers, fake_ai):
    """R1-008 AC6 与“建议复核”：模型返回的 needs_review / reference_issue 原样保存并在名录标出。"""
    g = copy.deepcopy(FOUR_TWO)
    g["questions"][1]["needs_review"] = True
    g["questions"][2]["reference_issue"] = "参考答案“a≥2”有误，应为 a≤2"
    fake_ai.grade_result = g
    t = await teachers()
    ck, hw, (m,) = await _setup(t)
    d = await _grade(t, hw, m)
    assert _q(d, 2).get("needs_review") is True
    assert _q(d, 3).get("reference_issue") == "参考答案“a≥2”有误，应为 a≤2"
    rows = items_of((await t.client.get(f"/api/class/{ck}/homework/{hw_key(hw)}/submissions")).json())
    row = next(x for x in rows if x.get("submission_id") == d["submission_id"])
    assert row.get("needs_review") is True or "建议复核" in json.dumps(row, ensure_ascii=False), row


async def test_grading_prompt_asks_for_review_fields(teachers, fake_ai):
    """R1-008 方案：批改提示词要求逐题返回 needs_review 与 reference_issue。"""
    from fakes import prompt_text
    t = await teachers()
    ck, hw, (m,) = await _setup(t)
    await _grade(t, hw, m)
    prompts = [prompt_text(c) for c in fake_ai.calls if c["feature"] == "grade"]
    assert prompts and all("needs_review" in p and "reference_issue" in p for p in prompts)


# ====================================================================== 迁移

@pytest.mark.slow
def test_migration_zero_question_records_become_failed(tmp_path):
    """R1-008 AC7：库中 completed 且 0 题的记录迁移为 failed（原因“未识别到题目”）并从统计剔除；
    旧的“有分数但无逐题明细”的演示记录不受影响（无损）。"""
    env = fresh_env(tmp_path)
    p, _ = run_runner("initdb", env)
    assert p.returncode == 0, (p.stdout + p.stderr)[-800:]
    from qa_helpers import db_path_from_url
    db = db_path_from_url(env["DATABASE_URL"])
    con = sqlite3.connect(str(db))
    cur = con.cursor()
    cur.execute("INSERT INTO classes (class_name, subject, grade) VALUES ('迁移班', '数学', '高三')")
    cid = cur.lastrowid
    cur.execute("INSERT INTO homework_assignments (title, class_id, subject) VALUES ('高考数学作业集10', ?, '数学')", (cid,))
    aid = cur.lastrowid
    good = lambda s: json.dumps({"total_questions": 2, "correct_count": 2 if s == 100 else 1, "score": s,  # noqa: E731
                                 "questions": [Q(1, True), Q(2, s == 100)]}, ensure_ascii=False)
    rows = [("甲", "completed", 100, good(100)), ("乙", "completed", 50, good(50)),
            ("丙", "completed", 0, json.dumps({"total_questions": 0, "correct_count": 0, "score": 0, "questions": []})),
            ("丁", "completed", 75, None)]
    ids = {}
    for name, st, score, gr in rows:
        cur.execute("INSERT INTO class_members (class_id, name) VALUES (?, ?)", (cid, name))
        cur.execute("INSERT INTO homework_submissions (assignment_id, student_name, status, grading_status, score, "
                    "grading_result, submit_time) VALUES (?, ?, ?, '已批改', ?, ?, '2026-09-01 10:00')",
                    (aid, name, st, score, gr))
        ids[name] = cur.lastrowid
    con.commit()
    con.close()
    user = uniq("mig")
    for args in (("create-user", "--username", user, "--name", "迁移老师", "--password", NEW_PASSWORD,
                  "--no-force-change"), ("assign-orphans", "--username", user)):
        pm = run_manage(*args, env=env)
        assert pm.returncode == 0, (pm.stdout + pm.stderr)[-800:]
    p, res = run_runner("boot", env, extra={"users": [{"username": user, "password": NEW_PASSWORD, "requests": [
        {"path": f"/api/class/{cid}/score-archive"}, {"path": f"/api/class/{cid}/homework/{aid}"}]}]})
    assert p.returncode == 0 and res, (p.stdout + p.stderr)[-1500:]
    con = sqlite3.connect(str(db))
    st = {n: con.execute("SELECT status, error_message, score FROM homework_submissions WHERE id = ?", (i,)).fetchone()
          for n, i in ids.items()}
    con.close()
    assert st["丙"][0] == "failed" and "未识别到题目" in (st["丙"][1] or "") and st["丙"][2] is None, st["丙"]
    assert st["甲"][0] == st["乙"][0] == "completed", st
    assert st["丁"][0] == "completed" and st["丁"][2] == 75, f"无逐题明细的旧记录不应被改为失败: {st['丁']}"
    arch = items_of(res["users"][0]["results"][0]["body"])
    a = next(x for x in arch if "作业集10" in x["name"])
    assert a["gradedCount"] == 3 and a["avgScore"] == 75, a
