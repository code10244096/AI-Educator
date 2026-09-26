"""Data must survive app restarts and schema initialisation / migration."""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from helpers import grade, submission_id_of

RUNNER = Path(__file__).resolve().parent / "_app_runner.py"


def _run(action: str, db: Path, workdir: Path, extra_env=None, timeout=180) -> dict:
    env = dict(os.environ)
    env.update({
        "DATABASE_URL": f"sqlite+aiosqlite:///{db.as_posix()}",
        "UPLOAD_DIR": str(workdir / "uploads"),
        "API_OUTPUT_ROOT": str(workdir / "api_runs"),
        "LLM_API_KEY": "your_api_key_here",
        "PYTHONIOENCODING": "utf-8",
    })
    env.update(extra_env or {})
    p = subprocess.run([sys.executable, str(RUNNER), action], env=env, capture_output=True,
                       timeout=timeout, cwd=str(workdir), encoding="utf-8", errors="replace")
    lines = [l for l in p.stdout.splitlines() if l.startswith("RESULT:")]
    assert p.returncode == 0 and lines, f"runner {action} failed rc={p.returncode}\n{p.stdout[-2000:]}\n{p.stderr[-3000:]}"
    return json.loads(lines[-1][len("RESULT:"):])


# ------------------------------------------------------------- in-process

async def test_init_db_rerun_keeps_rows(client, fake_ai):
    import database
    r = await grade(client, "/api/grader/upload",
                    files={"files": ("i.md", "### 1. x\n**学生答案**：1".encode(), "text/markdown")},
                    data={"student_name": "init_db 学生"})
    sid = submission_id_of(r.json())
    q = await client.post("/api/questionbank/add", data={
        "question_text": "init_db 题", "answer": "1", "question_type": "填空题",
        "subject": "数学", "education_level": "高中"})
    qid = q.json()["id"]

    await database.init_db()
    await database.init_db()

    assert (await client.get(f"/api/grader/{sid}")).status_code == 200
    assert (await client.get(f"/api/questionbank/{qid}")).status_code == 200


async def test_second_startup_does_not_reseed_or_duplicate(app, client):
    before_classes = (await client.get("/api/class/list")).json()["items"]
    before_hw = (await client.get("/api/class/class1/homework")).json()["items"]
    async with app.router.lifespan_context(app):  # simulate another startup on same DB
        pass
    after_classes = (await client.get("/api/class/list")).json()["items"]
    after_hw = (await client.get("/api/class/class1/homework")).json()["items"]
    assert len(after_classes) == len(before_classes)
    assert len(after_hw) == len(before_hw)
    assert [h["submitted"] for h in after_hw] == [h["submitted"] for h in before_hw]


# ------------------------------------------------------------- real restart (subprocess)

@pytest.mark.slow
def test_restart_process_keeps_data(test_tmp):
    work = test_tmp / "restart"
    work.mkdir(exist_ok=True)
    db = work / "restart.db"
    created = _run("create", db, work)
    assert created["grade_status"] == 200 and created["submission_id"]
    assert created["classes"] == 3

    checked = _run("check", db, work, {"RUNNER_IDS": json.dumps(created)})
    if created.get("lesson_id"):
        assert checked["lesson"] == 200
    assert checked["submission"] == 200
    assert checked["question"] == 200
    assert checked["classes"] == 3, "re-seeding duplicated classes"
    assert checked["hw10_submitted"] == created["hw10_submitted"]


