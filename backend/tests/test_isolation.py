"""R1-002 按教师隔离：教师 B 访问教师 A 的任何资源一律 404、列表不可见；存量数据迁移 assign-orphans。"""
import json
import os
import sqlite3
import subprocess
import sys
import uuid

import pytest

from fakes import DEFAULT_OCR
from helpers import generate_plan, grade, submission_id_of
from testenv import BACKEND_DIR


async def _setup_teacher_a(a):
    """A：班级 + 学生 + 作业 + 一份带文件的批改（自动同步错题）+ 教案"""
    cls = (await a.post("/api/class", json={"name": f"A班{uuid.uuid4().hex[:4]}"})).json()
    slug = cls["slug"]
    member = (await a.post(f"/api/class/{slug}/members", json={"name": "甲同学", "student_no": "A001"})).json()
    hw = (await a.post(f"/api/class/{slug}/homework", json={"title": "A的作业", "reference_answer": "1. 2"})).json()
    r = await grade(a, "/api/grader/upload", files={"files": ("a.md", DEFAULT_OCR.encode(), "text/markdown")},
                    data={"assignment_id": str(hw["assignment_id"]), "student_name": "甲同学"})
    sid = submission_id_of(r.json())
    wrong = (await a.get("/api/notebook/list", params={"limit": 100})).json()
    assert wrong, "A 应有同步错题"
    _, plan = await generate_plan(a, {"title": "A的教案"})
    return {"cls": cls, "slug": slug, "member": member, "hw": hw, "sid": sid, "wq": wrong[0]["id"], "plan": plan["id"]}


async def test_teacher_b_cannot_see_or_touch_teacher_a(make_teacher, fake_ai):
    a = await make_teacher()
    b = await make_teacher()
    d = await _setup_teacher_a(a)
    slug, hid, mid, sid, wq, pid = d["slug"], d["hw"]["id"], d["member"]["id"], d["sid"], d["wq"], d["plan"]
    cid = d["cls"]["id"]

    # A 自己能访问文件
    assert (await a.get(f"/api/grader/{sid}/files/0")).status_code == 200

    not_found = [
        ("GET", f"/api/class/{slug}", None), ("GET", f"/api/class/{cid}", None),
        ("PUT", f"/api/class/{slug}", {"name": "x"}), ("DELETE", f"/api/class/{slug}", None),
        ("GET", f"/api/class/{slug}/members", None), ("POST", f"/api/class/{slug}/members", {"name": "乙"}),
        ("PUT", f"/api/class/{slug}/members/{mid}", {"name": "乙"}),
        ("DELETE", f"/api/class/{slug}/members/{mid}", None),
        ("GET", f"/api/class/{slug}/homework", None), ("POST", f"/api/class/{slug}/homework", {"title": "x"}),
        ("GET", f"/api/class/{slug}/homework/{hid}", None),
        ("PUT", f"/api/class/{slug}/homework/{hid}", {"title": "x"}),
        ("DELETE", f"/api/class/{slug}/homework/{hid}", None),
        ("GET", f"/api/class/{slug}/homework/{hid}/submissions", None),
        ("GET", f"/api/class/{slug}/homework/{hid}/analysis", None),
        ("DELETE", f"/api/class/{slug}/homework/{hid}/submissions/pending", None),
        ("DELETE", f"/api/class/{slug}/homework/{hid}/submissions/keep-first/0", None),
        ("GET", f"/api/class/{slug}/homework-stats", None), ("GET", f"/api/class/{slug}/grading-tasks", None),
        ("GET", f"/api/class/{slug}/alert-students", None), ("GET", f"/api/class/{slug}/score-archive", None),
        ("GET", f"/api/class/stats?class_slug={slug}", None),
        ("GET", f"/api/grader/{sid}", None), ("GET", f"/api/grader/{sid}/files/0", None),
        ("POST", f"/api/grader/{sid}/retry", None), ("DELETE", f"/api/grader/{sid}", None),
        ("POST", f"/api/notebook/{wq}/mastered", None), ("POST", f"/api/notebook/{wq}/unmastered", None),
        ("POST", f"/api/notebook/{wq}/variants", None), ("DELETE", f"/api/notebook/{wq}", None),
        ("GET", f"/api/lessonplan/{pid}", None), ("PUT", f"/api/lessonplan/{pid}", {"title": "x"}),
        ("DELETE", f"/api/lessonplan/{pid}", None), ("POST", f"/api/lessonplan/{pid}/regenerate", None),
        ("GET", f"/api/lessonplan/{pid}/export?format=md", None),
    ]
    failures = []
    for method, url, body in not_found:
        r = await b.request(method, url, json=body) if body is not None else await b.request(method, url)
        if r.status_code != 404:
            failures.append(f"{method} {url} -> {r.status_code}")
    assert not failures, failures

    # B 不能把文件上传到 A 的作业 / 覆盖 A 的提交
    up = await b.post("/api/grader/upload", files={"files": ("b.md", DEFAULT_OCR.encode(), "text/markdown")},
                      data={"assignment_id": str(d["hw"]["assignment_id"])})
    assert up.status_code == 404
    up = await b.post("/api/grader/upload", files={"files": ("b.md", DEFAULT_OCR.encode(), "text/markdown")},
                      data={"submission_id": str(sid)})
    assert up.status_code == 404

    # B 的列表里没有 A 的任何数据
    assert (await b.get("/api/class/list")).json()["items"] == []
    assert (await b.get("/api/grader/submissions", params={"include_seed": "true", "limit": 200})).json()["total"] == 0
    assert (await b.get("/api/notebook/list", params={"limit": 500})).json() == []
    assert (await b.get("/api/notebook/stats")).json()["total"] == 0
    assert (await b.get("/api/lessonplan/list")).json()["total"] == 0
    assert (await b.get("/api/tasks/all")).json()["items"] == []
    assert (await b.get("/api/tasks/jobs")).json()["items"] == []
    assert (await b.get("/api/class/stats")).json()["total_students"] == 0

    # A 的数据毫发无损
    assert (await a.get(f"/api/class/{slug}")).status_code == 200
    assert (await a.get(f"/api/grader/{sid}")).json()["status"] == "completed"
    assert (await a.get(f"/api/lessonplan/{pid}")).status_code == 200
    assert len((await a.get("/api/class/list")).json()["items"]) == 1


