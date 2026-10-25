"""question_bank 查询计时：优化前后对比。对本地 teaching_assistant.db 只读探测。"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

DB = Path(__file__).resolve().parent / "teaching_assistant.db"

QUERIES = {
    "count_all": "SELECT COUNT(*) FROM question_bank",
    "subject_grade": (
        "SELECT id FROM question_bank WHERE subject = ? AND grade = ? "
        "ORDER BY created_at DESC LIMIT 20 OFFSET 0"
    ),
    "subject_level": (
        "SELECT id FROM question_bank WHERE subject = ? AND education_level = ? "
        "LIMIT 10"
    ),
    "knowledge_points_like": (
        "SELECT id FROM question_bank WHERE knowledge_points LIKE ? LIMIT 10"
    ),
    "question_text_like": (
        "SELECT id FROM question_bank WHERE question_text LIKE ? LIMIT 10"
    ),
    "deep_offset": (
        "SELECT id FROM question_bank WHERE subject = ? "
        "ORDER BY created_at DESC LIMIT 20 OFFSET 50000"
    ),
    "question_type_filter": (
        "SELECT id FROM question_bank WHERE subject = ? AND question_type = ? "
        "LIMIT 20"
    ),
    "exam_year": (
        "SELECT id FROM question_bank WHERE exam_type = ? ORDER BY year DESC LIMIT 20"
    ),
}


def connect(db: Path = DB) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def list_indexes(con: sqlite3.Connection) -> list[tuple[str, str | None]]:
    return list(
        con.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='index' AND tbl_name='question_bank' ORDER BY name"
        )
    )


def explain(con: sqlite3.Connection, sql: str, params: tuple) -> list[str]:
    rows = con.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
    return [str(tuple(r)) for r in rows]


def timed(con: sqlite3.Connection, sql: str, params: tuple, repeats: int = 3) -> dict:
    # warmup
    con.execute(sql, params).fetchall()
    times = []
    n = 0
    for _ in range(repeats):
        t0 = time.perf_counter()
        rows = con.execute(sql, params).fetchall()
        times.append((time.perf_counter() - t0) * 1000)
        n = len(rows)
    return {
        "ms_min": round(min(times), 2),
        "ms_avg": round(sum(times) / len(times), 2),
        "ms_max": round(max(times), 2),
        "rows": n,
        "plan": explain(con, sql, params),
    }


def pick_params(con: sqlite3.Connection) -> dict:
    subject = con.execute(
        "SELECT subject FROM question_bank GROUP BY subject ORDER BY COUNT(*) DESC LIMIT 1"
    ).fetchone()
    grade = con.execute(
        "SELECT grade FROM question_bank WHERE grade IS NOT NULL "
        "GROUP BY grade ORDER BY COUNT(*) DESC LIMIT 1"
    ).fetchone()
    level = con.execute(
        "SELECT education_level FROM question_bank GROUP BY education_level "
        "ORDER BY COUNT(*) DESC LIMIT 1"
    ).fetchone()
    qtype = con.execute(
        "SELECT question_type FROM question_bank GROUP BY question_type "
        "ORDER BY COUNT(*) DESC LIMIT 1"
    ).fetchone()
    exam = con.execute(
        "SELECT exam_type FROM question_bank WHERE exam_type IS NOT NULL AND exam_type != '' "
        "GROUP BY exam_type ORDER BY COUNT(*) DESC LIMIT 1"
    ).fetchone()
    kp = con.execute(
        "SELECT knowledge_points FROM question_bank "
        "WHERE knowledge_points IS NOT NULL AND length(knowledge_points) > 4 LIMIT 1"
    ).fetchone()
    token = "函数"
    if kp and kp[0]:
        raw = kp[0]
        for cand in ("函数", "方程", "几何", "导数", "代数"):
            if cand in raw:
                token = cand
                break
    return {
        "subject": subject[0] if subject else "数学",
        "grade": grade[0] if grade else 12,
        "level": level[0] if level else "高中",
        "qtype": qtype[0] if qtype else "选择题",
        "exam": exam[0] if exam else "高考",
        "kp": token,
    }


def run_suite(label: str, db: Path = DB) -> dict:
    con = connect(db)
    try:
        total = con.execute("SELECT COUNT(*) FROM question_bank").fetchone()[0]
        indexes = list_indexes(con)
        params = pick_params(con)
        results = {
            "label": label,
            "total": total,
            "indexes": [(n, s) for n, s in indexes],
            "params": params,
            "queries": {},
        }
        bind = {
            "count_all": (),
            "subject_grade": (params["subject"], params["grade"]),
            "subject_level": (params["subject"], params["level"]),
            "knowledge_points_like": (f"%{params['kp']}%",),
            "question_text_like": (f"%{params['kp']}%",),
            "deep_offset": (params["subject"],),
            "question_type_filter": (params["subject"], params["qtype"]),
            "exam_year": (params["exam"],),
        }
        for name, sql in QUERIES.items():
            results["queries"][name] = timed(con, sql, bind[name])
        return results
    finally:
        con.close()


def print_report(report: dict) -> None:
    print(f"=== {report['label']}  total={report['total']} ===")
    print("indexes:")
    for name, sql in report["indexes"]:
        print(f"  {name}: {sql}")
    print("params:", report["params"])
    for name, q in report["queries"].items():
        print(f"  {name}: avg={q['ms_avg']}ms min={q['ms_min']} max={q['ms_max']} rows={q['rows']}")
        for line in q["plan"]:
            print(f"    PLAN {line}")


def apply_indexes(db: Path = DB) -> None:
    from database import QUESTION_BANK_INDEX_DDL

    con = sqlite3.connect(db)
    try:
        t0 = time.perf_counter()
        for ddl in QUESTION_BANK_INDEX_DDL:
            con.execute(ddl)
        con.execute("ANALYZE question_bank")
        con.commit()
        print(f"applied indexes in {round((time.perf_counter() - t0) * 1000, 1)}ms")
    finally:
        con.close()


if __name__ == "__main__":
    import json
    import sys

    label = sys.argv[1] if len(sys.argv) > 1 else "current"
    if label == "after":
        apply_indexes()
    out = Path(__file__).resolve().parent / f"bench_{label}.json"
    report = run_suite(label)
    print_report(report)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}")