def _make_legacy_db(path: Path):
    """Simulate a DB created by an older version: homework_submissions without the
    grading_status / student_name columns and no class_members table, plus user data."""
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(50) NOT NULL, email VARCHAR(100),
                            password_hash VARCHAR(255) NOT NULL, role VARCHAR(20), created_at DATETIME);
        CREATE TABLE lesson_plans (id INTEGER PRIMARY KEY, teacher_id INTEGER, title VARCHAR(200) NOT NULL,
                            period VARCHAR(50), student_level VARCHAR(50), requirements TEXT, content TEXT,
                            created_at DATETIME, updated_at DATETIME);
        CREATE TABLE homework_assignments (id INTEGER PRIMARY KEY, title VARCHAR(200) NOT NULL, class_id INTEGER,
                            teacher_id INTEGER, reference_answer TEXT, deadline VARCHAR(20), created_at DATETIME);
        CREATE TABLE homework_submissions (id INTEGER PRIMARY KEY, assignment_id INTEGER, user_id INTEGER,
                            image_paths TEXT, ocr_result TEXT, grading_result TEXT, wrong_count INTEGER,
                            score FLOAT, status VARCHAR(20), created_at DATETIME);
        CREATE TABLE wrong_questions (id INTEGER PRIMARY KEY, user_id INTEGER, question_text TEXT NOT NULL,
                            user_answer TEXT, correct_answer TEXT, knowledge_point VARCHAR(200), subject VARCHAR(50),
                            error_date DATETIME, is_mastered BOOLEAN, variant_questions TEXT, image_path VARCHAR(500));
        INSERT INTO lesson_plans (id, title, content) VALUES (1, '老教案', '# 老师的心血');
        INSERT INTO homework_submissions (id, assignment_id, score, status, grading_result)
            VALUES (1, NULL, 88, 'completed', '{}');
        INSERT INTO wrong_questions (id, question_text, knowledge_point) VALUES (1, '老错题', '函数');
    """)
    con.commit()
    con.close()


def _count(path: Path, table: str) -> int:
    con = sqlite3.connect(path)
    try:
        return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        con.close()


@pytest.mark.slow
def test_init_db_on_current_schema_is_noop(test_tmp):
    work = test_tmp / "noop"
    work.mkdir(exist_ok=True)
    db = work / "noop.db"
    _run("initdb", db, work)
    con = sqlite3.connect(db)
    con.execute("INSERT INTO lesson_plans (title, content) VALUES ('保留', 'x')")
    con.commit()
    con.close()
    _run("initdb", db, work)
    assert _count(db, "lesson_plans") == 1


@pytest.mark.slow
# FINDING F-01 (CRITICAL at HEAD): init_db() used Base.metadata.drop_all() on schema drift.
# Fixed in the working tree during this session; this is now a hard regression guard.
def test_init_db_migrates_legacy_schema_without_data_loss(test_tmp):
    work = test_tmp / "legacy"
    work.mkdir(exist_ok=True)
    db = work / "legacy.db"
    _make_legacy_db(db)
    _run("initdb", db, work)
    assert _count(db, "lesson_plans") == 1, "lesson plans were dropped"
    assert _count(db, "wrong_questions") == 1, "notebook was dropped"
    assert _count(db, "homework_submissions") == 1, "submissions were dropped"
    con = sqlite3.connect(db)
    cols = {r[1] for r in con.execute("PRAGMA table_info(homework_submissions)")}
    con.close()
    assert {"grading_status", "student_name"} <= cols, "missing columns were not added"


@pytest.mark.slow
def test_init_db_on_legacy_schema_ends_with_usable_schema(test_tmp):
    """Whatever the migration strategy, the resulting schema must be complete."""
    work = test_tmp / "legacy2"
    work.mkdir(exist_ok=True)
    db = work / "legacy2.db"
    _make_legacy_db(db)
    _run("initdb", db, work)
    con = sqlite3.connect(db)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    sub_cols = {r[1] for r in con.execute("PRAGMA table_info(homework_submissions)")}
    asg_cols = {r[1] for r in con.execute("PRAGMA table_info(homework_assignments)")}
    con.close()
    assert "class_members" in tables
    assert {"grading_status", "student_name", "dataset_file_id"} <= sub_cols
    assert {"dataset_file_id", "status", "assign_date"} <= asg_cols


async def test_interrupted_jobs_marked_failed_on_startup(app, client, default_teacher):
    """A job left 'processing' by a crash/restart must not stay processing forever."""
    import database
    from models import HomeworkSubmission, LessonPlan
    tid = default_teacher["id"]
    async with database.AsyncSessionLocal() as db:
        sub = HomeworkSubmission(student_name="中断学生", status="processing", grading_status="批改中",
                                 progress_stage="批改中", image_paths="[]", teacher_id=tid)
        plan = LessonPlan(title="中断教案", status="processing", progress_stage="AI 生成中", content="",
                          teacher_id=tid)
        db.add_all([sub, plan])
        await db.commit()
        sid, pid = sub.id, plan.id
    async with app.router.lifespan_context(app):  # simulated restart
        pass
    s = (await client.get(f"/api/grader/{sid}")).json()
    assert s["status"] == "failed" and s["error_message"]
    assert s["grading_status"] != "批改中"
    p = (await client.get(f"/api/lessonplan/{pid}")).json()
    assert p["status"] == "failed" and p["error_message"]
