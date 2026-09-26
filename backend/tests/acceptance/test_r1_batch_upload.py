"""第⑤组 批量上传与队列：R1-007。
上线标准：L-P04（全局并发上限）、L-U06（批改部分，页面见浏览器用例）。
文件名自动对应规则（AC1/AC2）是前端逻辑，用 js/ssr_call.mjs 离线调用前端匹配函数验证。
"""
import asyncio
import copy
import json
import re
import subprocess
import time

import pytest

from qa_helpers import (ACCEPTANCE_DIR, FRONTEND, FRONTEND_SRC, NEW_PASSWORD, add_member, class_key, create_class,
                        create_homework, db_path_from_url, drain_jobs, fresh_env, hw_key, items_of, require_route,
                        run_manage, run_runner, sql, uniq, upload, wait_submission)

pytestmark = pytest.mark.xfail(reason="待开发：第⑤组 批量上传与队列（R1-007）", run=False)

PROGRESS = "/api/class/{class_slug}/homework/{homework_id}/progress"
Q = lambda n, ok, **kw: {"question_number": n, "question_text": f"第{n}题", "student_answer": "a",  # noqa: E731
                         "correct_answer": "a" if ok else "b", "is_correct": ok, "explanation": "", **kw}


async def _class_with(t, n):
    ck = class_key(await create_class(t.client))
    ms = [await add_member(t.client, ck, f"批量生{i}", f"2026{i:03d}") for i in range(n)]
    hw = await create_homework(t.client, ck, uniq("批量作业"))
    return ck, hw, ms


async def _submit(t, hw, m, files=None):
    r = await upload(t.client, assignment_id=hw["assignment_id"], member_id=m["id"], files=files)
    assert r.status_code in (200, 202), r.text
    return int(r.json()["submission_id"])


# ====================================================================== 覆盖已有结果

async def test_reupload_replaces_result_and_old_wrong_questions(teachers, fake_ai):
    """R1-007 AC3：为已批改学生再上传 → 旧结果被替换（名录只有一条），旧的同步错题被移除。"""
    fake_ai.grade_result = {"questions": [Q(1, True), Q(2, False), Q(3, False)]}
    t = await teachers()
    ck, hw, (m,) = await _class_with(t, 1)
    s1 = await _submit(t, hw, m)
    d1 = await wait_submission(t.client, s1)
    assert d1["status"] == "completed"
    nb = lambda: t.client.get("/api/notebook/list", params={"limit": 500})  # noqa: E731
    assert len(items_of((await nb()).json())) == 2
    fake_ai.grade_result = {"questions": [Q(1, True), Q(2, True), Q(3, True)]}
    s2 = await _submit(t, hw, m)
    d2 = await wait_submission(t.client, s2)
    assert d2["status"] == "completed" and d2["score"] == 100
    rows = [x for x in items_of((await t.client.get(f"/api/class/{ck}/homework/{hw_key(hw)}/submissions")).json())
            if x.get("member_id") == m["id"]]
    assert len(rows) == 1 and rows[0]["submission_id"] == s2 and rows[0]["score"] == 100, rows
    subs = [x for x in items_of((await t.client.get("/api/grader/submissions", params={"limit": 200})).json())
            if str(x.get("assignment_id")) == str(hw["assignment_id"])]
    assert len(subs) == 1, f"同一学生同一作业不应留下两条批改记录: {[s['submission_id'] for s in subs]}"
    assert not items_of((await nb()).json()), "旧结果的同步错题应被移除"


# ====================================================================== 队列与并发

async def test_global_concurrency_cap_and_queue_position(teachers, fake_ai, restore_settings):
    """R1-007 AC4 / L-P04：任意时刻 processing ≤ GRADING_CONCURRENCY，其余为“排队中（前面还有 N 份）”。
    跨教师也共享同一全局上限。"""
    restore_settings("GRADING_CONCURRENCY", 2)
    fake_ai.delay = 0.4
    t1, t2 = await teachers(), await teachers()
    _, hw1, ms1 = await _class_with(t1, 5)
    _, hw2, ms2 = await _class_with(t2, 5)
    sids = []
    for m in ms1:
        sids.append((t1, await _submit(t1, hw1, m)))
    for m in ms2:
        sids.append((t2, await _submit(t2, hw2, m)))
    max_proc, stages, statuses = 0, set(), set()
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        ds = [(await t.client.get(f"/api/grader/{sid}")).json() for t, sid in sids]
        proc = sum(1 for d in ds if d["status"] == "processing")
        max_proc = max(max_proc, proc)
        statuses |= {d["status"] for d in ds}
        stages |= {d.get("progress_stage") or "" for d in ds if d["status"] == "queued"}
        if all(d["status"] in ("completed", "failed") for d in ds):
            break
        await asyncio.sleep(0.05)
    assert all(d["status"] == "completed" for d in ds), [d["status"] for d in ds]
    assert max_proc <= 2, f"同时 processing 的提交数 {max_proc} 超过并发上限 2"
    assert "queued" in statuses, f"没有观察到 queued 状态: {statuses}"
    assert any(re.fullmatch(r"排队中（前面还有 \d+ 份）", s) for s in stages), stages


