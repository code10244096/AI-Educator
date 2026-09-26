"""第③组 数据与概念清理：R1-005 不播种 / 去开发概念 / 作业主键；R1-011 学号区分同名学生。
上线标准：L-S08、L-F03（代码检索部分）。
"""
import json
import re
import sqlite3
from datetime import datetime

import pytest

from qa_helpers import (NEW_PASSWORD, add_member, class_key, copy_real_db, create_class, create_homework,
                        fresh_env, graded_submission, grep_frontend, hw_key, import_members, items_of, prod_env,
                        run_manage, run_runner, sql, uniq)

pytestmark = pytest.mark.xfail(reason="待开发：第③组 数据与概念清理（R1-005、R1-011）", run=False)

def sql_exec(q, params=()):
    from qa_helpers import db_path_from_url
    con = sqlite3.connect(str(db_path_from_url()), timeout=30)
    try:
        con.execute(q, params)
        con.commit()
    finally:
        con.close()


SEED_TABLES = ["classes", "class_members", "homework_assignments", "homework_submissions"]


# ====================================================================== R1-005 不播种

@pytest.mark.slow
def test_fresh_start_no_demo_seed(tmp_path):
    """R1-005 AC1 / L-S08：全新数据目录以生产配置启动 → 业务表 0 行、users 0 行；数据集接口未注册。"""
    env = prod_env(tmp_path)
    p, res = run_runner("boot", env, extra={"requests": [{"path": "/health"}]})
    assert p.returncode == 0 and res, (p.stdout + p.stderr)[-1500:]
    from qa_helpers import db_path_from_url
    db = db_path_from_url(env["DATABASE_URL"])
    counts = {t: sql(f"SELECT COUNT(*) FROM {t}", db=db)[0][0] for t in SEED_TABLES + ["users"]}
    assert all(v == 0 for v in counts.values()), f"生产首次启动不应有数据: {counts}"
    leaked = [r for r in res["routes"] if "dataset" in r]
    assert not leaked, f"生产环境仍注册了数据集接口: {leaked}"


@pytest.mark.slow
def test_seed_only_when_flag_set(tmp_path):
    """R1-005 方案：开发环境默认也不播种；SEED_DEMO_DATA=true 时才播种。"""
    env = fresh_env(tmp_path / "off")
    p, _ = run_runner("boot", env)
    assert p.returncode == 0, (p.stdout + p.stderr)[-800:]
    from qa_helpers import db_path_from_url
    n = sql("SELECT COUNT(*) FROM classes", db=db_path_from_url(env["DATABASE_URL"]))[0][0]
    assert n == 0, f"未设置 SEED_DEMO_DATA 时仍播种了 {n} 个班级"
    env = fresh_env(tmp_path / "on", SEED_DEMO_DATA="true")
    p, _ = run_runner("boot", env)
    assert p.returncode == 0, (p.stdout + p.stderr)[-800:]
    n = sql("SELECT COUNT(*) FROM classes", db=db_path_from_url(env["DATABASE_URL"]))[0][0]
    assert n > 0, "SEED_DEMO_DATA=true 时应播种演示数据"


# ====================================================================== R1-005 作业主键

async def test_new_homework_url_id_is_primary_key(teachers):
    """R1-005 AC3：新建作业后 URL 中的 ID 等于数据库主键；列表与详情都用主键。"""
    t = await teachers()
    cls = await create_class(t.client)
    ck = class_key(cls)
    hw = await create_homework(t.client, ck, "主键作业")
    assert str(hw["id"]) == str(hw["assignment_id"]), hw
    assert sql("SELECT title FROM homework_assignments WHERE id = ?", (hw["assignment_id"],))[0][0] == "主键作业"
    r = await t.client.get(f"/api/class/{ck}/homework/{hw['assignment_id']}")
    assert r.status_code == 200 and r.json()["title"] == "主键作业"
    for item in items_of((await t.client.get(f"/api/class/{ck}/homework")).json()):
        assert str(item["id"]) == str(item["assignment_id"]), item


@pytest.mark.slow
def test_legacy_homework_accessed_by_primary_key(tmp_path):
    """R1-005 AC3：旧库（含 dataset 作业）迁移后，每个作业按主键访问都得到它自己（不撞号）；
    R1-011 方案：存量提交按班级+姓名回填 member_id。"""
    db = copy_real_db(tmp_path / "qa.db")
    env = fresh_env(tmp_path)
    p, _ = run_runner("initdb", env)
    assert p.returncode == 0, (p.stdout + p.stderr)[-800:]
    user = uniq("legacy")
    for args in (("create-user", "--username", user, "--name", "旧数据老师", "--password", NEW_PASSWORD,
                  "--no-force-change"), ("assign-orphans", "--username", user)):
        pm = run_manage(*args, env=env)
        assert pm.returncode == 0, (pm.stdout + pm.stderr)[-800:]
    hws = sql("SELECT id, class_id, title FROM homework_assignments WHERE class_id IS NOT NULL", db=db)
    reqs = [{"path": f"/api/class/{cid}/homework/{hid}"} for hid, cid, _ in hws]
    p, res = run_runner("boot", env, extra={"users": [{"username": user, "password": NEW_PASSWORD, "requests": reqs}]})
    assert p.returncode == 0 and res, (p.stdout + p.stderr)[-1500:]
    bad = []
    for (hid, _cid, title), r in zip(hws, res["users"][0]["results"]):
        body = r["body"] if isinstance(r["body"], dict) else {}
        if r["status"] != 200 or body.get("title") != title or str(body.get("assignment_id")) != str(hid):
            bad.append(f"{r['path']} -> {r['status']} {str(body)[:80]} (期望《{title}》)")
    assert not bad, "\n".join(bad[:20])
    assert "member_id" in [c[1] for c in sql("PRAGMA table_info(homework_submissions)", db=db)]
    filled = sql("SELECT COUNT(*) FROM homework_submissions WHERE member_id IS NOT NULL", db=db)[0][0]
    assert filled > 0, "存量提交未按班级+姓名回填 member_id"