async def test_background_job_uses_owner(make_teacher, fake_ai):
    """后台批改使用提交所属教师：错题进 A 的错题本；模型调用日志带 teacher_id"""
    a = await make_teacher()
    r = await grade(a, "/api/grader/upload", files={"files": ("o.md", DEFAULT_OCR.encode(), "text/markdown")},
                    data={"student_name": "归属学生"})
    assert r.json()["status"] == "completed"
    assert len((await a.get("/api/notebook/list", params={"student_name": "归属学生"})).json()) == 1
    grade_calls = [c for c in fake_ai.calls if c["feature"] == "grade"]
    assert grade_calls[-1]["task_meta"]["teacher_id"] == a.user["id"]


async def test_lessonplan_and_variant_calls_carry_teacher_id(make_teacher, fake_ai):
    a = await make_teacher()
    _, plan = await generate_plan(a, {"title": "带教师的教案"})
    assert plan["status"] == "completed"
    assert fake_ai.calls[-1]["task_meta"]["teacher_id"] == a.user["id"]


def _legacy_db(path):
    """模拟当前生产库：旧版播种的占位账号 teacher/hashed 拥有全部数据，另有无归属数据"""
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(50) NOT NULL, email VARCHAR(100),
                            password_hash VARCHAR(255) NOT NULL, role VARCHAR(20), created_at DATETIME);
        CREATE TABLE classes (id INTEGER PRIMARY KEY, class_name VARCHAR(100) NOT NULL, teacher_id INTEGER,
                            total_students INTEGER, subject VARCHAR(50), grade VARCHAR(20), created_at DATETIME);
        CREATE TABLE homework_assignments (id INTEGER PRIMARY KEY, title VARCHAR(200) NOT NULL, class_id INTEGER,
                            teacher_id INTEGER, reference_answer TEXT, deadline VARCHAR(20), created_at DATETIME);
        CREATE TABLE homework_submissions (id INTEGER PRIMARY KEY, assignment_id INTEGER, user_id INTEGER,
                            student_name VARCHAR(50), image_paths TEXT, grading_result TEXT, score FLOAT,
                            status VARCHAR(20), grading_status VARCHAR(20), created_at DATETIME);
        CREATE TABLE wrong_questions (id INTEGER PRIMARY KEY, user_id INTEGER, question_text TEXT NOT NULL,
                            knowledge_point VARCHAR(200), error_date DATETIME);
        CREATE TABLE lesson_plans (id INTEGER PRIMARY KEY, teacher_id INTEGER, title VARCHAR(200) NOT NULL,
                            content TEXT, created_at DATETIME);
        INSERT INTO users (id, username, email, password_hash, role) VALUES (1, 'teacher', 't@x', 'hashed', 'teacher');
        INSERT INTO classes (id, class_name, teacher_id) VALUES (1, '高三1班', 1), (2, '无主班', NULL);
        INSERT INTO homework_assignments (id, title, class_id, teacher_id) VALUES (1, '作业1', 1, 1), (2, '作业2', 2, NULL);
        INSERT INTO homework_submissions (id, assignment_id, student_name, status, grading_status, score)
            VALUES (1, 1, '张三', 'completed', '已批改', 80), (2, NULL, '临时', 'completed', '已批改', 90);
        INSERT INTO wrong_questions (id, user_id, question_text) VALUES (1, 1, '错题');
        INSERT INTO lesson_plans (id, teacher_id, title, content) VALUES (1, 1, '老教案', '# 内容');
    """)
    con.commit()
    con.close()


def _manage(db, *args):
    env = dict(os.environ, DATABASE_URL=f"sqlite+aiosqlite:///{db.as_posix()}", PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, str(BACKEND_DIR / "manage.py"), *args], env=env,
                          capture_output=True, text=True, encoding="utf-8", timeout=120)


@pytest.fixture
def on_db(monkeypatch):
    """让 manage.py 的函数在进程内操作指定的库（比起子进程快很多）"""
    from config import settings

    def _use(db):
        monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite+aiosqlite:///{db.as_posix()}")
    return _use


@pytest.mark.slow
def test_assign_orphans_cli_on_legacy_db(test_tmp):
    """命令行：在旧版结构的库上开通账号并认领历史数据（启动迁移只加列，不丢数据）"""
    db = test_tmp / "legacy_cli.db"
    _legacy_db(db)
    p = _manage(db, "create-user", "--username", "13800000001", "--name", "王老师", "--password", "Passw0rd99")
    assert p.returncode == 0, p.stderr
    p = _manage(db, "assign-orphans", "--username", "13800000001")
    assert p.returncode == 0, p.stderr
    assert "班级 2" in p.stdout and "教案 1" in p.stdout


def test_assign_orphans_on_legacy_db_is_idempotent_and_lossless(test_tmp, on_db):
    import manage
    db = test_tmp / "legacy_owner.db"
    _legacy_db(db)
    on_db(db)
    a_id, _ = manage.create_user("13800000001", "老师", password="Passw0rd99")
    manage.create_user("13800000003", "老师", password="Passw0rd99")
    counts = manage.assign_orphans("13800000001")
    assert counts["classes"] == 2 and counts["lesson_plans"] == 1
    # 第二次执行（哪怕换一个账号）不再改动任何数据
    assert set(manage.assign_orphans("13800000003").values()) == {0}

    con = sqlite3.connect(db)
    for table, col in (("classes", "teacher_id"), ("homework_assignments", "teacher_id"),
                       ("homework_submissions", "teacher_id"), ("wrong_questions", "user_id"),
                       ("lesson_plans", "teacher_id")):
        owners = {r[0] for r in con.execute(f"SELECT {col} FROM {table}")}
        assert owners == {a_id}, (table, owners)
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("users", "classes", "homework_assignments", "homework_submissions", "wrong_questions", "lesson_plans")}
    con.close()
    assert counts == {"users": 3, "classes": 2, "homework_assignments": 2, "homework_submissions": 2,
                      "wrong_questions": 1, "lesson_plans": 1}, "迁移不能丢数据"


def test_assign_orphans_keeps_other_teachers_data(test_tmp, on_db):
    """已经属于真实教师的数据不会被重新分配；子数据跟随上级的真实归属"""
    import manage
    db = test_tmp / "two_owners.db"
    _legacy_db(db)
    on_db(db)
    real_id, _ = manage.create_user("t_real", "甲", password="Passw0rd99")
    target_id, _ = manage.create_user("t_target", "乙", password="Passw0rd99")
    con = sqlite3.connect(db)
    con.execute("UPDATE classes SET teacher_id=? WHERE id=1", (real_id,))
    con.commit()
    con.close()
    manage.assign_orphans("t_target")
    con = sqlite3.connect(db)
    assert con.execute("SELECT teacher_id FROM classes WHERE id=1").fetchone()[0] == real_id
    assert con.execute("SELECT teacher_id FROM homework_assignments WHERE id=1").fetchone()[0] == real_id
    assert con.execute("SELECT teacher_id FROM homework_submissions WHERE id=1").fetchone()[0] == real_id
    assert con.execute("SELECT teacher_id FROM classes WHERE id=2").fetchone()[0] == target_id
    assert con.execute("SELECT teacher_id FROM homework_submissions WHERE id=2").fetchone()[0] == target_id
    con.close()
    with pytest.raises(manage.ManageError):
        manage.assign_orphans("no_such_teacher")