async def test_mock_llm_delay_env(teachers, restore_settings):
    """R1-007 方案：模拟模式支持 MOCK_LLM_DELAY_SECONDS（每次模拟调用等待指定秒数）。"""
    restore_settings("MOCK_LLM_DELAY_SECONDS", 1)
    t = await teachers()
    _, hw, (m,) = await _class_with(t, 1)
    t0 = time.monotonic()
    d = await wait_submission(t.client, await _submit(t, hw, m))
    assert d["status"] == "completed" and time.monotonic() - t0 >= 1.0


async def test_daily_grading_quota(teachers, fake_ai, restore_settings):
    """R1-007 AC9：DAILY_GRADING_QUOTA=2 时同一教师当天第 3 份 → 429“今日批改额度已用完…”；按教师计；调大后恢复。"""
    restore_settings("DAILY_GRADING_QUOTA", 2)
    t, other = await teachers(), await teachers()
    _, hw, ms = await _class_with(t, 3)
    await _submit(t, hw, ms[0])
    await _submit(t, hw, ms[1])
    r = await upload(t.client, assignment_id=hw["assignment_id"], member_id=ms[2]["id"])
    assert r.status_code == 429 and "今日批改额度已用完" in r.json()["detail"], (r.status_code, r.text)
    _, hw2, (mo,) = await _class_with(other, 1)
    await _submit(other, hw2, mo)  # 其他教师不受影响
    await drain_jobs()
    restore_settings("DAILY_GRADING_QUOTA", 300)
    assert (await upload(t.client, assignment_id=hw["assignment_id"], member_id=ms[2]["id"])).status_code in (200, 202)


# ====================================================================== 进度接口

async def test_progress_endpoint_matches_roster(app, teachers, fake_ai):
    """R1-007 AC5（接口部分）：progress 各数字与名录状态一致（5 人：2 份完成且建议复核、1 份失败、2 人未上传）。"""
    require_route(app, PROGRESS)
    fake_ai.grade_result = {"questions": [Q(1, True), Q(2, False, needs_review=True)]}
    t = await teachers()
    ck, hw, ms = await _class_with(t, 5)
    for m in ms[:2]:
        await _submit(t, hw, m)
    await _submit(t, hw, ms[2], files=[("blank.txt", "。。".encode(), "text/plain")])  # → failed（R1-008）
    await drain_jobs()
    p = (await t.client.get(f"/api/class/{ck}/homework/{hw_key(hw)}/progress")).json()
    exp = {"total_members": 5, "uploaded": 3, "queued": 0, "processing": 0, "completed": 2, "failed": 1,
           "needs_review": 2}
    assert {k: p.get(k) for k in exp} == exp, p
    assert "eta_seconds" in p and (p["eta_seconds"] in (0, None))
    rows = items_of((await t.client.get(f"/api/class/{ck}/homework/{hw_key(hw)}/submissions")).json())
    st = [x.get("status") for x in rows if x.get("submission_id")]
    assert st.count("completed") == 2 and st.count("failed") == 1, st


async def test_progress_eta_while_running(app, teachers, fake_ai, restore_settings):
    """R1-007 方案：批改进行中 eta_seconds > 0，queued+processing+completed+failed == uploaded。"""
    require_route(app, PROGRESS)
    restore_settings("GRADING_CONCURRENCY", 1)
    fake_ai.delay = 0.3
    t = await teachers()
    ck, hw, ms = await _class_with(t, 4)
    for m in ms:
        await _submit(t, hw, m)
    p = (await t.client.get(f"/api/class/{ck}/homework/{hw_key(hw)}/progress")).json()
    assert p["uploaded"] == 4
    assert p["queued"] + p["processing"] + p["completed"] + p["failed"] == 4, p
    if p["queued"] + p["processing"]:
        assert (p.get("eta_seconds") or 0) > 0, p
    await drain_jobs()


# ====================================================================== 重启恢复

@pytest.mark.slow
def test_queued_jobs_resume_after_restart(tmp_path):
    """R1-007 AC6：批量进行中后端被杀掉 → 重启后排队中的任务自动继续完成；进行中的标记失败可重试。"""
    env = fresh_env(tmp_path, GRADING_CONCURRENCY="1", MOCK_LLM_DELAY_SECONDS="2")
    p, _ = run_runner("initdb", env)
    assert p.returncode == 0, (p.stdout + p.stderr)[-800:]
    user = uniq("rs")
    pm = run_manage("create-user", "--username", user, "--name", "重启老师", "--password", NEW_PASSWORD,
                    "--no-force-change", env=env)
    assert pm.returncode == 0, (pm.stdout + pm.stderr)[-800:]
    p, first = run_runner("crash_after_batch", env, extra={"username": user, "password": NEW_PASSWORD, "n": 4})
    assert first, (p.stdout + p.stderr)[-1500:]
    before = {s["id"]: s["status"] for s in first["submissions"]}
    assert list(before.values()).count("queued") >= 2, f"用例前提：崩溃时应有排队任务 {before}"
    env2 = dict(env, MOCK_LLM_DELAY_SECONDS="0")
    p, res = run_runner("boot", env2)
    assert p.returncode == 0, (p.stdout + p.stderr)[-1500:]
    db = db_path_from_url(env["DATABASE_URL"])
    after = {sid: sql("SELECT status FROM homework_submissions WHERE id = ?", (sid,), db=db)[0][0] for sid in before}
    for sid, st in before.items():
        if st == "queued":
            assert after[sid] == "completed", f"排队任务 {sid} 重启后未继续: {after}"
        if st == "processing":
            assert after[sid] in ("failed", "completed"), after