async def test_reupload_updates_submit_time(teachers, fake_ai):
    """R1-005 AC4：对已批改学生重新上传，名录与批改记录中的时间变为本次上传时间。"""
    t = await teachers()
    ck = class_key(await create_class(t.client))
    m = await add_member(t.client, ck, "林雨桐", "2025002")
    hw = await create_homework(t.client, ck)
    await graded_submission(t.client, assignment_id=hw["assignment_id"], member_id=m["id"])
    row = lambda rows: next(r for r in rows if r.get("member_id") == m["id"])  # noqa: E731
    first = row(items_of((await t.client.get(f"/api/class/{ck}/homework/{hw_key(hw)}/submissions")).json()))
    # 把第一次的提交时间改成旧时间（模拟播种数据里的 2024-01-18 10:05），再重新上传
    sql_exec("UPDATE homework_submissions SET submit_time = '2024-01-18 10:05' WHERE id = ?", (first["submission_id"],))
    d2 = await graded_submission(t.client, assignment_id=hw["assignment_id"], member_id=m["id"])
    today = datetime.now().strftime("%Y-%m-%d")
    second = row(items_of((await t.client.get(f"/api/class/{ck}/homework/{hw_key(hw)}/submissions")).json()))
    assert str(second["submitTime"]).startswith(today), f"名录时间未更新: {second['submitTime']}"
    detail = (await t.client.get(f"/api/grader/{d2['submission_id']}")).json()
    assert str(detail.get("submit_time")).startswith(today), f"批改记录时间未更新: {detail.get('submit_time')}"
    listed = items_of((await t.client.get("/api/grader/submissions", params={"limit": 50})).json())
    mine = [x for x in listed if x["submission_id"] == d2["submission_id"]]
    assert mine and str(mine[0]["submit_time"]).startswith(today), mine


# ====================================================================== R1-005 界面去开发概念（代码检索）

def test_frontend_has_no_dev_concepts():
    """R1-005 AC2 / L-F03（代码部分；页面文本检索见浏览器用例 B-005-2）。"""
    bad = []
    for rx in (r"测试数据|测试集|调试模式|作业\s*#|使用测试数据", r"dataset|datasetFileId|isTestData|hasTestData"):
        bad += grep_frontend(rx, re.I)
    # 班级 slug / 模型名只允许出现在管理员用量页
    for h in grep_frontend(r"['\"`]class\$?\{?|class\d+|gpt-|gemini|deepseek", re.I):
        if "UsageStats" not in h[0] and "className" not in h[2]:
            bad.append(h)
    assert not bad, "\n".join(f"{f}:{n}: {s}" for f, n, s in bad[:30])


# ====================================================================== R1-011 学号区分同名

async def test_import_same_name_different_student_no(teachers):
    """R1-011 AC1：导入“陈晓明,男,2025001”“陈晓明,男,2025004” → 两人都导入，提示“成功导入 2 名”。"""
    t = await teachers()
    ck = class_key(await create_class(t.client))
    r = await import_members(t.client, ck, "陈晓明,男,2025001\n陈晓明,男,2025004")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["added_count"] == 2 and "成功导入 2 名" in body["message"], body
    ms = items_of((await t.client.get(f"/api/class/{ck}/members")).json())
    assert sorted(m["student_no"] for m in ms if m["name"] == "陈晓明") == ["2025001", "2025004"]


async def test_import_duplicate_name_without_no_skipped(teachers):
    """R1-011 AC2：两行“张三”（都无学号）→ 第二行跳过并提示“重名跳过 1 名：张三”。"""
    t = await teachers()
    ck = class_key(await create_class(t.client))
    r = await import_members(t.client, ck, "张三\n张三")
    body = r.json()
    assert body["added_count"] == 1 and body["skipped_count"] == 1, body
    assert "重名跳过 1 名：张三" in body["message"], body["message"]


async def test_add_member_uniqueness_rules(teachers):
    """R1-011 方案：有学号按学号唯一，无学号按姓名唯一。"""
    t = await teachers()
    ck = class_key(await create_class(t.client))
    await add_member(t.client, ck, "陈晓明", "2025001")
    r = await t.client.post(f"/api/class/{ck}/members", json={"name": "陈晓明", "student_no": "2025004"})
    assert r.status_code in (200, 201), "同名不同学号应允许"
    r = await t.client.post(f"/api/class/{ck}/members", json={"name": "陈小明", "student_no": "2025001"})
    assert r.status_code == 409, "学号重复应 409"
    await add_member(t.client, ck, "张三")
    r = await t.client.post(f"/api/class/{ck}/members", json={"name": "张三"})
    assert r.status_code == 409, "无学号同名应 409"


async def test_same_name_students_graded_separately(teachers, fake_ai):
    """R1-011 AC3：两个陈晓明分别上传批改后，名录、成绩档案、逐题做错名单中分开统计、姓名后带学号。"""
    t = await teachers()
    ck = class_key(await create_class(t.client))
    m1 = await add_member(t.client, ck, "陈晓明", "2025001")
    m4 = await add_member(t.client, ck, "陈晓明", "2025004")
    hw = await create_homework(t.client, ck)
    for m in (m1, m4):
        d = await graded_submission(t.client, assignment_id=hw["assignment_id"], member_id=m["id"])
        assert d["status"] == "completed", d
    hk = hw_key(hw)
    rows = [r for r in items_of((await t.client.get(f"/api/class/{ck}/homework/{hk}/submissions")).json())
            if r.get("submission_id")]
    assert {r["member_id"] for r in rows} == {m1["id"], m4["id"]} and len(rows) == 2, rows
    assert len({r["submission_id"] for r in rows}) == 2
    shown = json.dumps(rows, ensure_ascii=False)
    assert "2025001" in shown and "2025004" in shown, "名录中重名学生应带学号"
    an = (await t.client.get(f"/api/class/{ck}/homework/{hk}/analysis")).json()
    wrong_q = next(q for q in an["questions"] if q["total"] and q["correct"] < q["total"])
    ws = wrong_q["wrong_students"]
    assert len(ws) == 2 and len({json.dumps(w, ensure_ascii=False) for w in ws}) == 2, ws
    assert "2025001" in json.dumps(ws, ensure_ascii=False) and "2025004" in json.dumps(ws, ensure_ascii=False), ws
    arch = items_of((await t.client.get(f"/api/class/{ck}/score-archive")).json())
    a = next(x for x in arch if str(x.get("assignment_id")) == str(hw["assignment_id"]))
    assert a["gradedCount"] == 2, a
    ms = items_of((await t.client.get(f"/api/class/{ck}/members")).json())
    assert all(m.get("gradedCount") == 1 for m in ms if m["name"] == "陈晓明"), ms


async def test_rename_member_keeps_history(teachers, fake_ai):
    """R1-011 AC4：修改学生姓名后，其历史批改记录、成绩仍归属该学生。"""
    t = await teachers()
    ck = class_key(await create_class(t.client))
    m = await add_member(t.client, ck, "王浩然", "2025003")
    hw = await create_homework(t.client, ck)
    d = await graded_submission(t.client, assignment_id=hw["assignment_id"], member_id=m["id"])
    r = await t.client.put(f"/api/class/{ck}/members/{m['id']}", json={"name": "王浩燃"})
    assert r.status_code == 200, r.text
    rows = items_of((await t.client.get(f"/api/class/{ck}/homework/{hw_key(hw)}/submissions")).json())
    mine = [x for x in rows if x.get("member_id") == m["id"]]
    assert len(mine) == 1 and mine[0]["submission_id"] == d["submission_id"] and mine[0]["name"].startswith("王浩燃"), mine
    assert not [x for x in rows if x.get("name", "").startswith("王浩然")], "旧名字不应作为另一名学生出现"
    ms = items_of((await t.client.get(f"/api/class/{ck}/members")).json())
    me = next(x for x in ms if x["id"] == m["id"])
    assert me.get("gradedCount") == 1 and me.get("avgScore") is not None, me


async def test_upload_by_member_id_and_foreign_member_rejected(teachers, fake_ai):
    """R1-011 方案：上传接口接受 member_id；member_id 不属于该作业班级 → 4xx。"""
    t = await teachers()
    ck = class_key(await create_class(t.client))
    ck2 = class_key(await create_class(t.client))
    m = await add_member(t.client, ck, "李四", "2025010")
    other = await add_member(t.client, ck2, "外班学生", "2025099")
    hw = await create_homework(t.client, ck)
    d = await graded_submission(t.client, assignment_id=hw["assignment_id"], member_id=m["id"])
    assert d["status"] == "completed"
    rows = items_of((await t.client.get(f"/api/class/{ck}/homework/{hw_key(hw)}/submissions")).json())
    assert any(x.get("member_id") == m["id"] and x.get("submission_id") == d["submission_id"] for x in rows)
    from qa_helpers import upload
    r = await upload(t.client, assignment_id=hw["assignment_id"], member_id=other["id"])
    assert r.status_code in (400, 404), (r.status_code, r.text)