# ====================================================================== 文件名自动对应（前端逻辑）

def _matcher_module():
    cands = [p for p in FRONTEND_SRC.rglob("*.js") if re.search(r"match", p.name, re.I)]
    cands += [p for p in FRONTEND_SRC.rglob("*.js*") if re.search(r"export (const|function) match\w*", p.read_text(
        encoding="utf-8", errors="ignore"))]
    if not cands:
        pytest.xfail("待开发：前端文件名匹配函数（请导出纯函数，便于离线验证）")
    p = cands[0]
    fn = re.search(r"export (?:const|function|async function) (match\w*)", p.read_text(encoding="utf-8")).group(1)
    return "src/" + p.relative_to(FRONTEND_SRC).as_posix(), fn


def _node_call(mod, fn, args):
    p = subprocess.run(["node", str(ACCEPTANCE_DIR / "js" / "ssr_call.mjs"), "call", mod, fn,
                        json.dumps(args, ensure_ascii=False)], capture_output=True, text=True, encoding="utf-8",
                       cwd=str(FRONTEND), timeout=120)
    line = next((l for l in p.stdout.splitlines() if l.startswith("RESULT:")), None)
    assert line, p.stdout[-500:] + p.stderr[-800:]
    out = json.loads(line[7:])
    assert "error" not in out, out["error"]
    return out["value"]


def _normalize(result, students):
    """把匹配结果统一成 {学号: [文件名...]} + [未对应]（兼容几种常见返回结构）。"""
    by_id = {s["id"]: s["student_no"] for s in students}
    assigned, unmatched = {}, []
    if isinstance(result, dict):
        unmatched = [f if isinstance(f, str) else f.get("name") for f in (result.get("unmatched") or [])]
        src = result.get("matched") or result.get("assignments") or result.get("byStudent") or {}
        if isinstance(src, dict):
            for k, files in src.items():
                assigned[by_id.get(int(k), k) if str(k).isdigit() else k] = \
                    [f if isinstance(f, str) else f.get("name") for f in files]
        else:
            for row in src:
                sid = row.get("memberId") or row.get("member_id") or (row.get("student") or {}).get("id")
                assigned[by_id[sid]] = [f if isinstance(f, str) else f.get("name") for f in row["files"]]
    return assigned, unmatched


STUDENTS = [{"id": 1, "name": "陈晓明", "student_no": "2025001"}, {"id": 2, "name": "林雨桐", "student_no": "2025002"},
            {"id": 3, "name": "王浩然", "student_no": "2025003"}]


def test_file_matching_rules_basic():
    """R1-007 AC1：陈晓明 2 页（按自然序 1、2）、林雨桐 1 页、王浩然（学号命名）1 页、IMG_0231.jpg 未对应。"""
    mod, fn = _matcher_module()
    files = ["陈晓明_2.jpg", "林雨桐.jpg", "2025003.jpg", "IMG_0231.jpg", "陈晓明_1.jpg"]
    res = _node_call(mod, fn, [[{"name": f} for f in files], STUDENTS])
    assigned, unmatched = _normalize(res, STUDENTS)
    assert assigned.get("2025001") == ["陈晓明_1.jpg", "陈晓明_2.jpg"], res
    assert assigned.get("2025002") == ["林雨桐.jpg"] and assigned.get("2025003") == ["2025003.jpg"], res
    assert unmatched == ["IMG_0231.jpg"], res


def test_file_matching_same_name_uses_student_no():
    """R1-007 AC2：两个陈晓明时 `陈晓明.jpg` 不自动对应；`2025004_陈晓明.jpg` 对应学号 2025004；页序按自然排序（2 < 10）。"""
    mod, fn = _matcher_module()
    students = STUDENTS + [{"id": 4, "name": "陈晓明", "student_no": "2025004"}]
    files = ["陈晓明.jpg", "2025004_陈晓明.jpg", "林雨桐_10.jpg", "林雨桐_2.jpg"]
    res = _node_call(mod, fn, [[{"name": f} for f in files], students])
    assigned, unmatched = _normalize(res, students)
    assert "陈晓明.jpg" in unmatched and "2025001" not in assigned, res
    assert assigned.get("2025004") == ["2025004_陈晓明.jpg"], res
    assert assigned.get("2025002") == ["林雨桐_2.jpg", "林雨桐_10.jpg"], res
